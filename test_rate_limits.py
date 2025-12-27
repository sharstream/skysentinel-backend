#!/usr/bin/env python3
"""
Test script to verify rate limit header extraction from OpenSky API
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_rate_limit_headers():
    """Test that we correctly extract rate limit headers from OpenSky API"""

    # Use basic auth credentials
    username = os.getenv("OPENSKY_USERNAME")
    password = os.getenv("OPENSKY_PASSWORD")

    print("=" * 60)
    print("Testing OpenSky API Rate Limit Headers")
    print("=" * 60)

    # Test with anonymous request (no auth)
    print("\n1. Testing Anonymous Request (no authentication):")
    print("-" * 60)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use a small bounding box to minimize data
            url = "https://opensky-network.org/api/states/all"
            params = {
                "lamin": 40.0,
                "lomin": -74.0,
                "lamax": 40.1,
                "lomax": -73.9
            }

            response = await client.get(url, params=params)

            print(f"Status Code: {response.status_code}")
            print(f"X-Rate-Limit-Remaining: {response.headers.get('X-Rate-Limit-Remaining', 'NOT PRESENT')}")
            print(f"X-Rate-Limit-Retry-After-Seconds: {response.headers.get('X-Rate-Limit-Retry-After-Seconds', 'NOT PRESENT')}")

            # Show all rate-limit related headers
            rate_headers = {k: v for k, v in response.headers.items() if 'rate' in k.lower() or 'limit' in k.lower()}
            if rate_headers:
                print("\nAll rate-limit related headers:")
                for key, value in rate_headers.items():
                    print(f"  {key}: {value}")
            else:
                print("\nNo rate-limit headers found in response")

    except Exception as e:
        print(f"Error: {e}")

    # Test with basic authentication if credentials are available
    if username and password and username != "your_username_here":
        print("\n2. Testing Authenticated Request (Basic Auth):")
        print("-" * 60)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://opensky-network.org/api/states/all"
                params = {
                    "lamin": 40.0,
                    "lomin": -74.0,
                    "lamax": 40.1,
                    "lomax": -73.9
                }

                response = await client.get(
                    url,
                    params=params,
                    auth=(username, password)
                )

                print(f"Status Code: {response.status_code}")
                print(f"X-Rate-Limit-Remaining: {response.headers.get('X-Rate-Limit-Remaining', 'NOT PRESENT')}")
                print(f"X-Rate-Limit-Retry-After-Seconds: {response.headers.get('X-Rate-Limit-Retry-After-Seconds', 'NOT PRESENT')}")

                # Show all rate-limit related headers
                rate_headers = {k: v for k, v in response.headers.items() if 'rate' in k.lower() or 'limit' in k.lower()}
                if rate_headers:
                    print("\nAll rate-limit related headers:")
                    for key, value in rate_headers.items():
                        print(f"  {key}: {value}")
                else:
                    print("\nNo rate-limit headers found in response")

                if response.status_code == 200:
                    data = response.json()
                    states_count = len(data.get('states', [])) if data.get('states') else 0
                    print(f"\nSuccessfully retrieved {states_count} aircraft states")

        except httpx.HTTPStatusError as e:
            print(f"HTTP Error: {e.response.status_code}")
            if e.response.status_code == 429:
                retry_after = e.response.headers.get('X-Rate-Limit-Retry-After-Seconds')
                print(f"Rate limit hit! Retry after: {retry_after} seconds")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\n2. Skipping authenticated test (no valid credentials)")

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_rate_limit_headers())
