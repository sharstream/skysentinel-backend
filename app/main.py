import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from python_opensky import OpenSky, BoundingBox
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv

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

# Initialize OpenSky API
# For authenticated requests, provide username and password
opensky_username = os.getenv("OPENSKY_USERNAME")
opensky_password = os.getenv("OPENSKY_PASSWORD")

if opensky_username and opensky_password:
    opensky = OpenSky(username=opensky_username, password=opensky_password)
else:
    opensky = OpenSky()


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
            "category": state.category.value if state.category else None
        }
    }


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
        # Represents the state of the airspace as seen by OpenSky at a particular time.
        # It has the following fields: by reference to http://openskynetwork.github.io/opensky-api/python.html#opensky_api.OpenSkyStates
        # time: int - in seconds since epoch (Unix time stamp). Gives the validity period of all states. 
        # All vectors represent the state of a vehicle with the interval of 1 second.
        # states: list [StateVector] - a list of StateVector or is None if there have been no states received.
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
                "timestamp": states.time
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                "timestamp": states.time
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
