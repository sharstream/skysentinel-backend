# SkySentinel Backend v2.0

Intelligent Aerospace Surveillance System - Backend API with OAuth2 & Rate Limiting

## Description

SkySentinel is a geospatial middleware that connects real-time aircraft data from OpenSky Network API with Artificial Intelligence agents. The backend is built with FastAPI and serves data in GeoJSON format optimized for map visualization and AI analysis.

## Features

- **OAuth2 Authentication**: Automatic token management with 10x rate limit upgrade (4000 req vs 400 anon)
- **Resilient Error Handling**: Automatic token refresh on expiration
- **Rate Limit Tracking**: Real-time credit monitoring and countdown timers
- **OpenSky Network Integration**: Real-time aircraft data
- **GeoJSON Output**: Optimized format for maps and AI
- **FastAPI Backend**: Fast and modern REST API
- **CORS Enabled**: Ready for frontend integration
- **Regional Filtering**: Bounding box query support
- **Aircraft Tracking**: Query specific aircraft by ICAO24
- **Docker Ready**: Easy cloud deployment

## Architecture

```
OpenSky Network API → SkySentinel Backend (FastAPI) → Frontend (Vue.js/Leaflet)
       ↓                        ↓                              ↓
   OAuth2 Auth          Rate Limit Tracking              Gemini AI
```

## Installation

### Requirements

- Python 3.11+
- pip

### Local Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your OpenSky OAuth2 credentials:
```env
# OAuth2 Client Credentials (recommended - 10x higher rate limits)
OPENSKY_CLIENT_ID=your_client_id_here
OPENSKY_CLIENT_SECRET=your_client_secret_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

Get OAuth2 credentials from: https://opensky-network.org/my-opensky

4. Run server:
```bash
python app/main.py
# Or use uvicorn directly:
uvicorn app.main:app --reload
```

The server will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```http
GET /
```

**Response:**
```json
{
  "service": "SkySentinel API",
  "status": "operational",
  "version": "2.0.0",
  "auth_mode": "oauth2"
}
```

---

### Get Airspace Data
```http
GET /api/v1/airspace?limit=50
```

Returns aircraft data in GeoJSON FeatureCollection format with rate limit information.

**Parameters:**
- `limit` (optional): Maximum number of aircraft to return (1-500, default: 50)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "properties": {
        "icao24": "a12345",
        "callsign": "UAL123",
        "altitude": 10000,
        "velocity": 250,
        "heading": 180,
        "origin_country": "United States",
        "on_ground": false,
        "last_contact": 1234567890,
        "vertical_rate": 5.2
      }
    }
  ],
  "metadata": {
    "total_aircraft": 50,
    "timestamp": 1234567890,
    "auth_mode": "oauth2"
  },
  "rate_limit": {
    "remaining": "3999",
    "retry_after_seconds": null
  }
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/airspace?limit=10" | python -m json.tool
```

---

### Get Regional Airspace Data
```http
GET /api/v1/airspace/region?min_lat=37&max_lat=38&min_lon=-123&max_lon=-122
```

Returns aircraft data within a specific bounding box region.

**Parameters:**
- `min_lat`: Minimum latitude (-90 to 90)
- `max_lat`: Maximum latitude (-90 to 90)
- `min_lon`: Minimum longitude (-180 to 180)
- `max_lon`: Maximum longitude (-180 to 180)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [...],
  "metadata": {
    "total_aircraft": 15,
    "timestamp": 1234567890,
    "auth_mode": "oauth2",
    "bounding_box": {
      "min_lat": 37.0,
      "max_lat": 38.0,
      "min_lon": -123.0,
      "max_lon": -122.0
    }
  },
  "rate_limit": {
    "remaining": "3998",
    "retry_after_seconds": null
  }
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/airspace/region?min_lat=40&max_lat=41&min_lon=-74&max_lon=-73" | python -m json.tool
```

---

### Get Authenticated States
```http
GET /api/v1/states/authenticated
```

Retrieve all states as an authenticated OpenSky user. Requires OAuth2 configuration.

**Response:**
Same as `/api/v1/airspace` but uses authentication to access the full dataset.

**Example:**
```bash
curl "http://localhost:8000/api/v1/states/authenticated" | python -m json.tool
```

**Note:** This endpoint requires `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET` to be configured.

---

### Get Aircraft States
```http
GET /api/v1/states/aircraft?icao24=3c6444&icao24=3e1bf9
```

Retrieve states of specific aircraft by ICAO24 address.

**Parameters:**
- `icao24`: One or more ICAO24 addresses (can be repeated)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [...],
  "metadata": {
    "total_aircraft": 2,
    "timestamp": 1234567890,
    "auth_mode": "oauth2",
    "requested_aircraft": ["3c6444", "3e1bf9"],
    "found_aircraft": 2
  },
  "rate_limit": {
    "remaining": "3997",
    "retry_after_seconds": null
  }
}
```

**Example:**
```bash
# Single aircraft
curl "http://localhost:8000/api/v1/states/aircraft?icao24=3c6444" | python -m json.tool

# Multiple aircraft
curl "http://localhost:8000/api/v1/states/aircraft?icao24=3c6444&icao24=3e1bf9" | python -m json.tool
```

---

### Get API Status
```http
GET /api/v1/status
```

Get backend and OpenSky API status with rate limit information.

**Response:**
```json
{
  "backend": {
    "status": "OPERATIONAL",
    "service": "SkySentinel API",
    "version": "2.0.0"
  },
  "opensky": {
    "status": "OPERATIONAL",
    "auth_mode": "oauth2",
    "rate_limit": {
      "remaining": "3996",
      "retry_after_seconds": null
    }
  }
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/status" | python -m json.tool
```

---

## Rate Limiting

### API Credits

| Authentication Mode | Rate Limit | Requests/Day |
|---------------------|------------|--------------|
| Anonymous | 400 credits | ~400 requests |
| **OAuth2** | **4000 credits** | **~4000 requests** |

### Rate Limit Headers

All endpoints return rate limit information:

```json
{
  "rate_limit": {
    "remaining": "3999",
    "retry_after_seconds": null
  }
}
```

- `remaining`: Number of API credits remaining
- `retry_after_seconds`: Seconds until rate limit resets (only present when rate limited)

### Error Response (429 - Rate Limited)

```json
{
  "error": "RATE_LIMIT",
  "detail": "Rate limit exceeded. Please wait before making more requests.",
  "message": "Rate limit exceeded. Please wait before making more requests.",
  "rate_limit": {
    "remaining": "0",
    "retry_after_seconds": 60
  }
}
```

---

## OAuth2 Configuration

### Getting Credentials

1. Visit https://opensky-network.org/my-opensky
2. Create a new OAuth2 client
3. Copy your `Client ID` and `Client Secret`
4. Add them to your `.env` file

### Benefits

- **10x Rate Limit**: 4000 requests vs 400 anonymous
- **Automatic Token Refresh**: Tokens refresh every 25 minutes automatically
- **Resilient Error Handling**: Automatic retry on token expiration
- **No Manual Management**: Fully automated authentication flow

### How It Works

The backend automatically:
1. Requests an OAuth2 token using client credentials
2. Attaches the token to all API requests
3. Monitors token expiration (30 min lifetime)
4. Refreshes tokens 5 minutes before expiry
5. Retries failed requests with fresh tokens

---

## Future Endpoints

### Flights in Time Interval
```http
GET /api/v1/flights/all?begin=1517227200&end=1517230800
```

Get flights within a specific time interval.

**Parameters:**
- `begin`: Unix timestamp (start of interval)
- `end`: Unix timestamp (end of interval)

**Example:**
```bash
curl "http://localhost:8000/api/v1/flights/all?begin=1517227200&end=1517230800" | python -m json.tool
```

---

### Aircraft Flight History
```http
GET /api/v1/flights/aircraft?icao24=3c675a&begin=1517184000&end=1517270400
```

Get flight history for a specific aircraft.

**Parameters:**
- `icao24`: ICAO24 address of aircraft
- `begin`: Unix timestamp (start of interval)
- `end`: Unix timestamp (end of interval)

**Example:**
```bash
curl "http://localhost:8000/api/v1/flights/aircraft?icao24=3c675a&begin=1517184000&end=1517270400" | python -m json.tool
```

---

## Caching Strategy (Future Enhancement)

### Design Considerations

For optimal performance with AI agents and real-time plotting:

**10-Second Cache Layer:**
- Cache OpenSky API responses for 10 seconds
- Reduces API calls while maintaining accuracy
- Sufficient precision for coordinate plotting
- Prevents rate limit exhaustion during AI interactions

**Implementation Goals:**
- Redis/In-Memory cache for state data
- Automatic cache invalidation after 10s
- Cache hit/miss metrics
- Configurable cache duration

**Benefits:**
- Supports high-frequency AI agent queries
- Maintains coordinate/waypoint accuracy
- Prevents unnecessary API consumption
- Enables real-time maneuver tracking

---

## Docker

### Build
```bash
docker build -t skysentinel-backend .
```

### Run
```bash
docker run -p 8000:8000 -e OPENSKY_CLIENT_ID=your_id -e OPENSKY_CLIENT_SECRET=your_secret skysentinel-backend
```

---

## Cloud Deployment

### Google Cloud Run (Recommended)

1. Build and push to Container Registry:
```bash
gcloud builds submit --tag gcr.io/[PROJECT-ID]/skysentinel-backend
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy skysentinel-backend \
  --image gcr.io/[PROJECT-ID]/skysentinel-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENSKY_CLIENT_ID=your_id,OPENSKY_CLIENT_SECRET=your_secret
```

### AWS App Runner

1. Connect with GitHub
2. Configure auto-deploy from repository
3. Specify port 8000
4. Add environment variables for OAuth2

---

## Frontend Integration

The backend is designed to integrate with Vue.js/React frontends:

```javascript
// Fetch airspace data with rate limit info
async function fetchAirspaceData() {
  const response = await fetch('http://localhost:8000/api/v1/airspace?limit=50');
  const data = await response.json();

  // Access rate limit info
  console.log(`Remaining credits: ${data.rate_limit.remaining}`);

  // Use with Leaflet
  L.geoJSON(data).addTo(map);
}
```

---

## Technologies

- **FastAPI**: Modern and fast web framework
- **OpenSky Network API**: Aircraft data source with OAuth2
- **Uvicorn**: High-performance ASGI server
- **HTTPX**: Async HTTP client with retry support
- **Pydantic**: Data validation
- **Python 3.11+**: Programming language

---

## API Credit Usage (Per OpenSky Documentation)

| Operation | Credits (Anonymous) | Credits (OAuth2) |
|-----------|---------------------|------------------|
| Any call | 1 credit | 1 credit |
| Own sensors | 0 credits | 0 credits |

**Credit Reset:** Credits reset periodically (typically daily)

---

## Error Handling

The API returns standardized error responses:

```json
{
  "error": "ERROR_TYPE",
  "detail": "Human-readable error message",
  "message": "Human-readable error message"
}
```

**Error Types:**
- `RATE_LIMIT`: API rate limit exceeded
- `AUTHENTICATION_ERROR`: OAuth2 authentication failed
- `CONNECTION_ERROR`: Cannot connect to OpenSky API
- `SERVER_ERROR`: Internal server error
- `EXTERNAL_SERVER_ERROR`: OpenSky API unavailable

---

## License

MIT

---

## Author

SkySentinel Project - Intelligent Aerospace Surveillance System v2.0
