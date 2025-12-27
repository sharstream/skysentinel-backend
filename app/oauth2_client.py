"""
OAuth2 Client for OpenSky Network API
Handles token acquisition and refresh using client credentials flow
"""

import os
from typing import Optional
import httpx
from datetime import datetime, timedelta


class OpenSkyOAuth2Client:
    """Manages OAuth2 authentication for OpenSky Network API"""

    TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    TOKEN_EXPIRY_BUFFER = 300  # Refresh token 5 minutes before expiry

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize OAuth2 client

        Args:
            client_id: OAuth2 client ID from OpenSky account
            client_secret: OAuth2 client secret from OpenSky account
        """
        self.client_id = client_id or os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("OPENSKY_CLIENT_SECRET")
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def is_configured(self) -> bool:
        """Check if OAuth2 credentials are configured"""
        return bool(self.client_id and self.client_secret)

    def is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at

    async def get_access_token(self) -> Optional[str]:
        """
        Get a valid access token, requesting a new one if needed

        Returns:
            Access token string or None if OAuth2 is not configured
        """
        if not self.is_configured():
            return None

        if self.is_token_valid():
            return self.access_token

        # Request new token
        return await self._request_token()

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

                    return self.access_token
                else:
                    print(f"OAuth2 token request failed: {response.status_code} {response.text}")
                    return None

        except Exception as e:
            print(f"Error requesting OAuth2 token: {e}")
            return None

    def get_auth_headers(self) -> dict:
        """
        Get authorization headers for API requests

        Returns:
            Dictionary with Authorization header if token is available
        """
        if self.access_token and self.is_token_valid():
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}
