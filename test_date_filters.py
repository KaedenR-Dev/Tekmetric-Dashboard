from tekmetric_api import TekmetricAPI

api = TekmetricAPI()

tests = [
    (
        "No dates",
        {
            "shop": api.shop_id,
            "size": 5
        }
    ),
    (
        "Start only",
        {
            "shop": api.shop_id,
            "start": "2025-08-09",
            "size": 5
        }
    ),
    (
        "End only",
        {
            "shop": api.shop_id,
            "end": "2026-08-09",
            "size": 5
        }
    ),
    (
        "Start + End",
        {
            "shop": api.shop_id,
            "start": "2025-08-09",
            "end": "2026-08-09",
            "size": 5
        }
    ),
]


for name, params in tests:

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)
    print("Parameters:", params)

    try:

        response = api.get(
            "/repair-orders",
            params=params
        )

        records = response.get("content", [])

        print("✓ SUCCESS")
        print(f"Records returned: {len(records)}")

        if "totalElements" in response:
            print(f"Total matching records: {response['totalElements']}")

    except Exception as e:

        print("✗ FAILED")
        print(str(e))