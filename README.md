# SkySentinel Backend

Intelligent Aerospace Surveillance System - Backend API

## Description

SkySentinel is a geospatial middleware that connects real-time aircraft data from OpenSky Network API with Artificial Intelligence agents. The backend is built with FastAPI and serves data in GeoJSON format optimized for map visualization and AI analysis.

## Features

- **OpenSky Network Integration**: Real-time aircraft data
- **GeoJSON Output**: Optimized format for maps and AI
- **FastAPI Backend**: Fast and modern REST API
- **CORS Enabled**: Ready for frontend integration
- **Regional Filtering**: Bounding box query support
- **Docker Ready**: Easy cloud deployment

## Architecture

```
OpenSky Network API → SkySentinel Backend (FastAPI) → Frontend (Vue.js/Leaflet)
                                                     ↓
                                                 Gemini AI
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

3. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your OpenSky credentials (optional)
```

4. Run server:
```bash
python app/main.py
# Or use uvicorn directly:
uvicorn app.main:app --reload
```

The server will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /
```

### Get Airspace Data
```
GET /api/v1/airspace?limit=50
```

Returns aircraft data in GeoJSON FeatureCollection format.

**Parameters:**
- `limit` (optional): Maximum number of aircraft to return (default: 50)

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
        "last_contact": 1234567890
      }
    }
  ],
  "metadata": {
    "total_aircraft": 50,
    "timestamp": 1234567890
  }
}
```

### Get Regional Airspace Data
```
GET /api/v1/airspace/region?min_lat=37&max_lat=38&min_lon=-123&max_lon=-122
```

Returns aircraft data within a specific region (bounding box).

**Parameters:**
- `min_lat`: Minimum latitude
- `max_lat`: Maximum latitude
- `min_lon`: Minimum longitude
- `max_lon`: Maximum longitude

## Docker

### Build
```bash
docker build -t skysentinel-backend .
```

### Run
```bash
docker run -p 8000:8000 skysentinel-backend
```

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
  --allow-unauthenticated
```

### AWS App Runner

1. Connect with GitHub
2. Configure auto-deploy from repository
3. Specify port 8000

## Frontend Integration

The backend is designed to integrate with the existing Vue.js project:

```javascript
// In your Vue component
async function fetchAirspaceData() {
  const response = await fetch('http://localhost:8000/api/v1/airspace?limit=50');
  const geojson = await response.json();

  // Use with Leaflet
  L.geoJSON(geojson).addTo(map);
}
```

## Upcoming Features

- [ ] Geofencing: Airspace exclusion zones
- [ ] WebSocket support for real-time updates
- [ ] Advanced filters (altitude, velocity, aircraft type)
- [ ] Data caching to reduce OpenSky API calls
- [ ] Authentication and rate limiting

## Technologies

- **FastAPI**: Modern and fast web framework
- **OpenSky Network API**: Aircraft data source
- **Uvicorn**: High-performance ASGI server
- **Pydantic**: Data validation
- **Python 3.11+**: Programming language

## License

MIT

## Author

SkySentinel Project - Intelligent Aerospace Surveillance System
