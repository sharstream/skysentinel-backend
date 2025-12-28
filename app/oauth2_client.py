"""
OAuth2 Client for OpenSky Network API
Handles token acquisition, refresh, and automatic retry using client credentials flow
"""

import os
from typing import Optional, Callable, Any
import httpx
from datetime import datetime, timedelta
import asyncio


class OpenSkyOAuth2Client:
    """
    Manages OAuth2 authentication for OpenSky Network API with automatic token refresh
    and resilient error handling
    """

    TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    TOKEN_EXPIRY_BUFFER = 300  # Refresh token 5 minutes before expiry
    MAX_RETRIES = 2  # Maximum number of retries on 401

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize OAuth2 client with automatic token management

        Args:
            client_id: OAuth2 client ID from OpenSky account
            client_secret: OAuth2 client secret from OpenSky account
        """
        self.client_id = client_id or os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("OPENSKY_CLIENT_SECRET")
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._token_lock = asyncio.Lock()  # Prevent concurrent token refresh

    def is_configured(self) -> bool:
        """Check if OAuth2 credentials are configured"""
        return bool(self.client_id and self.client_secret and
                   self.client_id != "your_client_id_here" and
                   self.client_secret != "your_client_secret_here")

    def is_token_valid(self) -> bool:
        """Check if current token is still valid (with buffer)"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at

    async def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get a valid access token, requesting a new one if needed

        Args:
            force_refresh: Force token refresh even if current token is valid

        Returns:
            Access token string or None if OAuth2 is not configured
        """
        if not self.is_configured():
            return None

        # Use lock to prevent multiple simultaneous token refreshes
        async with self._token_lock:
            if force_refresh or not self.is_token_valid():
                return await self._request_token()

            return self.access_token

    async def _request_token(self) -> Optional[str]:
        """
        Request a new access token from OpenSky OAuth2 server

        Returns:
            Access token string or None on failure
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 1800)  # Default 30 minutes

                    # Set expiry time with buffer
                    self.token_expires_at = datetime.now() + timedelta(
                        seconds=expires_in - self.TOKEN_EXPIRY_BUFFER
                    )

                    print(f"✅ OAuth2 token refreshed. Expires in {expires_in//60} minutes")
                    return self.access_token
                else:
                    print(f"❌ OAuth2 token request failed: {response.status_code} {response.text}")
                    return None

        except Exception as e:
            print(f"❌ Error requesting OAuth2 token: {e}")
            return None

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an API call with automatic token refresh on 401 errors

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the function call

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                result = await func(*args, **kwargs)
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401 and attempt < self.MAX_RETRIES - 1:
                    print(f"⚠️  401 Unauthorized - Refreshing token (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    # Force token refresh
                    await self.get_access_token(force_refresh=True)
                    # Retry with new token
                    continue
                raise
            except Exception as e:
                raise

        raise Exception("Max retries exceeded")

    def get_auth_headers(self) -> dict:
        """
        Get authorization headers for API requests

        Returns:
            Dictionary with Authorization header if token is available
        """
        if self.access_token and self.is_token_valid():
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}
