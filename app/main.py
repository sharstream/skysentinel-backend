from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from python_opensky import OpenSky, BoundingBox, OpenSkyConnectionError, OpenSkyError
from aiohttp import ClientResponseError
from typing import Optional
import uvicorn
import os
from dotenv import load_dotenv
from app.oauth2_client import OpenSkyOAuth2Client

# Load environment variables
load_dotenv()

app = FastAPI(
    title="SkySentinel API",
    description="Sistema Inteligente de Vigilancia Aeroespacial",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OAuth2 client
oauth2_client = OpenSkyOAuth2Client()

# Initialize OpenSky API
# Priority: OAuth2 > Basic Auth > Anonymous
opensky_username = os.getenv("OPENSKY_USERNAME")
opensky_password = os.getenv("OPENSKY_PASSWORD")

# Note: python-opensky library doesn't natively support OAuth2 bearer tokens
# If OAuth2 is configured, we'll need to fetch token and use it differently
if oauth2_client.is_configured():
    print("🔐 OpenSky OAuth2 configured - using client credentials flow")
    opensky = OpenSky()  # Initialize without auth, we'll add bearer token per request
    auth_mode = "oauth2"
elif opensky_username and opensky_password:
    print("🔑 OpenSky Basic Auth configured")
    opensky = OpenSky(username=opensky_username, password=opensky_password)
    auth_mode = "basic"
else:
    print("⚠️  OpenSky Anonymous mode - rate limits apply")
    opensky = OpenSky()
    auth_mode = "anonymous"


async def fetch_opensky_states_oauth2(bbox: Optional[BoundingBox] = None):
    """
    Fetch states from OpenSky API using OAuth2 bearer token

    Args:
        bbox: Optional bounding box for regional queries

    Returns:
        States object with time and states list
    """
    import httpx

    # Get OAuth2 token
    token = await oauth2_client.get_access_token()
    if not token:
        raise OpenSkyConnectionError("Failed to obtain OAuth2 access token")

    # Build request URL
    base_url = "https://opensky-network.org/api/states/all"
    params = {}
    if bbox:
        params = {
            "lamin": bbox.min_latitude,
            "lomin": bbox.min_longitude,
            "lamax": bbox.max_latitude,
            "lomax": bbox.max_longitude
        }

    # Make authenticated request
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(base_url, params=params, headers=headers)

        if response.status_code == 401:
            raise OpenSkyConnectionError("OAuth2 token expired or invalid")
        elif response.status_code == 429:
            raise OpenSkyConnectionError("Rate limit exceeded")
        elif response.status_code != 200:
            raise OpenSkyConnectionError(f"OpenSky API returned status {response.status_code}")

        data = response.json()

        # Parse response into states object (mimicking python-opensky structure)
        class State:
            def __init__(self, state_data):
                self.icao24 = state_data[0]
                self.callsign = state_data[1]
                self.origin_country = state_data[2]
                self.time_position = state_data[3]
                self.last_contact = state_data[4]
                self.longitude = state_data[5]
                self.latitude = state_data[6]
                self.barometric_altitude = state_data[7]
                self.on_ground = state_data[8]
                self.velocity = state_data[9]
                self.true_track = state_data[10]
                self.vertical_rate = state_data[11]
                self.geo_altitude = state_data[13] if len(state_data) > 13 else None
                self.category = None  # Not provided in basic API response

        class States:
            def __init__(self, time, states_data):
                self.time = time
                self.states = [State(s) for s in states_data] if states_data else []

        return States(data.get("time"), data.get("states"))


def to_geojson(state):
    """Convert OpenSky state vector to GeoJSON feature"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [state.longitude, state.latitude]
        },
        "properties": {
            "icao24": state.icao24,
            "callsign": state.callsign.strip() if state.callsign else "N/A",
            "altitude": state.barometric_altitude,
            "geo_altitude": state.geo_altitude,
            "velocity": state.velocity,
            "heading": state.true_track,
            "origin_country": state.origin_country,
            "on_ground": state.on_ground,
            "last_contact": state.last_contact,
            "time_position": state.time_position,
            "vertical_rate": state.vertical_rate,
            "category": state.category.value if hasattr(state.category, 'value') and state.category else None
        }
    }


def handle_opensky_error(e: Exception) -> JSONResponse:
    """
    Handle OpenSky API errors and return appropriate HTTP status codes and error types.

    Error types:
    - RATE_LIMIT: API rate limit exceeded (429)
    - TIMEOUT: Request timeout (504)
    - CONNECTION_ERROR: Network/connection issues (503)
    - SERVER_ERROR: Internal server error (500)
    """
    error_type = "SERVER_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = str(e)

    # Check if it's an OpenSkyConnectionError with an underlying HTTP error
    if isinstance(e, OpenSkyConnectionError):
        # Check the underlying cause for HTTP status codes
        if e.__cause__ and isinstance(e.__cause__, ClientResponseError):
            http_status = e.__cause__.status

            if http_status == 429:
                error_type = "RATE_LIMIT"
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
                detail = "OpenSky API rate limit exceeded. Please wait before making more requests or configure authentication credentials."
            elif http_status >= 500:
                error_type = "EXTERNAL_SERVER_ERROR"
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                detail = "OpenSky API is currently unavailable. Please try again later."
            elif http_status == 401:
                error_type = "AUTHENTICATION_ERROR"
                status_code = status.HTTP_401_UNAUTHORIZED
                detail = "Invalid OpenSky API credentials."
            else:
                error_type = "CONNECTION_ERROR"
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                detail = f"Failed to communicate with OpenSky API (HTTP {http_status})"

        # Check for timeout errors
        elif "timeout" in str(e).lower():
            error_type = "TIMEOUT"
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            detail = "Request to OpenSky API timed out. Please try again."
        else:
            error_type = "CONNECTION_ERROR"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = "Failed to connect to OpenSky API. Please check your internet connection."

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "detail": detail,
            "message": detail  # Legacy field for backwards compatibility
        }
    )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "SkySentinel API",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/api/v1/airspace")
async def get_airspace(limit: int = 50):
    """
    Get current airspace data as GeoJSON FeatureCollection

    Args:
        limit: Maximum number of aircraft to return (default: 50)

    Returns:
        GeoJSON FeatureCollection with aircraft positions
    """
    try:
        # Use OAuth2 if configured, otherwise use python-opensky library
        if auth_mode == "oauth2":
            states = await fetch_opensky_states_oauth2()
        else:
            states = await opensky.get_states()

        if not states or not states.states:
            return {"type": "FeatureCollection", "features": []}

        # Filter aircraft with valid position
        features = [
            to_geojson(s)
            for s in states.states[:limit]
            if s.longitude is not None and s.latitude is not None
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_aircraft": len(features),
                "timestamp": states.time,
                "auth_mode": auth_mode
            }
        }
    except (OpenSkyConnectionError, OpenSkyError) as e:
        return handle_opensky_error(e)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "SERVER_ERROR",
                "detail": f"An unexpected error occurred: {str(e)}",
                "message": f"An unexpected error occurred: {str(e)}"
            }
        )


@app.get("/api/v1/airspace/region")
async def get_airspace_region(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float
):
    """
    Get airspace data for a specific bounding box region

    Args:
        min_lat: Minimum latitude
        max_lat: Maximum latitude
        min_lon: Minimum longitude
        max_lon: Maximum longitude

    Returns:
        GeoJSON FeatureCollection with aircraft positions in the region
    """
    try:
        bbox = BoundingBox(
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon
        )

        # Use OAuth2 if configured, otherwise use python-opensky library
        if auth_mode == "oauth2":
            states = await fetch_opensky_states_oauth2(bbox)
        else:
            states = await opensky.get_states(bounding_box=bbox)

        if not states or not states.states:
            return {"type": "FeatureCollection", "features": []}

        features = [
            to_geojson(s)
            for s in states.states
            if s.longitude is not None and s.latitude is not None
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_aircraft": len(features),
                "bounding_box": {
                    "min_lat": min_lat,
                    "max_lat": max_lat,
                    "min_lon": min_lon,
                    "max_lon": max_lon
                },
                "timestamp": states.time,
                "auth_mode": auth_mode
            }
        }
    except (OpenSkyConnectionError, OpenSkyError) as e:
        return handle_opensky_error(e)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "SERVER_ERROR",
                "detail": f"An unexpected error occurred: {str(e)}",
                "message": f"An unexpected error occurred: {str(e)}"
            }
        )


@app.get("/api/v1/status")
async def get_status():
    """
    Get backend and OpenSky API status

    Returns:
        Status information including backend health and OpenSky API connectivity
    """
    backend_status = "OPERATIONAL"
    opensky_status = "UNKNOWN"
    error_type = None
    error_detail = None

    try:
        # Try a minimal request to check OpenSky API connectivity
        # Use a small bounding box to minimize credit usage
        test_bbox = BoundingBox(
            min_latitude=0.0,
            max_latitude=0.1,
            min_longitude=0.0,
            max_longitude=0.1
        )
        states = await opensky.get_states(bounding_box=test_bbox)
        opensky_status = "OPERATIONAL"
    except (OpenSkyConnectionError, OpenSkyError) as e:
        # Determine the specific error type
        if isinstance(e, OpenSkyConnectionError) and e.__cause__:
            if isinstance(e.__cause__, ClientResponseError):
                http_status = e.__cause__.status
                if http_status == 429:
                    opensky_status = "RATE_LIMIT"
                    error_type = "RATE_LIMIT"
                    error_detail = "OpenSky API rate limit exceeded"
                elif http_status >= 500:
                    opensky_status = "EXTERNAL_ERROR"
                    error_type = "EXTERNAL_SERVER_ERROR"
                    error_detail = "OpenSky API server error"
                elif http_status == 401:
                    opensky_status = "AUTH_ERROR"
                    error_type = "AUTHENTICATION_ERROR"
                    error_detail = "Invalid credentials"
                else:
                    opensky_status = "CONNECTION_ERROR"
                    error_type = "CONNECTION_ERROR"
                    error_detail = f"HTTP {http_status}"
            elif "timeout" in str(e).lower():
                opensky_status = "TIMEOUT"
                error_type = "TIMEOUT"
                error_detail = "Request timeout"
            else:
                opensky_status = "CONNECTION_ERROR"
                error_type = "CONNECTION_ERROR"
                error_detail = "Connection failed"
        else:
            opensky_status = "ERROR"
            error_type = "SERVER_ERROR"
            error_detail = str(e)
    except Exception as e:
        opensky_status = "ERROR"
        error_type = "SERVER_ERROR"
        error_detail = str(e)

    response = {
        "backend": {
            "status": backend_status,
            "service": "SkySentinel API",
            "version": "1.0.0"
        },
        "opensky": {
            "status": opensky_status,
            "authenticated": opensky.is_authenticated if hasattr(opensky, 'is_authenticated') else False
        }
    }

    if error_type:
        response["opensky"]["error"] = error_type
        response["opensky"]["error_detail"] = error_detail

    return response


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
