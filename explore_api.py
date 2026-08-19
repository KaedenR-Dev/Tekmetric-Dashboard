from tekmetric_api import TekmetricAPI
import json

api = TekmetricAPI()

print()
print("Shop Information")
print("=" * 50)

shop = api.get(f"/shops/{api.shop_id}")

print(json.dumps(shop, indent=4))