from database import get_connection


def main():

    connection = get_connection()
    cursor = connection.cursor()

    print("=" * 70)
    print("COMPLETE AUTO REPAIR — DATABASE INSPECTION")
    print("=" * 70)

    # --------------------------------------------------
    # BASIC COUNTS
    # --------------------------------------------------

    tables = [
        ("employees", "Employees"),
        ("repair_orders", "Repair Orders"),
        ("jobs", "Jobs"),
        ("labor_lines", "Labor Lines"),
        ("parts", "Parts"),
    ]

    print()
    print("RECORD COUNTS")
    print("-" * 70)

    for table, label in tables:

        cursor.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        )

        count = cursor.fetchone()["count"]

        print(f"{label:<20}: {count:,}")

    # --------------------------------------------------
    # REPAIR ORDER STATUS
    # --------------------------------------------------

    print()
    print("REPAIR ORDER STATUS")
    print("-" * 70)

    cursor.execute("""
        SELECT
            status_name,
            COUNT(*) AS count
        FROM repair_orders
        GROUP BY status_name
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():

        print(
            f"{str(row['status_name']):<25} "
            f"{row['count']:,}"
        )

    # --------------------------------------------------
    # JOB CATEGORIES
    # --------------------------------------------------

    print()
    print("JOB CATEGORIES")
    print("-" * 70)

    cursor.execute("""
        SELECT
            job_category_name,
            COUNT(*) AS count
        FROM jobs
        GROUP BY job_category_name
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():

        print(
            f"{str(row['job_category_name']):<35} "
            f"{row['count']:,}"
        )

    # --------------------------------------------------
    # TECHNICIAN JOB COUNTS
    # --------------------------------------------------

    print()
    print("TECHNICIAN JOB COUNTS")
    print("-" * 70)

    cursor.execute("""
        SELECT
            e.id,
            e.first_name,
            e.last_name,
            COUNT(j.id) AS jobs
        FROM employees e
        LEFT JOIN jobs j
            ON j.technician_id = e.id
        WHERE LOWER(e.role_name) = 'technician'
        GROUP BY
            e.id,
            e.first_name,
            e.last_name
        ORDER BY jobs DESC
    """)

    for row in cursor.fetchall():

        name = (
            f"{row['first_name']} "
            f"{row['last_name']}"
        )

        print(
            f"{name:<30} "
            f"{row['jobs']:,} jobs"
        )

    # --------------------------------------------------
    # TECHNICIAN LABOR HOURS
    # --------------------------------------------------

    print()
    print("TECHNICIAN LABOR HOURS")
    print("-" * 70)

    cursor.execute("""
        SELECT
            e.id,
            e.first_name,
            e.last_name,
            SUM(ll.hours) AS hours
        FROM employees e
        LEFT JOIN labor_lines ll
            ON ll.technician_id = e.id
        WHERE LOWER(e.role_name) = 'technician'
        GROUP BY
            e.id,
            e.first_name,
            e.last_name
        ORDER BY hours DESC
    """)

    for row in cursor.fetchall():

        name = (
            f"{row['first_name']} "
            f"{row['last_name']}"
        )

        hours = row["hours"] or 0

        print(
            f"{name:<30} "
            f"{hours:,.2f} hours"
        )

    # --------------------------------------------------
    # SALES
    # --------------------------------------------------

    print()
    print("12-MONTH SALES")
    print("-" * 70)

    cursor.execute("""
        SELECT
            SUM(labor_sales) AS labor,
            SUM(parts_sales) AS parts,
            SUM(sublet_sales) AS sublet,
            SUM(discount_total) AS discounts,
            SUM(fee_total) AS fees,
            SUM(taxes) AS taxes,
            SUM(total_sales) AS total
        FROM repair_orders
    """)

    row = cursor.fetchone()

    def dollars(value):
        return f"${(value or 0) / 100:,.2f}"

    print(f"Labor Sales       : {dollars(row['labor'])}")
    print(f"Parts Sales       : {dollars(row['parts'])}")
    print(f"Sublet Sales      : {dollars(row['sublet'])}")
    print(f"Discounts         : {dollars(row['discounts'])}")
    print(f"Fees              : {dollars(row['fees'])}")
    print(f"Taxes             : {dollars(row['taxes'])}")
    print(f"Total Sales       : {dollars(row['total'])}")

    # --------------------------------------------------
    # MONTHLY SALES
    # --------------------------------------------------

    print()
    print("MONTHLY SALES")
    print("-" * 70)

    cursor.execute("""
        SELECT
            substr(created_date, 1, 7) AS month,
            COUNT(*) AS repair_orders,
            SUM(labor_sales) AS labor,
            SUM(parts_sales) AS parts,
            SUM(total_sales) AS total
        FROM repair_orders
        GROUP BY substr(created_date, 1, 7)
        ORDER BY month
    """)

    print(
        f"{'Month':<12}"
        f"{'ROs':>8}"
        f"{'Labor':>15}"
        f"{'Parts':>15}"
        f"{'Total':>15}"
    )

    print("-" * 70)

    for row in cursor.fetchall():

        print(
            f"{row['month']:<12}"
            f"{row['repair_orders']:>8,}"
            f"{dollars(row['labor']):>15}"
            f"{dollars(row['parts']):>15}"
            f"{dollars(row['total']):>15}"
        )

    # --------------------------------------------------
    # DATA INTEGRITY
    # --------------------------------------------------

    print()
    print("DATA INTEGRITY")
    print("-" * 70)

    cursor.execute("""
        SELECT COUNT(*)
        FROM jobs j
        LEFT JOIN repair_orders r
            ON j.repair_order_id = r.id
        WHERE r.id IS NULL
    """)

    orphan_jobs = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM labor_lines l
        LEFT JOIN jobs j
            ON l.job_id = j.id
        WHERE j.id IS NULL
    """)

    orphan_labor = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM parts p
        LEFT JOIN jobs j
            ON p.job_id = j.id
        WHERE j.id IS NULL
    """)

    orphan_parts = cursor.fetchone()[0]

    print(f"Orphan Jobs        : {orphan_jobs:,}")
    print(f"Orphan Labor Lines : {orphan_labor:,}")
    print(f"Orphan Parts       : {orphan_parts:,}")

    connection.close()

    print()
    print("=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()