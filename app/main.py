from fastapi import FastAPI, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import httpx
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv
from app.oauth2_client import OpenSkyOAuth2Client

# Load environment variables
load_dotenv()

app = FastAPI(
    title="SkySentinel API",
    description="Sistema Inteligente de Vigilancia Aeroespacial - Refactored with OAuth2",
    version="2.0.0"
)

# ============================================================================
# DEFAULT BOUNDING BOX - GEORGIA STATE COVERAGE
# ============================================================================
# OpenSky charges by area square degrees:
#   0-25 sq deg = 1 credit
#   25-100 sq deg = 2 credits
#   100-400 sq deg = 3 credits
#   >400 or all = 4 credits
#
# Georgia state coverage (centered on Hartsfield-Jackson Atlanta International Airport):
#   Center: 33.6407°N, -84.4277°W (ATL Airport)
#   Coverage: Most of Georgia state (North GA mountains to Middle GA, Augusta to AL border)
#   Area: 24.9 sq deg (just under 25 sq deg threshold for maximum coverage at 1 credit)
#   Cost: 1 credit per request (vs 4 credits for global)
#   Savings: 75% reduction in API consumption vs global queries
DEFAULT_BBOX = {
    "lamin": 31.15,   # South - Middle Georgia (Macon area)
    "lamax": 36.14,   # North - North Georgia mountains
    "lomin": -86.92,  # West - Alabama border
    "lomax": -81.93   # East - Augusta area
}

# ============================================================================
# IN-MEMORY CACHE (45-second TTL)
# ============================================================================
# Perfect balance between Excellent (30s) and Very Good (60s) real-time feel
# Aircraft travel ~7-10 km in 45s - imperceptible lag at typical map zoom levels
# Saves 73% of API credits (640 requests/day vs 2400 uncached)
_api_cache = {
    "data": None,
    "rate_limit": None,
    "timestamp": None,
    "ttl_seconds": 45,  # 45 seconds - mathematical sweet spot for real-time + savings
    "endpoint": None,
    "params_hash": None
}

def _get_cache_key(endpoint: str, params: Optional[Dict[str, Any]]) -> str:
    """Generate a cache key from endpoint and params"""
    import json
    params_str = json.dumps(params or {}, sort_keys=True)
    return f"{endpoint}:{params_str}"

def _get_cached_response(endpoint: str, params: Optional[Dict[str, Any]]) -> Optional[tuple]:
    """Get cached response if available and not expired"""
    if _api_cache["data"] is None:
        return None

    cache_key = _get_cache_key(endpoint, params)
    if cache_key != _api_cache.get("cache_key"):
        return None

    cache_age = (datetime.now() - _api_cache["timestamp"]).total_seconds()
    if cache_age < _api_cache["ttl_seconds"]:
        print(f"✨ Cache HIT! Age: {cache_age:.1f}s (saved 1 API credit)")
        return _api_cache["data"], _api_cache["rate_limit"]

    print(f"⏱️  Cache EXPIRED (age: {cache_age:.1f}s)")
    return None

def _update_cache(endpoint: str, params: Optional[Dict[str, Any]], data: Dict, rate_limit: Dict):
    """Update cache with new data"""
    cache_key = _get_cache_key(endpoint, params)
    _api_cache["data"] = data
    _api_cache["rate_limit"] = rate_limit
    _api_cache["timestamp"] = datetime.now()
    _api_cache["cache_key"] = cache_key
    print(f"💾 Cache UPDATED (TTL: {_api_cache['ttl_seconds']}s)")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OAuth2 client
oauth2_client = OpenSkyOAuth2Client()

# Determine authentication mode
if oauth2_client.is_configured():
    print("🔐 OpenSky OAuth2 configured - using client credentials flow")
    auth_mode = "oauth2"
else:
    print("⚠️  OpenSky Anonymous mode - rate limits apply")
    auth_mode = "anonymous"


# ============================================================================
# UNIFIED API FETCH FUNCTION
# ============================================================================

async def fetch_opensky_api(
    endpoint: str = "/api/states/all",
    params: Optional[Dict[str, Any]] = None,
    use_auth: bool = True,
    use_cache: bool = True
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Unified function to fetch data from OpenSky API with automatic retry, rate limit tracking, and caching

    Args:
        endpoint: API endpoint path (default: /api/states/all)
        params: Query parameters dictionary
        use_auth: Whether to use OAuth2 authentication
        use_cache: Whether to use 10-second in-memory cache (default: True)

    Returns:
        Tuple of (response_data, rate_limit_info)

    Raises:
        httpx.HTTPStatusError: On HTTP errors
        Exception: On other errors
    """
    # Check cache first
    if use_cache:
        cached = _get_cached_response(endpoint, params)
        if cached is not None:
            return cached

    base_url = f"https://opensky-network.org{endpoint}"
    headers = {}

    # Add OAuth2 token if configured and requested
    if use_auth and oauth2_client.is_configured():
        token = await oauth2_client.get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

    async def _make_request():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params or {}, headers=headers)

            # Extract rate limit headers
            rate_limit_info = {
                "remaining": response.headers.get("X-Rate-Limit-Remaining"),
                "retry_after_seconds": None
            }

            # Handle 401 - will trigger retry in oauth2_client
            if response.status_code == 401:
                response.raise_for_status()

            # Handle 429 - Rate limit exceeded
            if response.status_code == 429:
                retry_after = response.headers.get("X-Rate-Limit-Retry-After-Seconds")
                rate_limit_info["retry_after_seconds"] = int(retry_after) if retry_after else None
                response.raise_for_status()

            # Handle other errors
            response.raise_for_status()

            data = response.json()
            return data, rate_limit_info

    # Use OAuth2 client's retry mechanism if authenticated
    if use_auth and oauth2_client.is_configured():
        result = await oauth2_client.execute_with_retry(_make_request)
    else:
        result = await _make_request()

    # Update cache with fresh data
    if use_cache:
        _update_cache(endpoint, params, result[0], result[1])

    return result


# ============================================================================
# DATA TRANSFORMATION FUNCTIONS
# ============================================================================

class State:
    """Represents an aircraft state vector"""
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
        self.category = None


def parse_states(data: Dict[str, Any]) -> List[State]:
    """Parse states data from OpenSky API response"""
    states_data = data.get("states", [])
    return [State(s) for s in states_data] if states_data else []


def to_geojson(state: State) -> Dict[str, Any]:
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


def create_geojson_response(states: List[State], timestamp: int, rate_limit_info: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a GeoJSON FeatureCollection response with rate limit info"""
    features = [
        to_geojson(s)
        for s in states
        if s.longitude is not None and s.latitude is not None
    ]

    response = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_aircraft": len(features),
            "timestamp": timestamp,
            "auth_mode": auth_mode,
            **(metadata or {})
        },
        "rate_limit": rate_limit_info
    }

    return response


# ============================================================================
# ERROR HANDLING
# ============================================================================

def handle_api_error(e: Exception) -> JSONResponse:
    """Handle API errors and return appropriate JSON response"""
    error_type = "SERVER_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = str(e)
    rate_limit_info = None

    if isinstance(e, httpx.HTTPStatusError):
        http_status = e.response.status_code

        if http_status == 429:
            error_type = "RATE_LIMIT"
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
            detail = "Rate limit exceeded. Please wait before making more requests."

            # Try to extract rate limit info
            retry_after = e.response.headers.get("X-Rate-Limit-Retry-After-Seconds")
            remaining = e.response.headers.get("X-Rate-Limit-Remaining")
            if retry_after or remaining:
                rate_limit_info = {
                    "remaining": remaining,
                    "retry_after_seconds": int(retry_after) if retry_after else None
                }
        elif http_status == 401:
            error_type = "AUTHENTICATION_ERROR"
            status_code = status.HTTP_401_UNAUTHORIZED
            detail = "Authentication failed. Please check your credentials."
        elif http_status >= 500:
            error_type = "EXTERNAL_SERVER_ERROR"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = "OpenSky API is currently unavailable. Please try again later."
        else:
            error_type = "CONNECTION_ERROR"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = f"Failed to communicate with OpenSky API (HTTP {http_status})"

    response_content = {
        "error": error_type,
        "detail": detail,
        "message": detail
    }

    if rate_limit_info:
        response_content["rate_limit"] = rate_limit_info

    return JSONResponse(
        status_code=status_code,
        content=response_content
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================
# Note: Root endpoint (GET /) removed - use GET /api/v1/status for health checks

@app.get("/api/v1/airspace")
async def get_airspace(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get current airspace data as GeoJSON FeatureCollection for Georgia state

    Defaults to Georgia state bounding box centered on Atlanta Airport (24.9 sq deg = 1 credit vs 4 credits for global)
    Coverage: North Georgia mountains to Middle Georgia, Augusta area to Alabama border

    Args:
        limit: Maximum number of aircraft to return (1-500)

    Returns:
        GeoJSON FeatureCollection with aircraft positions and rate limit info
    """
    try:
        # Use Georgia state bounding box by default (24.9 sq deg = 1 credit vs 4 credits for global)
        data, rate_limit_info = await fetch_opensky_api(params=DEFAULT_BBOX)

        states = parse_states(data)[:limit]
        timestamp = data.get("time", 0)

        # Add bounding box to metadata for transparency
        metadata = {
            "bounding_box": DEFAULT_BBOX,
            "area_coverage": "Georgia State (North GA mountains, Middle GA, Augusta area, centered on ATL Airport)",
            "area_square_degrees": 24.9
        }

        return create_geojson_response(states, timestamp, rate_limit_info, metadata)

    except Exception as e:
        return handle_api_error(e)


@app.get("/api/v1/airspace/region")
async def get_airspace_region(
    min_lat: float = Query(..., ge=-90, le=90),
    max_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lon: float = Query(..., ge=-180, le=180)
):
    """
    Get airspace data for a specific bounding box region

    Args:
        min_lat: Minimum latitude (-90 to 90)
        max_lat: Maximum latitude (-90 to 90)
        min_lon: Minimum longitude (-180 to 180)
        max_lon: Maximum longitude (-180 to 180)

    Returns:
        GeoJSON FeatureCollection with aircraft positions in the region and rate limit info
    """
    try:
        params = {
            "lamin": min_lat,
            "lomin": min_lon,
            "lamax": max_lat,
            "lomax": max_lon
        }

        data, rate_limit_info = await fetch_opensky_api(params=params)

        states = parse_states(data)
        timestamp = data.get("time", 0)

        metadata = {
            "bounding_box": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon
            }
        }

        return create_geojson_response(states, timestamp, rate_limit_info, metadata)

    except Exception as e:
        return handle_api_error(e)


@app.get("/api/v1/states/authenticated")
async def get_states_authenticated():
    """
    Retrieve all states as an authenticated OpenSky user
    Requires OAuth2 authentication

    Returns:
        GeoJSON FeatureCollection with all aircraft states and rate limit info
    """
    try:
        if not oauth2_client.is_configured():
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "AUTHENTICATION_REQUIRED",
                    "detail": "OAuth2 credentials not configured. This endpoint requires authentication."
                }
            )

        data, rate_limit_info = await fetch_opensky_api(use_auth=True)

        states = parse_states(data)
        timestamp = data.get("time", 0)

        return create_geojson_response(states, timestamp, rate_limit_info)

    except Exception as e:
        return handle_api_error(e)


@app.get("/api/v1/states/aircraft")
async def get_states_aircraft(
    icao24: List[str] = Query(..., description="ICAO24 address(es) of aircraft (e.g., 3c6444, 3e1bf9)")
):
    """
    Retrieve states of specific aircraft by ICAO24 address

    Args:
        icao24: One or more ICAO24 addresses (e.g., ?icao24=3c6444&icao24=3e1bf9)

    Returns:
        GeoJSON FeatureCollection with requested aircraft states and rate limit info
    """
    try:
        # Build params with multiple icao24 values
        params = {"icao24": icao24}

        data, rate_limit_info = await fetch_opensky_api(params=params)

        states = parse_states(data)
        timestamp = data.get("time", 0)

        metadata = {
            "requested_aircraft": icao24,
            "found_aircraft": len(states)
        }

        return create_geojson_response(states, timestamp, rate_limit_info, metadata)

    except Exception as e:
        return handle_api_error(e)


@app.get("/api/v1/tracks/{icao24}")
async def get_aircraft_track(
    icao24: str,
    time: Optional[int] = Query(default=None, description="Unix timestamp (seconds). If omitted, uses current time.")
):
    """
    Retrieve trajectory/track data for a specific aircraft by ICAO24 address

    Returns waypoints, first/last positions, and all on-ground state changes.
    Tracks show the complete flight path of an aircraft.

    Args:
        icao24: ICAO24 address of aircraft (e.g., 3c6444)
        time: Unix timestamp in seconds (optional, defaults to current time if not provided)

    Returns:
        Track data including waypoints, path, and ground state changes with rate limit info

    Note:
        - OpenSky API endpoint: https://openskynetwork.github.io/opensky-api/rest.html#track-by-aircraft
        - ⚠️ REQUIRES SPECIAL PERMISSIONS: This endpoint may require OpenSky researcher/contributor access
        - Standard OAuth2 authentication may return 403 Forbidden
        - Consider using /api/v1/states/aircraft for real-time position tracking instead
    """
    try:
        # Use current time if not provided
        import time as time_module
        if time is None:
            time = int(time_module.time())

        # Build endpoint and params
        endpoint = f"/tracks/all"
        params = {
            "icao24": icao24.lower(),
            "time": time
        }

        # Fetch track data (do not use cache for historical data)
        data, rate_limit_info = await fetch_opensky_api(
            endpoint=endpoint,
            params=params,
            use_cache=False  # Historical data shouldn't be cached
        )

        # Transform track data to GeoJSON LineString
        if not data or "path" not in data:
            return {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": []
                },
                "properties": {
                    "icao24": icao24,
                    "callsign": data.get("callsign", "N/A") if data else "N/A",
                    "start_time": data.get("startTime", time) if data else time,
                    "end_time": data.get("endTime", time) if data else time,
                    "waypoint_count": 0
                },
                "metadata": {
                    "message": "No track data found for this aircraft at the specified time"
                },
                "rate_limit": rate_limit_info
            }

        # Extract waypoints from path data
        # Each waypoint: [time, latitude, longitude, baro_altitude, true_track, on_ground]
        path = data.get("path", [])
        coordinates = []
        waypoints = []
        ground_segments = []

        for i, point in enumerate(path):
            if len(point) >= 3 and point[1] is not None and point[2] is not None:
                # GeoJSON format: [longitude, latitude, altitude]
                lon, lat = point[2], point[1]
                alt = point[3] if len(point) > 3 and point[3] is not None else 0
                coordinates.append([lon, lat, alt])

                waypoint = {
                    "time": point[0],
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": alt,
                    "heading": point[4] if len(point) > 4 else None,
                    "on_ground": point[5] if len(point) > 5 else False
                }
                waypoints.append(waypoint)

                # Track ground state changes
                if len(point) > 5 and point[5]:
                    ground_segments.append({
                        "index": i,
                        "time": point[0],
                        "position": [lat, lon]
                    })

        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {
                "icao24": data.get("icao24", icao24),
                "callsign": data.get("callsign", "N/A"),
                "start_time": data.get("startTime", time),
                "end_time": data.get("endTime", time),
                "waypoint_count": len(waypoints),
                "ground_segments": len(ground_segments)
            },
            "waypoints": waypoints,
            "ground_state_changes": ground_segments,
            "metadata": {
                "first_position": waypoints[0] if waypoints else None,
                "last_position": waypoints[-1] if waypoints else None,
                "duration_seconds": data.get("endTime", time) - data.get("startTime", time) if data else 0
            },
            "rate_limit": rate_limit_info
        }

    except Exception as e:
        return handle_api_error(e)


@app.get("/api/v1/flights/all")
async def get_all_flights(
    begin: int = Query(..., description="Start of time interval (Unix timestamp in seconds)"),
    end: int = Query(..., description="End of time interval (Unix timestamp in seconds)")
):
    """
    Retrieve all flights for a specific time interval

    Returns departure and arrival airports, times, and aircraft information for all flights
    within the specified time window. Use these results to get detailed track information.

    Args:
        begin: Start time as Unix timestamp in seconds
        end: End time as Unix timestamp in seconds

    Returns:
        List of flights with departure/arrival info and rate limit info

    Note:
        - OpenSky API endpoint: https://openskynetwork.github.io/opensky-api/rest.html#flights-all
        - Time interval must not exceed 2 hours (7200 seconds)
        - ⚠️ REQUIRES SPECIAL PERMISSIONS: This endpoint may require OpenSky researcher/contributor access
        - Standard OAuth2 authentication may return 403 Forbidden
        - Consider using /api/v1/airspace for real-time aircraft monitoring instead
    """
    try:
        # Validate time interval (max 2 hours per OpenSky API)
        if end - begin > 7200:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "INVALID_TIME_INTERVAL",
                    "detail": "Time interval exceeds maximum of 2 hours (7200 seconds)",
                    "begin": begin,
                    "end": end,
                    "interval_seconds": end - begin
                }
            )

        # Build endpoint and params
        endpoint = "/flights/all"
        params = {
            "begin": begin,
            "end": end
        }

        # Fetch flights data (do not use cache for historical data)
        data, rate_limit_info = await fetch_opensky_api(
            endpoint=endpoint,
            params=params,
            use_cache=False  # Historical data shouldn't be cached
        )

        # Transform flights data
        flights = []
        if data and isinstance(data, list):
            for flight in data:
                flights.append({
                    "icao24": flight.get("icao24"),
                    "callsign": flight.get("callsign", "").strip() if flight.get("callsign") else "N/A",
                    "departure_airport": flight.get("estDepartureAirport") or "Unknown",
                    "arrival_airport": flight.get("estArrivalAirport") or "Unknown",
                    "departure_time": flight.get("firstSeen"),
                    "arrival_time": flight.get("lastSeen"),
                    "departure_horizontal_distance": flight.get("estDepartureAirportHorizDistance"),
                    "departure_vertical_distance": flight.get("estDepartureAirportVertDistance"),
                    "arrival_horizontal_distance": flight.get("estArrivalAirportHorizDistance"),
                    "arrival_vertical_distance": flight.get("estArrivalAirportVertDistance")
                })

        return {
            "flights": flights,
            "metadata": {
                "begin": begin,
                "end": end,
                "interval_seconds": end - begin,
                "total_flights": len(flights)
            },
            "rate_limit": rate_limit_info
        }

    except Exception as e:
        return handle_api_error(e)


@app.get("/api/v1/status")
async def get_status():
    """
    Get backend and OpenSky API status with rate limit information

    NOTE: This endpoint does NOT make an actual OpenSky API call to avoid wasting credits.
    It only checks if OAuth2 is configured and returns cached rate limit info.

    Returns:
        Status information including backend health, authentication mode, and rate limits
    """
    backend_status = "OPERATIONAL"
    opensky_status = "UNKNOWN"

    # Check OAuth2 configuration without making an API call
    if oauth2_client.is_configured():
        if oauth2_client.is_token_valid():
            opensky_status = "OPERATIONAL"
        else:
            opensky_status = "TOKEN_EXPIRED"
    else:
        opensky_status = "NOT_CONFIGURED"

    response = {
        "backend": {
            "status": backend_status,
            "service": "SkySentinel API",
            "version": "2.0.0"
        },
        "opensky": {
            "status": opensky_status,
            "auth_mode": auth_mode,
            "rate_limit": None  # Rate limit info comes from actual data endpoints
        }
    }

    return response


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
