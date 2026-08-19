import os
import requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("TEKMETRIC_CLIENT_ID")
client_secret = os.getenv("TEKMETRIC_CLIENT_SECRET")

# --------------------------------------------------
# Get access token
# --------------------------------------------------

token_url = "https://shop.tekmetric.com/api/v1/oauth/token"

token_response = requests.post(
    token_url,
    auth=(client_id, client_secret),
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    data={
        "grant_type": "client_credentials"
    }
)

if not token_response.ok:
    print("Authentication failed.")
    print(token_response.text)
    exit(1)

token_data = token_response.json()
access_token = token_data["access_token"]

print("✓ Authentication successful")
print()

# --------------------------------------------------
# Get shop information
# --------------------------------------------------

shop_id = token_data["scope"]

url = f"https://shop.tekmetric.com/api/v1/shops/{shop_id}"

headers = {
    "Authorization": f"Bearer {access_token}"
}

print(f"Requesting information for Shop {shop_id}...")
print()

response = requests.get(
    url,
    headers=headers
)

print("HTTP Status:", response.status_code)
print()

if response.ok:
    print("✓ Shop request successful!")
    print()
    print(response.json())
else:
    print("Shop request failed.")
    print()
    print(response.text)