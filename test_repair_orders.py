from tekmetric_api import TekmetricAPI
import json

api = TekmetricAPI()

print()
print("Fetching recent Repair Orders...")
print("=" * 60)

params = {
    "shop": api.shop_id,
    "size": 5,
    "sort": "createdDate",
    "sortDirection": "DESC"
}

response = api.get("/repair-orders", params=params)

print()
print(f"Total matching records: {response.get('totalElements')}")
print(f"Records returned: {len(response.get('content', []))}")
print()

for ro in response.get("content", []):

    print("-" * 60)

    print(f"RO #:          {ro.get('repairOrderNumber')}")
    print(f"RO ID:         {ro.get('id')}")
    print(f"Status:        {ro.get('repairOrderStatus', {}).get('name')}")
    print(f"Created:       {ro.get('createdDate')}")
    print(f"Completed:     {ro.get('completedDate')}")
    print(f"Posted:        {ro.get('postedDate')}")

    print()
    print("FINANCIALS")
    print(f"  Labor:       ${ro.get('laborSales', 0):,.2f}")
    print(f"  Parts:       ${ro.get('partsSales', 0):,.2f}")
    print(f"  Sublet:      ${ro.get('subletSales', 0):,.2f}")
    print(f"  Discounts:   ${ro.get('discountTotal', 0):,.2f}")
    print(f"  Fees:        ${ro.get('feeTotal', 0):,.2f}")
    print(f"  Taxes:       ${ro.get('taxes', 0):,.2f}")
    print(f"  TOTAL:       ${ro.get('totalSales', 0):,.2f}")

    print()
    print(f"Technician ID:  {ro.get('technicianId')}")
    print(f"Service Writer:  {ro.get('serviceWriterId')}")

    jobs = ro.get("jobs", [])

    print()
    print(f"Jobs: {len(jobs)}")

    for job in jobs:
        print(f"  • {job.get('name')}")

print()
print("=" * 60)
print("Done.")