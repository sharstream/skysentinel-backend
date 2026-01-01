"""
Skill Registry for Aerospace Monitoring
Implements progressive disclosure pattern for context-efficient AI agents

Skills contain procedural knowledge that is loaded only when needed,
reducing initial context token consumption by ~95%.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel


class Skill(BaseModel):
    """
    Represents a procedural skill for aerospace monitoring
    
    Attributes:
        skill_id: Unique identifier
        name: Human-readable name
        description: Short description (sent to context initially)
        full_instructions: Complete procedural knowledge (lazy-loaded)
        category: Skill category (fuel, pressure, trajectory, electrical, malfunction)
        prerequisites: List of skill IDs required before using this skill
        context_tokens: Estimated token cost when fully loaded
    """
    skill_id: str
    name: str
    description: str  # Short description (sent to context)
    full_instructions: str  # Full procedural knowledge (lazy-loaded)
    category: str  # fuel, pressure, trajectory, electrical, malfunction
    prerequisites: List[str] = []  # Required skills before using this one
    context_tokens: int  # Estimated token cost


class SkillRegistry:
    """
    Registry for aerospace monitoring skills with progressive disclosure
    
    Provides lightweight skill catalog initially (~10 tokens per skill),
    then loads full instructions only when agent decides to use them.
    """
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._load_aerospace_skills()
    
    def _load_aerospace_skills(self):
        """Load predefined aerospace monitoring skills"""
        
        # Fuel Analysis Skill
        self._skills['fuel_analysis'] = Skill(
            skill_id='fuel_analysis',
            name='Fuel System Analysis',
            description='Analyze fuel consumption patterns and detect anomalies',
            full_instructions='''
FUEL ANALYSIS PROCEDURE:
1. Assess current fuel level against flight plan
   - Compare actual vs expected fuel remaining
   - Account for flight duration and distance traveled
   
2. Calculate burn rate vs. expected consumption
   - Fuel flow rate (kg/hour or gallons/hour)
   - Compare to aircraft performance specifications
   
3. Factor in altitude, speed, weather conditions
   - Higher altitudes = more efficient (less drag)
   - Headwinds increase consumption
   - Temperature affects engine efficiency
   
4. Identify anomalies > 10% deviation
   - Log significant deviations
   - Calculate cause (weather, routing, aircraft issue)
   
5. Recommend corrective actions if needed
   - Altitude adjustment
   - Speed optimization
   - Alternative routing
   - Emergency diversion if critical

Critical Thresholds:
- Low fuel warning: < 15% remaining (alert crew)
- Emergency reserve: < 10% remaining (immediate action required)
- Consumption anomaly: > 15% deviation from baseline (investigate cause)
- Point of no return: Calculate distance where diversion is no longer possible

Safety Considerations:
- Always maintain regulatory fuel reserves
- Factor in emergency landing requirements
- Consider alternate airport fuel requirements
            ''',
            category='fuel',
            context_tokens=250
        )
        
        # Pressure Monitoring Skill
        self._skills['pressure_monitoring'] = Skill(
            skill_id='pressure_monitoring',
            name='Cabin Pressure System Monitor',
            description='Monitor cabin pressure and detect system malfunctions',
            full_instructions='''
PRESSURE MONITORING PROTOCOL:
1. Verify cabin pressure matches altitude requirements
   - Compare actual vs target pressure
   - Check against altitude-pressure curves
   
2. Monitor rate of pressure change (should be gradual)
   - Normal: 300-500 feet/minute equivalent
   - Alert if rate > 1000 feet/minute equivalent
   
3. Check for rapid depressurization indicators
   - Sudden pressure drop > 2 PSI/min
   - Audible alarms or warnings
   - Oxygen mask deployment triggers
   
4. Cross-reference with external atmospheric pressure
   - Verify altimeter settings
   - Check for instrument malfunctions
   
5. Alert crew if pressure delta > safe thresholds
   - Immediate notification for rapid decompression
   - Gradual alerts for slow leaks

Safe Ranges:
- Sea level: 14.7 PSI (101.3 kPa)
- Cruise altitude (35,000 ft): 11.3 PSI (77.9 kPa) - equivalent to 8,000 ft cabin altitude
- Max safe rate of change: 2 PSI/min (under normal operations)
- Emergency descent rate: Up to 500 ft/min cabin altitude change

Emergency Procedures:
- Rapid depressurization: Emergency descent to 10,000 ft or below
- Oxygen deployment: Automatic at 14,000 ft cabin altitude
- Backup pressurization systems: Engage if primary fails
            ''',
            category='pressure',
            context_tokens=280
        )
        
        # Trajectory Prediction Skill
        self._skills['trajectory_prediction'] = Skill(
            skill_id='trajectory_prediction',
            name='Trajectory Prediction & Path Analysis',
            description='Predict aircraft trajectories considering performance and weather',
            full_instructions='''
TRAJECTORY PREDICTION PROTOCOL:
1. Gather current aircraft state
   - Position (lat/lon/altitude)
   - Velocity (groundspeed and vertical rate)
   - Heading (true course)
   - Aircraft type and performance characteristics
   
2. Analyze flight plan and route
   - Waypoints and airways
   - Planned altitudes and speeds
   - SID/STAR procedures
   
3. Factor weather conditions
   - Wind speed and direction at altitude
   - Temperature and pressure
   - Turbulence and icing conditions
   - Storm systems and avoidance zones
   
4. Calculate predicted path
   - Great circle route adjustments
   - Wind correction angle
   - Climb/descent profiles
   - Turn radius at various speeds
   
5. Identify potential conflicts
   - Traffic separation requirements
   - Airspace restrictions
   - Weather hazards
   - Terrain clearance

Prediction Accuracy Factors:
- Short-term (0-15 min): 95%+ accuracy
- Medium-term (15-60 min): 85-90% accuracy (weather dependent)
- Long-term (60+ min): 70-80% accuracy (multiple variables)

Safety Buffers:
- Lateral: Minimum 5 NM separation (typically 10 NM)
- Vertical: Minimum 1,000 ft (2,000 ft above FL290)
- Terrain clearance: Minimum 1,000 ft AGL (2,000 ft in mountains)
            ''',
            category='trajectory',
            context_tokens=310
        )
        
        # Electrical System Monitoring Skill
        self._skills['electrical_monitoring'] = Skill(
            skill_id='electrical_monitoring',
            name='Electrical System Health Monitoring',
            description='Monitor electrical systems and detect power anomalies',
            full_instructions='''
ELECTRICAL SYSTEM MONITORING:
1. Check power generation systems
   - Generator output (voltage and amperage)
   - Battery charge state
   - APU electrical status
   
2. Monitor power distribution
   - Bus voltages (should be stable)
   - Load balancing across systems
   - Circuit breaker status
   
3. Identify power anomalies
   - Voltage fluctuations > 5% of nominal
   - Current spikes or drops
   - Frequency instability
   
4. Assess redundancy status
   - Backup generator availability
   - Battery runtime remaining
   - Essential vs non-essential bus status
   
5. Prioritize power allocation
   - Essential systems first (flight controls, navigation)
   - Shed non-essential loads if needed
   - Manage battery reserves

Normal Operating Parameters:
- AC voltage: 115V ±5V (400 Hz)
- DC voltage: 28V ±2V
- Generator output: 40-90 kVA (depending on aircraft)
- Battery capacity: 24-44 Ah (typically)

Critical Alerts:
- Generator failure: Immediate crew notification
- Battery discharge > 50%: Power conservation mode
- Essential bus power loss: Emergency procedures
            ''',
            category='electrical',
            context_tokens=265
        )
        
        # Malfunction Detection Skill
        self._skills['malfunction_detection'] = Skill(
            skill_id='malfunction_detection',
            name='System Malfunction Detection & Diagnosis',
            description='Detect and diagnose aircraft system malfunctions',
            full_instructions='''
MALFUNCTION DETECTION PROTOCOL:
1. Monitor system health indicators
   - Engine parameters (EGT, N1, N2, fuel flow)
   - Hydraulics (pressure, quantity, temperature)
   - Electrical (voltage, current, frequency)
   - Pneumatics (pressure, temperature)
   - Flight controls (position, feedback)
   
2. Identify anomalous patterns
   - Out-of-range values
   - Unusual trends or rates of change
   - Inconsistent sensor readings
   - System warnings or cautions
   
3. Correlate symptoms across systems
   - Multiple related failures may indicate root cause
   - Cascade failures from single point of failure
   - Environmental factors (icing, turbulence)
   
4. Determine severity and urgency
   - CRITICAL: Immediate safety impact (engine fire, depressurization)
   - URGENT: Requires prompt action (single system failure with backup)
   - ADVISORY: Monitor and plan corrective action (degraded performance)
   
5. Recommend corrective actions
   - Emergency procedures for critical malfunctions
   - System isolation or shutdown
   - Alternate operation modes
   - Diversion or continuation decision

Common Malfunction Categories:
- Engine: EGT limits, vibration, oil pressure, surge
- Hydraulics: Low pressure, overheat, contamination
- Electrical: Generator failure, bus fault, battery discharge
- Flight controls: Jam, runaway, asymmetry
- Pressurization: Leak, controller failure, outflow valve stuck

Decision Framework:
- Can mission continue safely? (Yes/No/With limitations)
- Backup systems available and operational?
- Time to malfunction becoming critical?
- Nearest suitable diversion airport?
            ''',
            category='malfunction',
            prerequisites=['electrical_monitoring', 'pressure_monitoring'],
            context_tokens=320
        )
        
        print(f"✓ Loaded {len(self._skills)} aerospace skills")
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        Retrieve full skill instructions (lazy load)
        
        Args:
            skill_id: Unique skill identifier
            
        Returns:
            Complete Skill object with full instructions, or None if not found
        """
        skill = self._skills.get(skill_id)
        if skill:
            print(f"  → Loading full instructions for skill: {skill.name}")
        return skill
    
    def list_skills(self, category: Optional[str] = None) -> List[Dict]:
        """
        Return lightweight skill catalog (descriptions only)
        
        This is what gets sent to the AI agent initially - just names and
        brief descriptions. Full instructions are loaded only when needed.
        
        Args:
            category: Optional filter by category
            
        Returns:
            List of skill metadata (without full instructions)
        """
        skills = self._skills.values()
        if category:
            skills = [s for s in skills if s.category == category]
        
        return [{
            'skill_id': s.skill_id,
            'name': s.name,
            'description': s.description,
            'category': s.category,
            'context_tokens': s.context_tokens
        } for s in skills]
    
    def get_categories(self) -> List[str]:
        """Get all skill categories"""
        return list(set(skill.category for skill in self._skills.values()))
    
    def get_skills_by_category(self, category: str) -> List[Dict]:
        """Get lightweight catalog for specific category"""
        return self.list_skills(category=category)

