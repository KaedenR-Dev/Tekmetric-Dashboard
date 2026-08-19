import time

import requests

from tekmetric_api import TekmetricAPI
from database import get_connection, initialize_database
from sync_common import now, previous_year_range


PAGE_SIZE = 100
REQUEST_DELAY = 0.10
MAX_RETRIES = 3


def get_existing_job_ids():
    """Return Job IDs already stored in the database."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM jobs
    """)

    job_ids = {
        row["id"]
        for row in cursor.fetchall()
    }

    connection.close()

    return job_ids


def fetch_repair_order_page(
    api,
    start_datetime,
    end_datetime,
    page
):
    """Retrieve one page of Repair Orders."""

    return api.get(
        "/repair-orders",
        params={
            "shop": api.shop_id,
            "start": start_datetime,
            "end": end_datetime,
            "size": PAGE_SIZE,
            "page": page,
            "sort": "createdDate",
            "sortDirection": "ASC"
        }
    )


def fetch_job(api, job_id):
    """Retrieve a complete Job with retry handling."""

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            return api.get(
                f"/jobs/{job_id}"
            )

        except requests.exceptions.HTTPError as error:

            response = error.response

            if response is None:
                raise

            status = response.status_code

            # ------------------------------------------
            # Rate limit
            # ------------------------------------------

            if status == 429:

                retry_after = response.headers.get(
                    "Retry-After",
                    "2"
                )

                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = 2

                print(
                    f"      Rate limited. "
                    f"Waiting {wait:g}s..."
                )

                time.sleep(wait)

                continue

            # ------------------------------------------
            # Temporary server error
            # ------------------------------------------

            if status >= 500:

                wait = attempt * 2

                print(
                    f"      Server error {status}. "
                    f"Retrying in {wait}s..."
                )

                time.sleep(wait)

                continue

            raise

    raise RuntimeError(
        f"Job {job_id} failed after "
        f"{MAX_RETRIES} attempts."
    )


def save_job(job):
    """Save a complete Job and its children."""

    connection = get_connection()
    cursor = connection.cursor()

    # ==================================================
    # JOB
    # ==================================================

    cursor.execute("""
        INSERT OR REPLACE INTO jobs (
            id,
            repair_order_id,
            vehicle_id,
            customer_id,

            name,

            authorized,
            authorized_date,
            selected,

            technician_id,

            note,
            job_category_name,

            parts_total,
            labor_total,
            discount_total,
            fee_total,
            subtotal,

            archived,

            created_date,
            updated_date,
            completed_date,

            labor_hours,

            synced_at
        )
        VALUES (
            ?, ?, ?, ?,
            ?,
            ?, ?, ?,
            ?,
            ?, ?,
            ?, ?, ?, ?, ?,
            ?,
            ?, ?, ?,
            ?,
            ?
        )
    """, (
        job.get("id"),
        job.get("repairOrderId"),
        job.get("vehicleId"),
        job.get("customerId"),

        job.get("name"),

        int(bool(
            job.get("authorized")
        )),

        job.get("authorizedDate"),

        int(bool(
            job.get("selected")
        )),

        job.get("technicianId"),

        job.get("note"),
        job.get("jobCategoryName"),

        job.get("partsTotal", 0),
        job.get("laborTotal", 0),
        job.get("discountTotal", 0),
        job.get("feeTotal", 0),
        job.get("subtotal", 0),

        int(bool(
            job.get("archived")
        )),

        job.get("createdDate"),
        job.get("updatedDate"),
        job.get("completedDate"),

        job.get("laborHours", 0),

        now()
    ))

    # ==================================================
    # LABOR
    # ==================================================

    for labor in job.get("labor", []):

        cursor.execute("""
            INSERT OR REPLACE INTO labor_lines (
                id,
                job_id,
                name,
                rate,
                hours,
                complete,
                technician_id,
                synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            labor.get("id"),
            job.get("id"),
            labor.get("name"),
            labor.get("rate", 0),
            labor.get("hours", 0),
            int(bool(
                labor.get("complete")
            )),
            labor.get("technicianId"),
            now()
        ))

    # ==================================================
    # PARTS
    # ==================================================

    for part in job.get("parts", []):

        cursor.execute("""
            INSERT OR REPLACE INTO parts (
                id,
                job_id,
                quantity,
                brand,
                name,
                part_number,
                description,
                cost,
                retail,
                synced_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            part.get("id"),
            job.get("id"),
            part.get("quantity", 0),
            part.get("brand"),
            part.get("name"),
            part.get("partNumber"),
            part.get("description"),
            part.get("cost", 0),
            part.get("retail", 0),
            now()
        ))

    connection.commit()
    connection.close()


def sync_jobs(api):
    """Synchronize all Jobs from the previous 12 months."""

    print()
    print("=" * 60)
    print("COMPLETE AUTO REPAIR — JOB SYNC")
    print("=" * 60)
    print()

    start_datetime, end_datetime = previous_year_range()

    existing_job_ids = get_existing_job_ids()

    print(
        f"Jobs already in database: "
        f"{len(existing_job_ids)}"
    )

    print(
        f"Date range: "
        f"{start_datetime} → {end_datetime}"
    )

    print()

    # ----------------------------------------------
    # Get first page to determine pagination
    # ----------------------------------------------

    print("Checking Repair Order count...")

    first_response = fetch_repair_order_page(
        api,
        start_datetime,
        end_datetime,
        0
    )

    total_ros = first_response.get(
        "totalElements",
        0
    )

    total_pages = first_response.get(
        "totalPages",
        1
    )

    print(f"Repair Orders: {total_ros}")
    print(f"Pages: {total_pages}")
    print()

    jobs_found = 0
    jobs_synced = 0
    jobs_skipped = 0
    jobs_failed = 0

    errors = []

    # ----------------------------------------------
    # Process every RO page
    # ----------------------------------------------

    for page in range(total_pages):

        print(
            f"[Page {page + 1}/{total_pages}]"
        )

        if page == 0:

            response = first_response

        else:

            response = fetch_repair_order_page(
                api,
                start_datetime,
                end_datetime,
                page
            )

        repair_orders = response.get(
            "content",
            []
        )

        for ro in repair_orders:

            ro_number = ro.get(
                "repairOrderNumber"
            )

            jobs = ro.get("jobs") or []

            if not jobs:
                continue

            for job_summary in jobs:

                job_id = job_summary.get("id")

                if not job_id:
                    continue

                jobs_found += 1

                # ----------------------------------
                # Skip Jobs we've already downloaded
                # ----------------------------------

                if job_id in existing_job_ids:

                    jobs_skipped += 1
                    continue

                print(
                    f"  RO #{ro_number} "
                    f"→ Job {job_id}"
                )

                try:

                    job = fetch_job(
                        api,
                        job_id
                    )

                    save_job(job)

                    existing_job_ids.add(
                        job_id
                    )

                    jobs_synced += 1

                    print(
                        f"      ✓ Saved"
                    )

                    time.sleep(
                        REQUEST_DELAY
                    )

                except Exception as error:

                    jobs_failed += 1

                    errors.append({
                        "repair_order": ro_number,
                        "job_id": job_id,
                        "error": str(error)
                    })

                    print(
                        f"      ✗ FAILED: "
                        f"{error}"
                    )

    # ----------------------------------------------
    # Final report
    # ----------------------------------------------

    print()
    print("=" * 60)
    print("JOB SYNC COMPLETE")
    print("=" * 60)

    print(
        f"Jobs found:       {jobs_found}"
    )

    print(
        f"Jobs synced:      {jobs_synced}"
    )

    print(
        f"Jobs skipped:     {jobs_skipped}"
    )

    print(
        f"Jobs failed:      {jobs_failed}"
    )

    print()

    if errors:

        print("ERRORS")
        print("-" * 60)

        for error in errors[:25]:

            print(
                f"RO #{error['repair_order']} "
                f"| Job {error['job_id']} "
                f"| {error['error']}"
            )

        if len(errors) > 25:

            print(
                f"...and "
                f"{len(errors) - 25} more."
            )

    else:

        print("✓ No errors")

    return {
        "jobs_found": jobs_found,
        "jobs_synced": jobs_synced,
        "jobs_skipped": jobs_skipped,
        "jobs_failed": jobs_failed,
        "errors": errors[:25],
    }


def main():

    initialize_database()

    api = TekmetricAPI()

    sync_jobs(api)


if __name__ == "__main__":
    main()