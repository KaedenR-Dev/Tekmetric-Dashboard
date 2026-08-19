from tekmetric_api import TekmetricAPI
from database import get_connection, initialize_database
from sync_common import now, previous_year_range
from sync_jobs import sync_jobs


def sync_employees(api):
    """Download employees from Tekmetric."""

    print()
    print("Syncing employees...")

    response = api.get(
        "/employees",
        params={
            "shop": api.shop_id,
            "size": 100
        }
    )

    employees = response.get("content", [])

    connection = get_connection()
    cursor = connection.cursor()

    for employee in employees:

        role = employee.get("employeeRole") or {}

        cursor.execute("""
            INSERT OR REPLACE INTO employees (
                id,
                first_name,
                last_name,
                role_id,
                role_name,
                updated_date,
                synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            employee.get("id"),
            employee.get("firstName"),
            employee.get("lastName"),
            role.get("id"),
            role.get("name"),
            employee.get("updatedDate"),
            now()
        ))

    connection.commit()
    connection.close()

    print(f"✓ Employees synced: {len(employees)}")

    return len(employees)


def sync_repair_orders(api):
    """Download the previous 12 months of repair orders."""

    print()
    print("Syncing repair orders...")
    print("Date range: Previous 12 months")
    print()

    # Tekmetric requires full ISO-8601 UTC timestamps.
    start_datetime, end_datetime = previous_year_range()

    page = 0
    page_size = 100

    total_synced = 0
    total_pages = None

    connection = get_connection()
    cursor = connection.cursor()

    while True:

        print(f"Requesting page {page + 1}...", end=" ")

        response = api.get(
            "/repair-orders",
            params={
                "shop": api.shop_id,

                "start": start_datetime,
                "end": end_datetime,

                "size": page_size,
                "page": page,

                "sort": "createdDate",
                "sortDirection": "ASC"
            }
        )

        repair_orders = response.get("content", [])

        # Tekmetric tells us how many pages exist.
        if total_pages is None:
            total_pages = response.get("totalPages", 1)

            print(
                f"{len(repair_orders)} ROs "
                f"(Total matching: "
                f"{response.get('totalElements', 'unknown')})"
            )
        else:
            print(f"{len(repair_orders)} ROs")

        for ro in repair_orders:

            status = ro.get("repairOrderStatus") or {}
            label = ro.get("repairOrderLabel") or {}

            cursor.execute("""
                INSERT OR REPLACE INTO repair_orders (
                    id,
                    repair_order_number,
                    shop_id,

                    status_id,
                    status_code,
                    status_name,

                    label_code,
                    label_name,

                    appointment_start_time,

                    customer_id,
                    vehicle_id,

                    technician_id,
                    service_writer_id,

                    miles_in,
                    miles_out,

                    completed_date,
                    posted_date,
                    created_date,
                    updated_date,

                    labor_sales,
                    parts_sales,
                    sublet_sales,
                    discount_total,
                    fee_total,
                    taxes,
                    total_sales,

                    synced_at
                )
                VALUES (
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?,
                    ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?,
                    ?
                )
            """, (
                ro.get("id"),
                ro.get("repairOrderNumber"),
                ro.get("shopId"),

                status.get("id"),
                status.get("code"),
                status.get("name"),

                label.get("code"),
                label.get("name"),

                ro.get("appointmentStartTime"),

                ro.get("customerId"),
                ro.get("vehicleId"),

                ro.get("technicianId"),
                ro.get("serviceWriterId"),

                ro.get("milesIn"),
                ro.get("milesOut"),

                ro.get("completedDate"),
                ro.get("postedDate"),
                ro.get("createdDate"),
                ro.get("updatedDate"),

                ro.get("laborSales", 0),
                ro.get("partsSales", 0),
                ro.get("subletSales", 0),
                ro.get("discountTotal", 0),
                ro.get("feeTotal", 0),
                ro.get("taxes", 0),
                ro.get("totalSales", 0),

                now()
            ))

            total_synced += 1

        # Save this page before moving to the next one.
        connection.commit()

        page += 1

        # Stop when we've processed all pages.
        if page >= total_pages:
            break

        # Safety check in case Tekmetric returns an empty page.
        if not repair_orders:
            break

    connection.close()

    print()
    print(f"✓ Repair orders synced: {total_synced}")
    print(f"✓ Pages processed: {page}")
    print(
        f"✓ Date range: "
        f"{start_datetime} → {end_datetime}"
    )

    return total_synced


def run_full_sync():
    """
    Run the complete sync pipeline and return a stats dict describing
    what happened. This is the single entry point used both by the CLI
    (`python sync.py`) and by the dashboard's "Sync Now" button /
    background scheduler, so there's one place that defines what a
    "full sync" means.
    """

    started_at = now()

    # Make sure our database and tables exist.
    initialize_database()

    # Connect/authenticate with Tekmetric.
    api = TekmetricAPI()

    employees_synced = sync_employees(api)
    repair_orders_synced = sync_repair_orders(api)
    job_stats = sync_jobs(api)

    return {
        "started_at": started_at,
        "finished_at": now(),
        "employees_synced": employees_synced,
        "repair_orders_synced": repair_orders_synced,
        "jobs_found": job_stats["jobs_found"],
        "jobs_synced": job_stats["jobs_synced"],
        "jobs_skipped": job_stats["jobs_skipped"],
        "jobs_failed": job_stats["jobs_failed"],
        "job_errors": job_stats["errors"],
    }


def main():

    print("=" * 60)
    print("COMPLETE AUTO REPAIR — TEKMETRIC DATA SYNC")
    print("=" * 60)

    run_full_sync()

    print()
    print("=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()