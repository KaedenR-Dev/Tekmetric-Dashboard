"""
Complete Auto Repair - Analytics Layer

This module sits between the SQLite database and the dashboard UI.

Reporting bases:
    revenue  -> posted_date
    production -> completed_date
    activity -> created_date

All financial amounts returned by this module are in dollars.
Tekmetric stores financial values in cents.
"""

from datetime import datetime, timedelta
from database import get_connection


REPORTING_DATE_COLUMNS = {
    "revenue": "posted_date",
    "production": "completed_date",
    "activity": "created_date",
}


def _validate_basis(basis):
    if basis not in REPORTING_DATE_COLUMNS:
        raise ValueError(
            f"Invalid reporting basis '{basis}'. "
            f"Use one of: {', '.join(REPORTING_DATE_COLUMNS)}"
        )


def _date_column(basis):
    _validate_basis(basis)
    return REPORTING_DATE_COLUMNS[basis]


def _date_range(start_date=None, end_date=None, days=None):
    """
    Return YYYY-MM-DD strings.

    If days is supplied, end_date defaults to today and start_date
    defaults to today minus (days - 1).
    """
    today = datetime.now().date()

    if end_date is None:
        end = today
    elif hasattr(end_date, "date"):
        end = end_date.date()
    else:
        end = datetime.strptime(str(end_date), "%Y-%m-%d").date()

    if start_date is None:
        if days is None:
            start = end
        else:
            start = end - timedelta(days=days - 1)
    elif hasattr(start_date, "date"):
        start = start_date.date()
    else:
        start = datetime.strptime(str(start_date), "%Y-%m-%d").date()

    return start.isoformat(), end.isoformat()


def _normalize_total_sales(row):
    """
    Return a reliable total_sales for one aggregated row.

    Some historical repair orders have a zero or missing total_sales
    even though their component fields (labor, parts, sublet, fees,
    taxes, discounts) are populated. When that happens, rebuild the
    total from components instead. This is the single place that
    fallback happens; callers should never need to re-derive it.
    """
    direct = row.get("total_sales") or 0

    if direct > 0:
        return direct

    rebuilt = (
        (row.get("labor_sales") or 0)
        + (row.get("parts_sales") or 0)
        + (row.get("sublet_sales") or 0)
        + (row.get("fees") or 0)
        + (row.get("taxes") or 0)
        - (row.get("discounts") or 0)
    )

    return max(rebuilt, 0)


def _where_clause(basis, start_date, end_date, alias="r"):
    column = _date_column(basis)

    return f"""
        {alias}.{column} IS NOT NULL
        AND date(substr({alias}.{column}, 1, 10))
            BETWEEN date(?) AND date(?)
    """, [start_date, end_date]


def get_revenue(start_date=None, end_date=None, basis="revenue", days=None):
    """
    Return shop-level financial metrics for a selected period.

    For revenue/EOD, use posted_date.
    """
    start_date, end_date = _date_range(
        start_date, end_date, days
    )

    where, params = _where_clause(
        basis, start_date, end_date
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            COUNT(*) AS ro_count,
            COALESCE(SUM(labor_sales), 0) AS labor_sales,
            COALESCE(SUM(parts_sales), 0) AS parts_sales,
            COALESCE(SUM(sublet_sales), 0) AS sublet_sales,
            COALESCE(SUM(discount_total), 0) AS discounts,
            COALESCE(SUM(fee_total), 0) AS fees,
            COALESCE(SUM(taxes), 0) AS taxes,
            COALESCE(SUM(total_sales), 0) AS total_sales
        FROM repair_orders r
        WHERE {where}
        """,
        params,
    )

    row = cursor.fetchone()
    connection.close()

    ro_count = row["ro_count"] or 0

    labor = (row["labor_sales"] or 0) / 100
    parts = (row["parts_sales"] or 0) / 100
    sublet = (row["sublet_sales"] or 0) / 100
    discounts = (row["discounts"] or 0) / 100
    fees = (row["fees"] or 0) / 100
    taxes = (row["taxes"] or 0) / 100
    total = (row["total_sales"] or 0) / 100

    return {
        "start_date": start_date,
        "end_date": end_date,
        "basis": basis,
        "ro_count": ro_count,
        "labor_sales": labor,
        "parts_sales": parts,
        "sublet_sales": sublet,
        "discounts": discounts,
        "fees": fees,
        "taxes": taxes,
        "total_sales": total,
        "average_ro": total / ro_count if ro_count else 0,
        "labor_percent": labor / total * 100 if total else 0,
        "parts_percent": parts / total * 100 if total else 0,
        "discount_percent": discounts / (labor + parts) * 100
            if (labor + parts) else 0,
    }


def get_daily_trends(start_date=None, end_date=None, basis="revenue"):
    """Return one row per day for charting."""
    start_date, end_date = _date_range(
        start_date, end_date
    )

    column = _date_column(basis)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            substr(r.{column}, 1, 10) AS day,
            COUNT(*) AS ro_count,
            COALESCE(SUM(r.labor_sales), 0) / 100.0 AS labor_sales,
            COALESCE(SUM(r.parts_sales), 0) / 100.0 AS parts_sales,
            COALESCE(SUM(r.sublet_sales), 0) / 100.0 AS sublet_sales,
            COALESCE(SUM(r.fee_total), 0) / 100.0 AS fees,
            COALESCE(SUM(r.taxes), 0) / 100.0 AS taxes,
            COALESCE(SUM(r.discount_total), 0) / 100.0 AS discounts,
            COALESCE(SUM(r.total_sales), 0) / 100.0 AS total_sales
        FROM repair_orders r
        WHERE r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)
        GROUP BY substr(r.{column}, 1, 10)
        ORDER BY day
        """,
        [start_date, end_date],
    )

    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()

    for row in rows:
        row["total_sales"] = _normalize_total_sales(row)
        row["average_ro"] = (
            row["total_sales"] / row["ro_count"]
            if row["ro_count"] else 0
        )

    return rows


def get_monthly_trends(start_date=None, end_date=None, basis="revenue"):
    """Return one row per month for charting."""
    start_date, end_date = _date_range(
        start_date, end_date
    )

    column = _date_column(basis)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            substr(r.{column}, 1, 7) AS month,
            COUNT(*) AS ro_count,
            COALESCE(SUM(r.labor_sales), 0) / 100.0 AS labor_sales,
            COALESCE(SUM(r.parts_sales), 0) / 100.0 AS parts_sales,
            COALESCE(SUM(r.sublet_sales), 0) / 100.0 AS sublet_sales,
            COALESCE(SUM(r.fee_total), 0) / 100.0 AS fees,
            COALESCE(SUM(r.taxes), 0) / 100.0 AS taxes,
            COALESCE(SUM(r.discount_total), 0) / 100.0 AS discounts,
            COALESCE(SUM(r.total_sales), 0) / 100.0 AS total_sales
        FROM repair_orders r
        WHERE r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)
        GROUP BY substr(r.{column}, 1, 7)
        ORDER BY month
        """,
        [start_date, end_date],
    )

    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()

    for row in rows:
        row["total_sales"] = _normalize_total_sales(row)
        row["average_ro"] = (
            row["total_sales"] / row["ro_count"]
            if row["ro_count"] else 0
        )

    return rows


def get_technician_metrics(
    start_date=None,
    end_date=None,
    basis="revenue",
):
    """
    Technician production for the selected reporting period.

    The reporting period is applied directly to the repair order before
    labor lines are aggregated. This prevents technician metrics from
    accidentally including labor from outside the selected period.
    """

    start_date, end_date = _date_range(start_date, end_date)
    column = _date_column(basis)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            e.id AS technician_id,

            TRIM(
                COALESCE(e.first_name, '') || ' ' ||
                COALESCE(e.last_name, '')
            ) AS technician_name,

            COUNT(DISTINCT j.id) AS jobs,

            COALESCE(SUM(ll.hours), 0) AS labor_hours,

            COALESCE(
                SUM(ll.hours * ll.rate) / 100.0,
                0
            ) AS labor_sales

        FROM labor_lines ll

        INNER JOIN jobs j
            ON j.id = ll.job_id

        INNER JOIN repair_orders r
            ON r.id = j.repair_order_id

        INNER JOIN employees e
            ON e.id = ll.technician_id

        WHERE r.{column} IS NOT NULL

          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)

        GROUP BY
            e.id,
            e.first_name,
            e.last_name

        ORDER BY
            labor_hours DESC,
            technician_name
        """,
        [start_date, end_date],
    )

    rows = [dict(row) for row in cursor.fetchall()]

    connection.close()

    for row in rows:
        hours = row["labor_hours"] or 0
        sales = row["labor_sales"] or 0
        jobs = row["jobs"] or 0

        row["average_hours_per_job"] = (
            hours / jobs
            if jobs
            else 0
        )

        row["average_labor_per_job"] = (
            sales / jobs
            if jobs
            else 0
        )

        row["effective_labor_rate"] = (
            sales / hours
            if hours
            else 0
        )

    return rows


def get_technician_trend(
    technician_id,
    weeks=12,
    basis="revenue",
    end_date=None,
):
    """
    Return one technician's core metrics bucketed weekly over a
    trailing window, so a service manager can see how they're
    trending rather than reading a single-period snapshot.

    This is deliberately decoupled from the dashboard's own period
    selector (7/30/90/365 days) — a trend view needs a fixed, rolling
    number of weeks regardless of what window the rest of the
    dashboard happens to be showing.

    Weeks are bucketed Sunday-Saturday using SQLite's 'weekday 0'
    modifier, and labeled by each week's start date.
    """
    column = _date_column(basis)

    if end_date is None:
        end = datetime.now().date()
    elif hasattr(end_date, "date"):
        end = end_date.date()
    else:
        end = datetime.strptime(str(end_date), "%Y-%m-%d").date()

    # Start of the current week (Sunday), then back up (weeks - 1)
    # more full weeks to get the start of the window.
    start = end - timedelta(days=weeks * 7)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            date(
                substr(r.{column}, 1, 10),
                'weekday 0', '-6 days'
            ) AS week_start,

            COUNT(DISTINCT j.id) AS jobs,
            COALESCE(SUM(ll.hours), 0) AS labor_hours,
            COALESCE(SUM(ll.hours * ll.rate) / 100.0, 0) AS labor_sales

        FROM labor_lines ll

        INNER JOIN jobs j
            ON j.id = ll.job_id

        INNER JOIN repair_orders r
            ON r.id = j.repair_order_id

        WHERE ll.technician_id = ?
          AND r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)

        GROUP BY week_start
        ORDER BY week_start
        """,
        [technician_id, start.isoformat(), end.isoformat()],
    )

    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()

    for row in rows:
        hours = row["labor_hours"] or 0
        sales = row["labor_sales"] or 0
        jobs = row["jobs"] or 0

        row["average_hours_per_job"] = hours / jobs if jobs else 0
        row["effective_labor_rate"] = sales / hours if hours else 0

    # A simple trend read: compare the most recent half of the window
    # against the earlier half, on effective labor rate. Needs at
    # least 2 weeks of data with billed hours to mean anything.
    rate_weeks = [row for row in rows if row["labor_hours"]]
    trend_direction = None
    recent_average_rate = None
    prior_average_rate = None

    if len(rate_weeks) >= 2:
        midpoint = len(rate_weeks) // 2 or 1
        prior_weeks = rate_weeks[:midpoint]
        recent_weeks = rate_weeks[midpoint:] or rate_weeks[-1:]

        prior_average_rate = (
            sum(w["effective_labor_rate"] for w in prior_weeks)
            / len(prior_weeks)
        )
        recent_average_rate = (
            sum(w["effective_labor_rate"] for w in recent_weeks)
            / len(recent_weeks)
        )

        if prior_average_rate:
            change = (
                (recent_average_rate - prior_average_rate)
                / prior_average_rate
            )
            if change > 0.05:
                trend_direction = "up"
            elif change < -0.05:
                trend_direction = "down"
            else:
                trend_direction = "flat"

    return {
        "technician_id": technician_id,
        "basis": basis,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "weeks": rows,
        "trend_direction": trend_direction,
        "recent_average_rate": recent_average_rate,
        "prior_average_rate": prior_average_rate,
    }


def get_advisor_metrics(
    start_date=None,
    end_date=None,
    basis="revenue",
):
    """Return repair-order metrics by service writer."""
    start_date, end_date = _date_range(
        start_date, end_date
    )

    column = _date_column(basis)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            e.id AS advisor_id,

            TRIM(
                COALESCE(e.first_name, '') || ' ' ||
                COALESCE(e.last_name, '')
            ) AS advisor_name,

            COUNT(r.id) AS ro_count,

            COALESCE(SUM(r.total_sales), 0) / 100.0
                AS total_sales,

            COALESCE(SUM(r.labor_sales), 0) / 100.0
                AS labor_sales,

            COALESCE(SUM(r.parts_sales), 0) / 100.0
                AS parts_sales,

            COALESCE(SUM(r.discount_total), 0) / 100.0
                AS discounts

        FROM employees e

        LEFT JOIN repair_orders r
            ON r.service_writer_id = e.id
            AND r.{column} IS NOT NULL
            AND date(substr(r.{column}, 1, 10))
                BETWEEN date(?) AND date(?)

        WHERE LOWER(COALESCE(e.role_name, '')) = 'service advisor'

        GROUP BY
            e.id,
            e.first_name,
            e.last_name

        ORDER BY total_sales DESC
        """,
        [start_date, end_date],
    )

    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()

    for row in rows:
        row["average_ro"] = (
            row["total_sales"] / row["ro_count"]
            if row["ro_count"] else 0
        )

    return rows


def get_job_category_metrics(
    start_date=None,
    end_date=None,
    basis="revenue",
):
    """
    Return revenue and margin broken out by job category — i.e. the
    shop's profit centers (brakes, oil changes, diagnostics, etc.).

    Parts margin is a real cost-based margin (parts.cost vs.
    parts.retail is tracked per part). Labor margin is NOT included
    here, because technician labor cost isn't tracked anywhere in this
    database yet — only what was billed, not what it cost to produce.
    Treat "labor_revenue" as top-line only until a technician cost
    rate is captured somewhere.

    Only authorized, non-archived jobs are counted. Declined/estimated
    work can still carry a quoted labor_total/parts_total in Tekmetric
    even though it was never sold — including it here would overstate
    real revenue and blur this report with a future "missed revenue"
    report covering exactly that declined work.
    """
    start_date, end_date = _date_range(
        start_date, end_date
    )

    column = _date_column(basis)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        SELECT
            COALESCE(NULLIF(TRIM(j.job_category_name), ''), 'Uncategorized')
                AS category,

            COUNT(DISTINCT j.id) AS job_count,
            COUNT(DISTINCT j.repair_order_id) AS ro_count,

            COALESCE(SUM(j.labor_total), 0) / 100.0 AS labor_revenue,
            COALESCE(SUM(j.parts_total), 0) / 100.0 AS parts_revenue,
            COALESCE(SUM(j.discount_total), 0) / 100.0 AS discounts,
            COALESCE(SUM(j.fee_total), 0) / 100.0 AS fees,
            COALESCE(SUM(j.subtotal), 0) / 100.0 AS net_revenue,

            COALESCE(SUM(pc.parts_cost), 0) / 100.0 AS parts_cost,
            COALESCE(SUM(pc.parts_row_count), 0) AS parts_row_count,
            COALESCE(SUM(lh.labor_hours), 0) AS labor_hours

        FROM jobs j

        INNER JOIN repair_orders r
            ON r.id = j.repair_order_id

        -- Parts cost is aggregated per job in a subquery first, so
        -- joining it in doesn't fan out the job row (and double-count
        -- j.labor_total / j.parts_total) when a job has many parts.
        LEFT JOIN (
            SELECT
                job_id,
                SUM(COALESCE(cost, 0) * COALESCE(quantity, 0)) AS parts_cost,
                COUNT(*) AS parts_row_count
            FROM parts
            GROUP BY job_id
        ) pc ON pc.job_id = j.id

        -- Same reasoning for labor hours: aggregate per job first.
        LEFT JOIN (
            SELECT job_id, SUM(COALESCE(hours, 0)) AS labor_hours
            FROM labor_lines
            GROUP BY job_id
        ) lh ON lh.job_id = j.id

        WHERE r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)
          AND j.authorized = 1
          AND (j.archived IS NULL OR j.archived = 0)

        GROUP BY category

        ORDER BY net_revenue DESC
        """,
        [start_date, end_date],
    )

    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()

    shop_net_revenue = sum(row["net_revenue"] for row in rows)

    for row in rows:
        parts_revenue = row["parts_revenue"] or 0
        parts_cost = row["parts_cost"] or 0
        parts_row_count = row["parts_row_count"] or 0
        labor_hours = row["labor_hours"] or 0
        job_count = row["job_count"] or 0

        # If there's parts revenue but no itemized parts rows behind it,
        # that's missing cost data, not a genuine 100% margin — don't
        # report a margin that would be actively misleading.
        row["has_parts_cost_data"] = parts_row_count > 0

        row["parts_margin_dollars"] = (
            parts_revenue - parts_cost
            if row["has_parts_cost_data"] else None
        )

        row["parts_margin_percent"] = (
            row["parts_margin_dollars"] / parts_revenue * 100
            if parts_revenue and row["has_parts_cost_data"] else None
        )

        row["total_revenue"] = row["labor_revenue"] + parts_revenue

        row["percent_of_shop_revenue"] = (
            row["net_revenue"] / shop_net_revenue * 100
            if shop_net_revenue else 0
        )

        row["average_job_value"] = (
            row["net_revenue"] / job_count
            if job_count else 0
        )

        row["effective_labor_rate"] = (
            row["labor_revenue"] / labor_hours
            if labor_hours else 0
        )

    return rows


def get_missed_revenue(
    start_date=None,
    end_date=None,
    basis="revenue",
    job_limit=50,
):
    """
    Return revenue that was recommended to customers but never
    authorized — the flip side of get_job_category_metrics, which
    only counts sold work.

    "Declined" here just means jobs.authorized = 0; Tekmetric doesn't
    distinguish "customer said no" from "still waiting on a decision"
    beyond that. This uses the same reporting basis as the rest of the
    dashboard, so on the default "revenue" basis it only includes jobs
    on repair orders that have actually posted/closed — i.e. the
    customer's decision is final, not an estimate still sitting on an
    open RO.
    """
    start_date, end_date = _date_range(start_date, end_date)
    column = _date_column(basis)

    connection = get_connection()
    cursor = connection.cursor()

    # ------------------------------------------------------------
    # Shop-wide summary: sold vs. declined
    # ------------------------------------------------------------

    cursor.execute(
        f"""
        SELECT
            j.authorized AS authorized,
            COUNT(*) AS job_count,
            COALESCE(SUM(j.subtotal), 0) / 100.0 AS value
        FROM jobs j
        INNER JOIN repair_orders r ON r.id = j.repair_order_id
        WHERE r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)
          AND (j.archived IS NULL OR j.archived = 0)
        GROUP BY j.authorized
        """,
        [start_date, end_date],
    )

    declined_value = 0.0
    declined_count = 0
    authorized_value = 0.0
    authorized_count = 0

    for row in cursor.fetchall():
        if row["authorized"]:
            authorized_value = row["value"] or 0
            authorized_count = row["job_count"] or 0
        else:
            declined_value = row["value"] or 0
            declined_count = row["job_count"] or 0

    recommended_value = authorized_value + declined_value

    summary = {
        "declined_value": declined_value,
        "declined_count": declined_count,
        "authorized_value": authorized_value,
        "authorized_count": authorized_count,
        "recommended_value": recommended_value,
        "conversion_rate_percent": (
            authorized_value / recommended_value * 100
            if recommended_value else 0
        ),
        "average_declined_value": (
            declined_value / declined_count
            if declined_count else 0
        ),
    }

    # ------------------------------------------------------------
    # Breakdown by job category — where is work getting declined?
    # ------------------------------------------------------------

    cursor.execute(
        f"""
        SELECT
            COALESCE(NULLIF(TRIM(j.job_category_name), ''), 'Uncategorized')
                AS category,

            COALESCE(SUM(
                CASE WHEN j.authorized = 1 THEN j.subtotal ELSE 0 END
            ), 0) / 100.0 AS authorized_value,

            SUM(CASE WHEN j.authorized = 1 THEN 1 ELSE 0 END)
                AS authorized_count,

            COALESCE(SUM(
                CASE WHEN j.authorized = 0 THEN j.subtotal ELSE 0 END
            ), 0) / 100.0 AS declined_value,

            SUM(CASE WHEN j.authorized = 0 THEN 1 ELSE 0 END)
                AS declined_count

        FROM jobs j
        INNER JOIN repair_orders r ON r.id = j.repair_order_id
        WHERE r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)
          AND (j.archived IS NULL OR j.archived = 0)
        GROUP BY category
        HAVING declined_value > 0 OR authorized_value > 0
        ORDER BY declined_value DESC
        """,
        [start_date, end_date],
    )

    by_category = []

    for row in cursor.fetchall():
        category_authorized = row["authorized_value"] or 0
        category_declined = row["declined_value"] or 0
        category_recommended = category_authorized + category_declined

        by_category.append({
            "category": row["category"],
            "authorized_value": category_authorized,
            "authorized_count": row["authorized_count"] or 0,
            "declined_value": category_declined,
            "declined_count": row["declined_count"] or 0,
            "recommended_value": category_recommended,
            "conversion_rate_percent": (
                category_authorized / category_recommended * 100
                if category_recommended else 0
            ),
        })

    # ------------------------------------------------------------
    # Individual declined jobs — a follow-up call list, highest
    # dollar value first.
    # ------------------------------------------------------------

    cursor.execute(
        f"""
        SELECT
            j.id AS job_id,
            j.name AS job_name,
            COALESCE(NULLIF(TRIM(j.job_category_name), ''), 'Uncategorized')
                AS category,
            j.subtotal / 100.0 AS quoted_value,
            r.repair_order_number AS ro_number,
            r.{column} AS report_date,
            TRIM(
                COALESCE(tech.first_name, '') || ' ' ||
                COALESCE(tech.last_name, '')
            ) AS technician_name,
            TRIM(
                COALESCE(adv.first_name, '') || ' ' ||
                COALESCE(adv.last_name, '')
            ) AS advisor_name
        FROM jobs j
        INNER JOIN repair_orders r ON r.id = j.repair_order_id
        LEFT JOIN employees tech ON tech.id = j.technician_id
        LEFT JOIN employees adv ON adv.id = r.service_writer_id
        WHERE r.{column} IS NOT NULL
          AND date(substr(r.{column}, 1, 10))
              BETWEEN date(?) AND date(?)
          AND j.authorized = 0
          AND (j.archived IS NULL OR j.archived = 0)
        ORDER BY j.subtotal DESC
        LIMIT ?
        """,
        [start_date, end_date, job_limit],
    )

    top_declined_jobs = [dict(row) for row in cursor.fetchall()]

    connection.close()

    for job in top_declined_jobs:
        job["technician_name"] = job["technician_name"] or "Unassigned"
        job["advisor_name"] = job["advisor_name"] or "Unknown"

    return {
        "start_date": start_date,
        "end_date": end_date,
        "basis": basis,
        "summary": summary,
        "by_category": by_category,
        "top_declined_jobs": top_declined_jobs,
    }


def get_period_comparison(
    start_date,
    end_date,
    basis="revenue",
):
    """
    Compare the selected period with the immediately preceding
    period of the same length.
    """
    start = datetime.strptime(
        str(start_date), "%Y-%m-%d"
    ).date()

    end = datetime.strptime(
        str(end_date), "%Y-%m-%d"
    ).date()

    period_length = (end - start).days + 1

    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(
        days=period_length - 1
    )

    current = get_revenue(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        basis=basis,
    )

    previous = get_revenue(
        start_date=previous_start.isoformat(),
        end_date=previous_end.isoformat(),
        basis=basis,
    )

    def change(current_value, previous_value):
        if not previous_value:
            return None
        return (
            (current_value - previous_value)
            / abs(previous_value)
            * 100
        )

    return {
        "current": current,
        "previous": previous,
        "changes": {
            "total_sales_percent": change(
                current["total_sales"],
                previous["total_sales"],
            ),
            "ro_count_percent": change(
                current["ro_count"],
                previous["ro_count"],
            ),
            "average_ro_percent": change(
                current["average_ro"],
                previous["average_ro"],
            ),
            "labor_sales_percent": change(
                current["labor_sales"],
                previous["labor_sales"],
            ),
            "parts_sales_percent": change(
                current["parts_sales"],
                previous["parts_sales"],
            ),
            "discounts_percent": change(
                current["discounts"],
                previous["discounts"],
            ),
        },
    }


def get_dashboard_snapshot(
    start_date=None,
    end_date=None,
    basis="revenue",
):
    """
    One call for the main dashboard.

    The UI can use this object without knowing anything about SQL.
    """
    start_date, end_date = _date_range(
        start_date, end_date
    )

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
            "basis": basis,
        },
        "revenue": get_revenue(
            start_date=start_date,
            end_date=end_date,
            basis=basis,
        ),
        "monthly_trends": get_monthly_trends(
            start_date=start_date,
            end_date=end_date,
            basis=basis,
        ),
        "technicians": get_technician_metrics(
            start_date=start_date,
            end_date=end_date,
            basis=basis,
        ),
        "advisors": get_advisor_metrics(
            start_date=start_date,
            end_date=end_date,
            basis=basis,
        ),
        "job_categories": get_job_category_metrics(
            start_date=start_date,
            end_date=end_date,
            basis=basis,
        ),
        "missed_revenue": get_missed_revenue(
            start_date=start_date,
            end_date=end_date,
            basis=basis,
        ),
    }