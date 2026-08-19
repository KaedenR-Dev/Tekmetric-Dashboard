from tekmetric_api import TekmetricAPI

api = TekmetricAPI()

tests = [
    (
        "ISO timestamp UTC",
        {
            "shop": api.shop_id,
            "start": "2025-08-09T00:00:00Z",
            "end": "2026-08-09T23:59:59Z",
            "size": 5
        }
    ),
    (
        "ISO timestamp without Z",
        {
            "shop": api.shop_id,
            "start": "2025-08-09T00:00:00",
            "end": "2026-08-09T23:59:59",
            "size": 5
        }
    ),
    (
        "US date/time",
        {
            "shop": api.shop_id,
            "start": "08/09/2025",
            "end": "08/09/2026",
            "size": 5
        }
    ),
]


for name, params in tests:

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    print("Parameters:")
    print(params)

    try:

        response = api.get(
            "/repair-orders",
            params=params
        )

        records = response.get("content", [])

        print("✓ SUCCESS")
        print(f"Records returned: {len(records)}")
        print(f"Total records: {response.get('totalElements')}")

    except Exception as e:

        print("✗ FAILED")
        print(str(e))