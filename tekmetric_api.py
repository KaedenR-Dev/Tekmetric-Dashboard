import os
import requests
from dotenv import load_dotenv

load_dotenv()


class TekmetricAPI:

    def __init__(self):
        self.client_id = os.getenv("TEKMETRIC_CLIENT_ID")
        self.client_secret = os.getenv("TEKMETRIC_CLIENT_SECRET")

        self.base_url = "https://shop.tekmetric.com/api/v1"

        self.access_token = None
        self.shop_id = None

        self.authenticate()

    def authenticate(self):
        """Get an access token from Tekmetric."""

        url = f"{self.base_url}/oauth/token"

        response = requests.post(
            url,
            auth=(self.client_id, self.client_secret),
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "client_credentials"
            }
        )

        response.raise_for_status()

        data = response.json()

        self.access_token = data["access_token"]
        self.shop_id = data["scope"]

        print("✓ Tekmetric authentication successful")
        print(f"✓ Shop ID: {self.shop_id}")

    def get(self, endpoint, params=None):
        """Make an authenticated GET request."""

        url = f"{self.base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        response.raise_for_status()

        return response.json()