"""
Aerospace Control MCP Server
FastMCP server with lazy tool loading and progressive disclosure

Uses adapter pattern for version-agnostic FastMCP integration,
allowing seamless migration from v2 to v3 when released.
"""
from typing import Dict, Any, List
from .mcp_adapter import get_mcp_adapter

# Use adapter instead of direct FastMCP import for version flexibility
mcp_adapter = get_mcp_adapter()
mcp = mcp_adapter.create_server("aerospace-control-mcp")

# Progressive tool disclosure registry
# Tracks which tools are actively being used in each session
_active_tools: Dict[str, bool] = {}


# ============================================================================
# AEROSPACE MONITORING TOOLS
# ============================================================================

async def analyze_fuel_consumption(
    flight_id: str,
    current_fuel_level: float,
    fuel_capacity: float,
    distance_traveled: float,
    distance_remaining: float,
    current_altitude: int,
    airspeed: float,
    weather_conditions: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Analyzes fuel consumption patterns and predicts remaining flight time.
    Detects anomalies and recommends corrective actions.
    
    Args:
        flight_id: Unique flight identifier
        current_fuel_level: Current fuel in kg or gallons
        fuel_capacity: Maximum fuel capacity
        distance_traveled: Distance covered so far (km or nm)
        distance_remaining: Remaining distance to destination
        current_altitude: Current flight altitude (feet)
        airspeed: Current airspeed (knots)
        weather_conditions: Optional weather data (wind, temperature)
    
    Returns:
        Analysis with fuel status, predicted endurance, and recommendations
    """
    fuel_percentage = (current_fuel_level / fuel_capacity) * 100
    burn_rate = current_fuel_level / distance_traveled if distance_traveled > 0 else 0
    predicted_range = current_fuel_level / burn_rate if burn_rate > 0 else 0
    
    # Determine status
    status = "NORMAL"
    if fuel_percentage < 10:
        status = "CRITICAL"
    elif fuel_percentage < 15:
        status = "LOW"
    
    # Check for anomalies (burn rate deviation)
    expected_burn_rate = fuel_capacity * 0.02  # Simplified: 2% per segment
    deviation = abs(burn_rate - expected_burn_rate) / expected_burn_rate * 100 if expected_burn_rate > 0 else 0
    
    anomaly_detected = deviation > 15
    
    recommendations = []
    if status == "CRITICAL":
        recommendations.append("URGENT: Initiate emergency fuel procedures")
        recommendations.append("Identify nearest suitable diversion airport")
        recommendations.append("Declare minimum fuel or emergency if required")
    elif status == "LOW":
        recommendations.append("Monitor fuel closely")
        recommendations.append("Consider fuel-optimized altitude and speed")
        recommendations.append("Prepare diversion plan")
    
    if anomaly_detected:
        recommendations.append(f"Fuel consumption anomaly detected: {deviation:.1f}% deviation")
        recommendations.append("Investigate potential causes: weather, routing, aircraft systems")
    
    return {
        "flight_id": flight_id,
        "fuel_status": status,
        "fuel_remaining": current_fuel_level,
        "fuel_percentage": round(fuel_percentage, 2),
        "burn_rate": round(burn_rate, 2),
        "predicted_range": round(predicted_range, 2),
        "can_reach_destination": predicted_range >= distance_remaining,
        "anomaly_detected": anomaly_detected,
        "deviation_percentage": round(deviation, 2) if anomaly_detected else 0,
        "recommendations": recommendations
    }


async def detect_pressure_anomaly(
    cabin_pressure: float,
    current_altitude: int,
    rate_of_change: float,
    external_pressure: float = None
) -> Dict[str, Any]:
    """
    Detects cabin pressure system anomalies and suggests corrective actions.
    Monitors for rapid depressurization and slow leaks.
    
    Args:
        cabin_pressure: Current cabin pressure in PSI
        current_altitude: Aircraft altitude in feet
        rate_of_change: Pressure change rate in PSI/minute
        external_pressure: Optional external atmospheric pressure
    
    Returns:
        Pressure analysis with status and recommended actions
    """
    # Expected cabin pressure at altitude (simplified model)
    # Typical cruise: 8,000 ft cabin altitude = 11.3 PSI at 35,000 ft actual
    expected_cabin_pressure = 14.7 if current_altitude < 8000 else 11.3
    
    pressure_delta = abs(cabin_pressure - expected_cabin_pressure)
    pressure_ok = pressure_delta < 1.0  # Within 1 PSI tolerance
    
    # Check rate of change
    rapid_depressurization = abs(rate_of_change) > 2.0
    slow_leak = abs(rate_of_change) > 0.5 and not rapid_depressurization
    
    status = "NORMAL"
    severity = "INFO"
    
    if rapid_depressurization:
        status = "CRITICAL"
        severity = "EMERGENCY"
    elif slow_leak:
        status = "CAUTION"
        severity = "WARNING"
    elif not pressure_ok:
        status = "ABNORMAL"
        severity = "CAUTION"
    
    recommendations = []
    if rapid_depressurization:
        recommendations.append("EMERGENCY: Rapid depressurization detected")
        recommendations.append("Don oxygen masks immediately")
        recommendations.append("Initiate emergency descent to 10,000 ft or below")
        recommendations.append("Declare emergency with ATC")
    elif slow_leak:
        recommendations.append("Slow pressure leak detected")
        recommendations.append("Monitor pressure trend")
        recommendations.append("Engage backup pressurization if available")
        recommendations.append("Consider diversion if rate increases")
    elif not pressure_ok:
        recommendations.append("Cabin pressure outside normal range")
        recommendations.append("Check pressurization system")
        recommendations.append("Verify outflow valve operation")
    
    return {
        "status": status,
        "severity": severity,
        "cabin_pressure_psi": round(cabin_pressure, 2),
        "expected_pressure_psi": round(expected_cabin_pressure, 2),
        "pressure_delta": round(pressure_delta, 2),
        "rate_of_change": round(rate_of_change, 2),
        "rapid_depressurization": rapid_depressurization,
        "slow_leak_detected": slow_leak,
        "recommendations": recommendations
    }


async def predict_trajectory(
    current_position: Dict[str, float],
    velocity: Dict[str, float],
    heading: float,
    weather_conditions: Dict[str, Any] = None,
    flight_plan: List[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Predicts aircraft trajectory considering performance data and weather.
    Calculates estimated time of arrival and potential conflicts.
    
    Args:
        current_position: {'lat': float, 'lon': float, 'altitude': float}
        velocity: {'groundspeed': float, 'vertical_rate': float}
        heading: True heading in degrees
        weather_conditions: Wind speed, direction, temperature
        flight_plan: List of waypoints [{'lat': float, 'lon': float}, ...]
    
    Returns:
        Trajectory prediction with waypoints and timing
    """
    import math
    
    groundspeed = velocity.get('groundspeed', 450)  # knots
    vertical_rate = velocity.get('vertical_rate', 0)  # feet per minute
    
    # Simplified trajectory calculation
    # In production, this would use more sophisticated models
    
    predicted_waypoints = []
    current_lat = current_position['lat']
    current_lon = current_position['lon']
    current_alt = current_position.get('altitude', 35000)
    
    # If no flight plan, project straight ahead for 100 nm
    if not flight_plan:
        # Project position 100 nautical miles ahead
        distance_nm = 100
        distance_deg = distance_nm / 60  # Rough approximation
        
        heading_rad = math.radians(heading)
        next_lat = current_lat + (distance_deg * math.cos(heading_rad))
        next_lon = current_lon + (distance_deg * math.sin(heading_rad))
        
        predicted_waypoints.append({
            'lat': round(next_lat, 4),
            'lon': round(next_lon, 4),
            'altitude': current_alt,
            'eta_minutes': round((distance_nm / groundspeed) * 60, 1)
        })
    else:
        # Calculate ETAs for planned waypoints
        for i, waypoint in enumerate(flight_plan):
            # Simple great circle distance approximation
            lat_diff = abs(waypoint['lat'] - current_lat)
            lon_diff = abs(waypoint['lon'] - current_lon)
            distance_deg = math.sqrt(lat_diff**2 + lon_diff**2)
            distance_nm = distance_deg * 60
            
            eta_hours = distance_nm / groundspeed
            eta_minutes = eta_hours * 60
            
            predicted_waypoints.append({
                'waypoint_number': i + 1,
                'lat': waypoint['lat'],
                'lon': waypoint['lon'],
                'distance_nm': round(distance_nm, 1),
                'eta_minutes': round(eta_minutes, 1)
            })
            
            current_lat = waypoint['lat']
            current_lon = waypoint['lon']
    
    # Weather impact assessment
    weather_impact = "NONE"
    if weather_conditions:
        wind_speed = weather_conditions.get('wind_speed', 0)
        if wind_speed > 50:
            weather_impact = "MODERATE"
        if wind_speed > 80:
            weather_impact = "SIGNIFICANT"
    
    return {
        "current_position": current_position,
        "heading": heading,
        "groundspeed_knots": groundspeed,
        "predicted_waypoints": predicted_waypoints,
        "weather_impact": weather_impact,
        "prediction_confidence": "HIGH" if not weather_conditions else "MEDIUM"
    }


async def get_aircraft_status(
    flight_id: str,
    systems_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Comprehensive aircraft systems status check.
    Aggregates data from multiple systems and identifies issues.
    
    Args:
        flight_id: Unique flight identifier
        systems_data: Dictionary containing various system readings
    
    Returns:
        Overall status with system health indicators
    """
    systems_health = {}
    overall_status = "NORMAL"
    alerts = []
    
    # Check fuel system
    if 'fuel' in systems_data:
        fuel_pct = systems_data['fuel'].get('percentage', 100)
        systems_health['fuel'] = "NORMAL" if fuel_pct > 15 else "LOW" if fuel_pct > 10 else "CRITICAL"
        if systems_health['fuel'] != "NORMAL":
            alerts.append(f"Fuel: {systems_health['fuel']} ({fuel_pct}%)")
    
    # Check pressurization
    if 'pressure' in systems_data:
        pressure_ok = systems_data['pressure'].get('normal', True)
        systems_health['pressure'] = "NORMAL" if pressure_ok else "ABNORMAL"
        if not pressure_ok:
            alerts.append("Pressurization: Abnormal")
    
    # Check electrical
    if 'electrical' in systems_data:
        voltage = systems_data['electrical'].get('voltage', 28)
        systems_health['electrical'] = "NORMAL" if 26 <= voltage <= 30 else "ABNORMAL"
        if systems_health['electrical'] != "NORMAL":
            alerts.append(f"Electrical: Voltage {voltage}V (expected 28V)")
    
    # Check hydraulics
    if 'hydraulics' in systems_data:
        pressure_psi = systems_data['hydraulics'].get('pressure', 3000)
        systems_health['hydraulics'] = "NORMAL" if pressure_psi > 2800 else "LOW"
        if systems_health['hydraulics'] != "NORMAL":
            alerts.append(f"Hydraulics: {pressure_psi} PSI (low)")
    
    # Determine overall status
    if any(status == "CRITICAL" for status in systems_health.values()):
        overall_status = "CRITICAL"
    elif any(status == "ABNORMAL" for status in systems_health.values()):
        overall_status = "CAUTION"
    elif any(status == "LOW" for status in systems_health.values()):
        overall_status = "ADVISORY"
    
    return {
        "flight_id": flight_id,
        "overall_status": overall_status,
        "systems_health": systems_health,
        "alerts": alerts,
        "systems_checked": list(systems_health.keys())
    }


# Register tools with MCP adapter
# Tools are defined but only signatures are sent to context initially
mcp_adapter.register_tool(analyze_fuel_consumption)
mcp_adapter.register_tool(detect_pressure_anomaly)
mcp_adapter.register_tool(predict_trajectory)
mcp_adapter.register_tool(get_aircraft_status)

print(f"✓ MCP server initialized with {len(mcp_adapter.list_tools())} tools")


def get_server():
    """Get the MCP server instance"""
    return mcp


def get_adapter():
    """Get the MCP adapter instance"""
    return mcp_adapter

