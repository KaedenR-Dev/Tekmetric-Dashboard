import os
import requests
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

client_id = os.getenv("TEKMETRIC_CLIENT_ID")
client_secret = os.getenv("TEKMETRIC_CLIENT_SECRET")

# Make sure credentials exist
if not client_id or not client_secret:
    print("ERROR: Tekmetric credentials were not found.")
    print("Check your .env file.")
    exit(1)

# Tekmetric authentication endpoint
url = "https://shop.tekmetric.com/api/v1/oauth/token"

print("Connecting to Tekmetric...")
print()

response = requests.post(
    url,
    auth=(client_id, client_secret),
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    data={
        "grant_type": "client_credentials"
    }
)

print("HTTP Status:", response.status_code)
print()

if response.ok:
    data = response.json()

    print("SUCCESS! Tekmetric authentication worked.")
    print()
    print("Token Type:", data.get("token_type"))
    print("Scope:", data.get("scope"))
    print()
    print("Access token received successfully.")
    print("(The token itself is intentionally not displayed.)")

else:
    print("AUTHENTICATION FAILED")
    print()
    print("Tekmetric response:")
    print(response.text)