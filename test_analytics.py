from analytics import (
    get_revenue,
    get_monthly_trends,
    get_technician_metrics,
    get_advisor_metrics,
)


def money(value):
    return f"${value:,.2f}"


def main():

    print("=" * 80)
    print("COMPLETE AUTO REPAIR — ANALYTICS TEST")
    print("=" * 80)

    # ----------------------------------------------------------
    # 1. CURRENT 12-MONTH REVENUE
    # ----------------------------------------------------------

    print()
    print("12-MONTH REVENUE")
    print("-" * 80)

    revenue = get_revenue(days=365, basis="revenue")

    print(f"Period       : {revenue['start_date']} -> {revenue['end_date']}")
    print(f"Posted ROs   : {revenue['ro_count']:,}")
    print(f"Total Sales  : {money(revenue['total_sales'])}")
    print(f"Labor Sales  : {money(revenue['labor_sales'])}")
    print(f"Parts Sales  : {money(revenue['parts_sales'])}")
    print(f"Discounts    : {money(revenue['discounts'])}")
    print(f"Average RO   : {money(revenue['average_ro'])}")

    # ----------------------------------------------------------
    # 2. MONTHLY TREND
    # ----------------------------------------------------------

    print()
    print("MONTHLY TREND")
    print("-" * 80)

    trends = get_monthly_trends(
        start_date=revenue["start_date"],
        end_date=revenue["end_date"],
        basis="revenue",
    )

    print(
        f"{'Month':<10}"
        f"{'ROs':>8}"
        f"{'Labor':>15}"
        f"{'Parts':>15}"
        f"{'Total':>15}"
        f"{'Avg RO':>15}"
    )

    print("-" * 80)

    for row in trends:
        print(
            f"{row['month']:<10}"
            f"{row['ro_count']:>8,}"
            f"{money(row['labor_sales']):>15}"
            f"{money(row['parts_sales']):>15}"
            f"{money(row['total_sales']):>15}"
            f"{money(row['average_ro']):>15}"
        )

    # ----------------------------------------------------------
    # 3. TECHNICIANS
    # ----------------------------------------------------------

    print()
    print("TECHNICIAN METRICS")
    print("-" * 80)

    technicians = get_technician_metrics(
        start_date=revenue["start_date"],
        end_date=revenue["end_date"],
        basis="revenue",
    )

    print(
        f"{'Technician':<28}"
        f"{'Jobs':>8}"
        f"{'Hours':>12}"
        f"{'Labor Sales':>16}"
    )

    print("-" * 70)

    for row in technicians:
        print(
            f"{row['technician_name']:<28}"
            f"{row['jobs']:>8,}"
            f"{row['labor_hours']:>12.2f}"
            f"{money(row['labor_sales']):>16}"
        )

    # ----------------------------------------------------------
    # 4. SERVICE ADVISORS
    # ----------------------------------------------------------

    print()
    print("SERVICE ADVISOR METRICS")
    print("-" * 80)

    advisors = get_advisor_metrics(
        start_date=revenue["start_date"],
        end_date=revenue["end_date"],
        basis="revenue",
    )

    print(
        f"{'Advisor':<28}"
        f"{'ROs':>8}"
        f"{'Sales':>16}"
        f"{'Avg RO':>16}"
    )

    print("-" * 70)

    for row in advisors:
        print(
            f"{row['advisor_name']:<28}"
            f"{row['ro_count']:>8,}"
            f"{money(row['total_sales']):>16}"
            f"{money(row['average_ro']):>16}"
        )

    print()
    print("=" * 80)
    print("ANALYTICS TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()