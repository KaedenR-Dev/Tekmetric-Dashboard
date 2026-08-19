from database import get_connection


def dollars(value):
    """Convert Tekmetric cents to dollars."""
    return (value or 0) / 100


def main():

    connection = get_connection()
    cursor = connection.cursor()

    print("=" * 80)
    print("COMPLETE AUTO REPAIR — POSTED / EOD ANALYSIS")
    print("=" * 80)

    # ==========================================================
    # OVERALL POSTED SALES
    # ==========================================================

    print()
    print("12-MONTH POSTED SALES")
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

    ros = row["ros"] or 0
    total = dollars(row["total"])

    print(f"Posted ROs       : {ros:,}")
    print(f"Labor Sales      : ${dollars(row['labor']):,.2f}")
    print(f"Parts Sales      : ${dollars(row['parts']):,.2f}")
    print(f"Sublet Sales     : ${dollars(row['sublet']):,.2f}")
    print(f"Discounts        : ${dollars(row['discounts']):,.2f}")
    print(f"Fees             : ${dollars(row['fees']):,.2f}")
    print(f"Taxes            : ${dollars(row['taxes']):,.2f}")
    print(f"Total Sales      : ${total:,.2f}")

    if ros:
        print(f"Average RO       : ${total / ros:,.2f}")

    # ==========================================================
    # MONTHLY POSTED SALES
    # ==========================================================

    print()
    print("MONTHLY POSTED SALES")
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
        f"{'Month':<12}"
        f"{'ROs':>8}"
        f"{'Labor':>15}"
        f"{'Parts':>15}"
        f"{'Discounts':>15}"
        f"{'Total':>15}"
        f"{'Avg RO':>15}"
    )

    print("-" * 80)

    for row in cursor.fetchall():

        row_total = dollars(row["total"])
        row_ros = row["ros"] or 0

        average_ro = (
            row_total / row_ros
            if row_ros
            else 0
        )

        print(
            f"{row['month']:<12}"
            f"{row_ros:>8,}"
            f"${dollars(row['labor']):>14,.2f}"
            f"${dollars(row['parts']):>14,.2f}"
            f"${dollars(row['discounts']):>14,.2f}"
            f"${row_total:>14,.2f}"
            f"${average_ro:>14,.2f}"
        )

    # ==========================================================
    # POSTED RO STATUS
    # ==========================================================

    print()
    print("POSTED RO STATUS")
    print("-" * 80)

    cursor.execute("""
        SELECT
            status_name,
            COUNT(*) AS count
        FROM repair_orders
        WHERE posted_date IS NOT NULL
        GROUP BY status_name
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():

        print(
            f"{str(row['status_name']):<30}"
            f"{row['count']:>8,}"
        )

    # ==========================================================
    # DAILY POSTED SALES — LAST 30 DAYS
    # ==========================================================

    print()
    print("LAST 30 DAYS — POSTED SALES")
    print("-" * 80)

    cursor.execute("""
        SELECT
            substr(posted_date, 1, 10) AS day,

            COUNT(*) AS ros,

            SUM(labor_sales) AS labor,
            SUM(parts_sales) AS parts,
            SUM(total_sales) AS total

        FROM repair_orders

        WHERE posted_date IS NOT NULL
          AND date(substr(posted_date, 1, 10))
              >= date('now', '-30 days')

        GROUP BY substr(posted_date, 1, 10)

        ORDER BY day
    """)

    print(
        f"{'Date':<14}"
        f"{'ROs':>8}"
        f"{'Labor':>15}"
        f"{'Parts':>15}"
        f"{'Total':>15}"
    )

    print("-" * 70)

    for row in cursor.fetchall():

        print(
            f"{row['day']:<14}"
            f"{row['ros']:>8,}"
            f"${dollars(row['labor']):>14,.2f}"
            f"${dollars(row['parts']):>14,.2f}"
            f"${dollars(row['total']):>14,.2f}"
        )

    # ==========================================================
    # DISCOUNT ANALYSIS
    # ==========================================================

    print()
    print("DISCOUNT ANALYSIS")
    print("-" * 80)

    cursor.execute("""
        SELECT

            SUM(labor_sales) AS labor,
            SUM(parts_sales) AS parts,

            SUM(discount_total) AS discounts,

            SUM(total_sales) AS total

        FROM repair_orders

        WHERE posted_date IS NOT NULL
    """)

    row = cursor.fetchone()

    gross_sales = (
        dollars(row["labor"])
        + dollars(row["parts"])
    )

    discounts = dollars(
        row["discounts"]
    )

    total_sales = dollars(
        row["total"]
    )

    print(
        f"Labor + Parts Gross : "
        f"${gross_sales:,.2f}"
    )

    print(
        f"Discounts           : "
        f"${discounts:,.2f}"
    )

    if gross_sales:

        print(
            f"Discount Rate       : "
            f"{discounts / gross_sales * 100:.2f}%"
        )

    print(
        f"Net Sales           : "
        f"${total_sales:,.2f}"
    )

    # ==========================================================
    # DATA COVERAGE
    # ==========================================================

    print()
    print("DATA COVERAGE")
    print("-" * 80)

    cursor.execute("""
        SELECT
            MIN(posted_date) AS earliest,
            MAX(posted_date) AS latest,
            COUNT(*) AS posted_ros
        FROM repair_orders
        WHERE posted_date IS NOT NULL
    """)

    row = cursor.fetchone()

    print(
        f"Earliest Posted RO : "
        f"{row['earliest']}"
    )

    print(
        f"Latest Posted RO   : "
        f"{row['latest']}"
    )

    print(
        f"Posted ROs         : "
        f"{row['posted_ros']:,}"
    )

    connection.close()

    print()
    print("=" * 80)
    print("POSTED / EOD ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()