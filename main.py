#!/usr/bin/env python3
"""
ValSkinSpy: A utility to fetch Valorant skin shop information.

This script retrieves current skin shop offers from Riot Games servers
using credentials from the local Riot Client installation.
"""

import os
from typing import List, Dict, Any
import requests
import yaml


class ValShopClient:
    """Client for retrieving Valorant shop information."""

    def __init__(self) -> None:
        """Initialize the Valorant shop client."""
        self.local_app_data = os.environ.get("LOCALAPPDATA", "")
        self.access_token = ""
        self.entitlements_token = ""
        self.puuid = ""
        self.region = ""
        self.skins = []

    def authenticate(self) -> None:
        """Authenticate with Riot servers using local client tokens."""
        print("[+] Starting authentication process...")

        settings_path = os.path.join(
            self.local_app_data,
            "Riot Games",
            "Riot Client",
            "Data",
            "RiotGamesPrivateSettings.yaml",
        )

        region_path = os.path.join(
            self.local_app_data,
            "Riot Games",
            "Riot Client",
            "Config",
            "RiotClientSettings.yaml",
        )

        print(f"[+] Reading settings from: {settings_path}")
        # Get SSID value from settings
        try:
            with open(settings_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                ssid_value = data["riot-login"]["persist"]["session"]["cookies"][1][
                    "value"
                ]
                print("[+] Successfully read SSID token")
        except (FileNotFoundError, KeyError) as e:
            raise ValueError(f"Failed to read SSID from settings: {e}") from e

        print(f"[+] Reading region from: {region_path}")
        # Get region from config
        try:
            with open(region_path, "r", encoding="utf-8") as file:
                region_data = yaml.safe_load(file)
                self.region = region_data["install"]["player-affinity"]["product"][
                    "valorant"
                ]["live"]
                print(f"[+] Successfully read region: {self.region}")
        except (FileNotFoundError, KeyError) as e:
            raise ValueError(f"Failed to read region from settings: {e}") from e

        # Get access token
        print("[+] Fetching access token...")
        auth_url = (
            "https://auth.riotgames.com/authorize?"
            "redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in&"
            "client_id=play-valorant-web-prod&"
            "response_type=token%20id_token&"
            "nonce=1&"
            "scope=account%20openid"
        )
        cookies = {"ssid": ssid_value}

        response = requests.get(auth_url, cookies=cookies, timeout=10)
        start = response.url.find("access_token=") + len("access_token=")
        end = response.url.find("&", start)
        self.access_token = response.url[start:end]

        if self.access_token:
            token_preview = f"{self.access_token[:10]}...{self.access_token[-10:]}"
            print(f"[+] Access token obtained: {token_preview}")
        else:
            print("[-] Failed to obtain access token")

        # Get entitlements token
        print("[+] Fetching entitlements token...")
        entitlements_url = "https://entitlements.auth.riotgames.com/api/token/v1"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        response = requests.post(entitlements_url, headers=headers, timeout=10)
        response_json = response.json()
        self.entitlements_token = response_json.get("entitlements_token", "")

        if self.entitlements_token:
            token_preview = (
                f"{self.entitlements_token[:10]}...{self.entitlements_token[-10:]}"
            )
            print(f"[+] Entitlements token obtained: {token_preview}")
        else:
            print("[-] Failed to obtain entitlements token")

        # Get PUUID
        print("[+] Fetching player UUID...")
        userinfo_url = "https://auth.riotgames.com/userinfo"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = requests.get(userinfo_url, headers=headers, timeout=10)
        response_json = response.json()
        self.puuid = response_json.get("sub", "")

        if self.puuid:
            puuid_preview = f"{self.puuid[:8]}...{self.puuid[-8:]}"
            print(f"[+] Player UUID obtained: {puuid_preview}")
            print("[+] Authentication completed successfully!")
        else:
            print("[-] Failed to obtain player UUID")

    def get_shop_items(self) -> List[Dict[str, Any]]:
        """
        Fetch current shop items for the authenticated user.

        Returns:
            List of dictionaries containing skin information (name, image URL, and cost)
        """
        print("\n[+] Starting shop item retrieval...")

        if not all(
            [self.access_token, self.entitlements_token, self.puuid, self.region]
        ):
            raise ValueError(
                "Authentication tokens not available. Call authenticate() first."
            )

        storefront_url = (
            f"https://pd.{self.region}.a.pvp.net/store/v3/storefront/{self.puuid}"
        )
        print(f"[+] Connecting to storefront API: {storefront_url}")

        client_platform = (
            "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJ"
            "wbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm"
            "1DaGlwc2V0IjogIlVua25vd24iDQp9"
        )
        headers = {
            "X-Riot-ClientPlatform": client_platform,
            "X-Riot-Entitlements-JWT": self.entitlements_token,
            "X-Riot-ClientVersion": "release-09.08-shipping-7-2916535",
            "Authorization": f"Bearer {self.access_token}",
        }

        response = requests.post(storefront_url, data="{}", headers=headers, timeout=10)
        print(f"[+] Storefront API response status: {response.status_code}")

        if response.status_code != 200:
            print(f"[-] Error accessing storefront: {response.text}")
            return []

        response_json = response.json()

        skins_panel = response_json.get("SkinsPanelLayout", {})
        skin_ids = skins_panel.get("SingleItemOffers", [])
        costs_data = skins_panel.get("SingleItemStoreOffers", [])

        print(f"[+] Found {len(skin_ids)} skins in your shop")

        shop_items = []

        # Get detailed information for each skin
        for i, skin_id in enumerate(skin_ids):
            if i >= len(costs_data):
                print(f"[-] Cost data missing for skin at index {i}")
                break

            print(
                f"[+] Fetching details for skin {i+1}/{len(skin_ids)} (ID: {skin_id})"
            )
            skin_url = f"https://valorant-api.com/v1/weapons/skinlevels/{skin_id}"
            response = requests.get(skin_url, timeout=10)

            if response.status_code == 200:
                skin_data = response.json().get("data", {})
                # Extract the first cost value (usually VP)
                cost = (
                    list(costs_data[i]["Cost"].values())[0]
                    if costs_data[i]["Cost"]
                    else 0
                )

                skin_name = skin_data.get("displayName", "Unknown Skin")
                print(f"    - Found: {skin_name} (Cost: {cost} VP)")

                shop_items.append(
                    {
                        "name": skin_name,
                        "image_url": skin_data.get("displayIcon", ""),
                        "cost": cost,
                    }
                )
            else:
                print(
                    f"    - Failed to get skin details. Status: {response.status_code}"
                )

        print(f"[+] Successfully retrieved {len(shop_items)} shop items")
        return shop_items


def main() -> None:
    """Main function to run the Valorant shop client."""
    print("=" * 60)
    print("ValSkinSpy: Valorant Shop Scanner")
    print("=" * 60)

    try:
        print("[+] Initializing Valorant Shop Client...")
        client = ValShopClient()

        print("\n" + "=" * 60)
        print("AUTHENTICATION PROCESS")
        print("=" * 60)
        client.authenticate()

        print("\n" + "=" * 60)
        print("SHOP ITEMS RETRIEVAL")
        print("=" * 60)
        shop_items = client.get_shop_items()

        print("\n" + "=" * 60)
        print("SUMMARY RESULTS")
        print("=" * 60)
        print(f"Found {len(shop_items)} items in your shop:")
        for i, item in enumerate(shop_items, 1):
            print(f"{i}. {item['name']} (Cost: {item['cost']} VP)")
        print("=" * 60)
        print("[+] Script completed successfully!")
    # pylint: disable=broad-exception-caught
    except Exception as e:  # Still have a fallback for truly unexpected errors
        print("\n" + "=" * 60)
        print("UNEXPECTED ERROR")
        print("=" * 60)
        print(f"[-] An unexpected error occurred: {e}")
        print("[!] Please report this issue with the error details above.")
        print("=" * 60)


if __name__ == "__main__":
    main()
