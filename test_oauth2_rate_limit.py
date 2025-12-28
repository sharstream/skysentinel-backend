#!/usr/bin/env python3
"""
Test OAuth2 authentication and rate limit headers
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def test_oauth2_token():
    """Test the OAuth2 token and check rate limits"""

    token = os.getenv("OPENSKY_OAUTH2_TOKEN")
    client_id = os.getenv("OPENSKY_CLIENT_ID")
    client_secret = os.getenv("OPENSKY_CLIENT_SECRET")

    print("=" * 70)
    print("OPENSKY API OAUTH2 RATE LIMIT TEST")
    print("=" * 70)

    print(f"\nClient ID: {client_id}")
    print(f"Token present: {bool(token)}")
    print(f"Token length: {len(token) if token else 0}")

    # Test 1: Use the existing token
    print("\n" + "-" * 70)
    print("TEST 1: Using existing OAuth2 token from .env")
    print("-" * 70)

    if token:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://opensky-network.org/api/states/all"
                params = {
                    "lamin": 40.0,
                    "lomin": -74.0,
                    "lamax": 40.1,
                    "lomax": -73.9
                }

                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(url, params=params, headers=headers)

                print(f"Status Code: {response.status_code}")
                print(f"\nRate Limit Headers:")
                print(f"  X-Rate-Limit-Remaining: {response.headers.get('x-rate-limit-remaining', 'NOT PRESENT')}")
                print(f"  X-Rate-Limit-Retry-After-Seconds: {response.headers.get('x-rate-limit-retry-after-seconds', 'NOT PRESENT')}")

                # Show all rate-limit related headers
                rate_headers = {k: v for k, v in response.headers.items() if 'rate' in k.lower() or 'limit' in k.lower()}
                if rate_headers:
                    print(f"\nAll rate-limit headers found:")
                    for key, value in rate_headers.items():
                        print(f"    {key}: {value}")

                if response.status_code == 200:
                    data = response.json()
                    states_count = len(data.get('states', [])) if data.get('states') else 0
                    print(f"\n✅ Success! Retrieved {states_count} aircraft states")

                    # Check if we got the upgraded rate limit
                    remaining = response.headers.get('x-rate-limit-remaining')
                    if remaining:
                        remaining_int = int(remaining)
                        if remaining_int > 400:
                            print(f"🎉 UPGRADED RATE LIMIT CONFIRMED: {remaining_int} requests (> 400 anonymous limit)")
                        else:
                            print(f"⚠️  Using standard rate limit: {remaining_int} requests")
                elif response.status_code == 401:
                    print(f"\n❌ Token expired or invalid (401 Unauthorized)")
                    print(f"Response: {response.text[:200]}")
                else:
                    print(f"\n❌ Error: {response.status_code}")
                    print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Error: {e}")

    # Test 2: Get fresh token using client credentials
    print("\n" + "-" * 70)
    print("TEST 2: Getting fresh token using client credentials flow")
    print("-" * 70)

    if client_id and client_secret:
        try:
            async with httpx.AsyncClient() as client:
                token_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

                response = await client.post(
                    token_url,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    timeout=10.0
                )

                print(f"Token Request Status: {response.status_code}")

                if response.status_code == 200:
                    token_data = response.json()
                    new_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 0)

                    print(f"✅ Successfully obtained new token!")
                    print(f"   Expires in: {expires_in} seconds ({expires_in//60} minutes)")
                    print(f"   Token length: {len(new_token)}")

                    # Test the new token
                    print(f"\n   Testing new token with API...")
                    async with httpx.AsyncClient(timeout=30.0) as api_client:
                        url = "https://opensky-network.org/api/states/all"
                        params = {
                            "lamin": 40.0,
                            "lomin": -74.0,
                            "lamax": 40.1,
                            "lomax": -73.9
                        }

                        headers = {"Authorization": f"Bearer {new_token}"}
                        api_response = await api_client.get(url, params=params, headers=headers)

                        print(f"   API Status: {api_response.status_code}")
                        print(f"   X-Rate-Limit-Remaining: {api_response.headers.get('x-rate-limit-remaining', 'NOT PRESENT')}")

                        if api_response.status_code == 200:
                            remaining = api_response.headers.get('x-rate-limit-remaining')
                            if remaining and int(remaining) > 400:
                                print(f"   🎉 UPGRADED RATE LIMIT: {remaining} requests!")
                            else:
                                print(f"   Standard rate limit: {remaining} requests")
                else:
                    print(f"❌ Failed to get token: {response.status_code}")
                    print(f"Response: {response.text}")

        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ Client ID or Secret not configured")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_oauth2_token())
