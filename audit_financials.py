from database import get_connection


def dollars(value):
    return (value or 0) / 100


def main():

    connection = get_connection()
    cursor = connection.cursor()

    print("=" * 80)
    print("COMPLETE AUTO REPAIR — FINANCIAL AUDIT")
    print("=" * 80)

    # ==========================================================
    # 1. OVERALL FINANCIAL RECONCILIATION
    # ==========================================================

    print()
    print("OVERALL RECONCILIATION")
    print("-" * 80)

    cursor.execute("""
        SELECT
            COUNT(*) AS ros,
            SUM(labor_sales) AS labor,
            SUM(parts_sales) AS parts,
            SUM(sublet_sales) AS sublet,
            SUM(discount_total) AS discounts,
            SUM(fee_total) AS fees,
            SUM(taxes) AS taxes,
            SUM(total_sales) AS total
        FROM repair_orders
        WHERE posted_date IS NOT NULL
    """)

    row = cursor.fetchone()

    labor = dollars(row["labor"])
    parts = dollars(row["parts"])
    sublet = dollars(row["sublet"])
    discounts = dollars(row["discounts"])
    fees = dollars(row["fees"])
    taxes = dollars(row["taxes"])
    total = dollars(row["total"])

    calculated_total = (
        labor + parts + sublet + fees + taxes - discounts
    )

    difference = total - calculated_total

    print(f"Posted ROs              : {row['ros']:,}")
    print()
    print(f"Labor Sales              : ${labor:,.2f}")
    print(f"Parts Sales              : ${parts:,.2f}")
    print(f"Sublet Sales             : ${sublet:,.2f}")
    print(f"Fees                     : ${fees:,.2f}")
    print(f"Taxes                    : ${taxes:,.2f}")
    print(f"Discounts                : ${discounts:,.2f}")
    print("-" * 40)
    print(f"Calculated Total         : ${calculated_total:,.2f}")
    print(f"Tekmetric Total Sales    : ${total:,.2f}")
    print(f"UNEXPLAINED DIFFERENCE   : ${difference:,.2f}")

    # ==========================================================
    # 2. ALTERNATIVE RECONCILIATIONS
    # ==========================================================

    print()
    print("ALTERNATIVE RECONCILIATIONS")
    print("-" * 80)

    print(f"Labor + Parts                      : ${labor + parts:,.2f}")
    print(f"Labor + Parts + Sublet             : ${labor + parts + sublet:,.2f}")
    print(f"Labor + Parts + Sublet + Fees      : ${labor + parts + sublet + fees:,.2f}")
    print(f"Above + Taxes                      : ${labor + parts + sublet + fees + taxes:,.2f}")
    print(f"Above - Discounts                  : ${calculated_total:,.2f}")

    # ==========================================================
    # 3. DISCREPANCY BY MONTH
    # ==========================================================

    print()
    print("MONTHLY RECONCILIATION")
    print("-" * 80)

    cursor.execute("""
        SELECT
            substr(posted_date, 1, 7) AS month,
            COUNT(*) AS ros,
            SUM(labor_sales) AS labor,
            SUM(parts_sales) AS parts,
            SUM(sublet_sales) AS sublet,
            SUM(discount_total) AS discounts,
            SUM(fee_total) AS fees,
            SUM(taxes) AS taxes,
            SUM(total_sales) AS total
        FROM repair_orders
        WHERE posted_date IS NOT NULL
        GROUP BY substr(posted_date, 1, 7)
        ORDER BY month
    """)

    print(
        f"{'Month':<10}"
        f"{'ROs':>7}"
        f"{'Calculated':>17}"
        f"{'Tekmetric':>17}"
        f"{'Difference':>17}"
    )

    print("-" * 70)

    for row in cursor.fetchall():

        monthly_calculated = (
            dollars(row["labor"])
            + dollars(row["parts"])
            + dollars(row["sublet"])
            + dollars(row["fees"])
            + dollars(row["taxes"])
            - dollars(row["discounts"])
        )

        monthly_total = dollars(row["total"])
        monthly_difference = monthly_total - monthly_calculated

        print(
            f"{row['month']:<10}"
            f"{row['ros']:>7,}"
            f"${monthly_calculated:>16,.2f}"
            f"${monthly_total:>16,.2f}"
            f"${monthly_difference:>16,.2f}"
        )

    # ==========================================================
    # 4. FIND REPAIR ORDERS WITH A FINANCIAL DISCREPANCY
    # ==========================================================

    print()
    print("LARGEST REPAIR ORDER DISCREPANCIES")
    print("-" * 80)

    cursor.execute("""
        SELECT
            repair_order_number,
            posted_date,
            labor_sales,
            parts_sales,
            sublet_sales,
            discount_total,
            fee_total,
            taxes,
            total_sales
        FROM repair_orders
        WHERE posted_date IS NOT NULL
    """)

    discrepancies = []

    for row in cursor.fetchall():

        calculated = (
            dollars(row["labor_sales"])
            + dollars(row["parts_sales"])
            + dollars(row["sublet_sales"])
            + dollars(row["fee_total"])
            + dollars(row["taxes"])
            - dollars(row["discount_total"])
        )

        actual = dollars(row["total_sales"])
        difference = actual - calculated

        if abs(difference) > 0.01:
            discrepancies.append({
                "ro": row["repair_order_number"],
                "posted": row["posted_date"],
                "calculated": calculated,
                "actual": actual,
                "difference": difference
            })

    discrepancies.sort(
        key=lambda x: abs(x["difference"]),
        reverse=True
    )

    print(
        f"{'RO':<10}"
        f"{'Posted':<22}"
        f"{'Calculated':>15}"
        f"{'Tekmetric':>15}"
        f"{'Difference':>15}"
    )

    print("-" * 80)

    for item in discrepancies[:25]:

        print(
            f"{str(item['ro']):<10}"
            f"{str(item['posted']):<22}"
            f"${item['calculated']:>14,.2f}"
            f"${item['actual']:>14,.2f}"
            f"${item['difference']:>14,.2f}"
        )

    print()
    print(
        f"Repair Orders with discrepancies: "
        f"{len(discrepancies):,}"
    )

    # ==========================================================
    # 5. LOOK FOR COMMON DIFFERENCE AMOUNTS
    # ==========================================================

    print()
    print("COMMON DISCREPANCY AMOUNTS")
    print("-" * 80)

    difference_counts = {}

    for item in discrepancies:

        rounded = round(item["difference"], 2)

        difference_counts[rounded] = (
            difference_counts.get(rounded, 0) + 1
        )

    common = sorted(
        difference_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for difference_amount, count in common[:20]:

        print(
            f"${difference_amount:>12,.2f}"
            f"   {count:,} ROs"
        )

    # ==========================================================
    # 6. CHECK FOR OTHER FINANCIAL COLUMNS
    # ==========================================================

    print()
    print("DATABASE FINANCIAL COLUMNS")
    print("-" * 80)

    cursor.execute("""
        PRAGMA table_info(repair_orders)
    """)

    columns = cursor.fetchall()

    financial_keywords = [
        "sale",
        "discount",
        "fee",
        "tax",
        "sublet",
        "labor",
        "part",
        "total",
        "cost"
    ]

    found_columns = []

    for column in columns:

        column_name = column["name"]

        if any(
            keyword in column_name.lower()
            for keyword in financial_keywords
        ):
            found_columns.append(column_name)

    for column_name in found_columns:
        print(column_name)

    # ==========================================================
    # 7. JOB-LEVEL FINANCIAL TOTALS
    # ==========================================================

    print()
    print("JOB-LEVEL FINANCIAL TOTALS")
    print("-" * 80)

    # IMPORTANT:
    # Prefix job-level financial columns with j.
    # Both jobs and repair_orders contain some similarly
    # named columns, so leaving them unqualified causes
    # SQLite's "ambiguous column name" error.

    cursor.execute("""
        SELECT
            SUM(j.labor_total) AS labor,
            SUM(j.parts_total) AS parts,
            SUM(j.discount_total) AS discounts,
            SUM(j.fee_total) AS fees,
            SUM(j.subtotal) AS subtotal
        FROM jobs j
        INNER JOIN repair_orders r
            ON j.repair_order_id = r.id
        WHERE r.posted_date IS NOT NULL
    """)

    row = cursor.fetchone()

    job_labor = dollars(row["labor"])
    job_parts = dollars(row["parts"])
    job_discounts = dollars(row["discounts"])
    job_fees = dollars(row["fees"])
    job_subtotal = dollars(row["subtotal"])

    print(f"Job Labor Total       : ${job_labor:,.2f}")
    print(f"Job Parts Total       : ${job_parts:,.2f}")
    print(f"Job Discounts         : ${job_discounts:,.2f}")
    print(f"Job Fees              : ${job_fees:,.2f}")
    print(f"Job Subtotal          : ${job_subtotal:,.2f}")

    # ==========================================================
    # 8. FINAL CONCLUSION
    # ==========================================================

    print()
    print("=" * 80)

    if abs(difference) < 0.01:

        print("✓ FINANCIALS RECONCILE")

    else:

        print(
            f"⚠ UNEXPLAINED DIFFERENCE: "
            f"${difference:,.2f}"
        )

        print()
        print(
            "We need to identify the missing Tekmetric "
            "financial component before using calculated "
            "totals in the dashboard."
        )

    print("=" * 80)

    connection.close()


if __name__ == "__main__":
    main()