"""
Dynamic Tool Injector
Analyzes conversation context and injects only relevant tools/skills

Implements progressive disclosure by loading tools on-demand based on
conversation content, reducing initial context from ~3500 to ~150 tokens.
"""
from typing import List, Dict, Any
from ..skills.registry import SkillRegistry


class DynamicToolInjector:
    """
    Analyzes conversation and determines which tools/skills are relevant.
    Uses keyword matching and heuristics to minimize context consumption.
    """
    
    def __init__(self, mcp_adapter, skill_registry: SkillRegistry):
        """
        Initialize tool injector
        
        Args:
            mcp_adapter: MCP server adapter instance
            skill_registry: Skill registry instance
        """
        self.mcp_adapter = mcp_adapter
        self.skills = skill_registry
        
        # Keyword mappings for context analysis
        self.keyword_mappings = {
            'fuel': {
                'keywords': ['fuel', 'consumption', 'range', 'endurance', 'burn', 'tank', 'refuel'],
                'tools': ['analyze_fuel_consumption'],
                'skills': ['fuel_analysis']
            },
            'pressure': {
                'keywords': ['pressure', 'cabin', 'altitude', 'depressurization', 'leak', 'oxygen'],
                'tools': ['detect_pressure_anomaly'],
                'skills': ['pressure_monitoring']
            },
            'trajectory': {
                'keywords': ['trajectory', 'path', 'route', 'waypoint', 'eta', 'navigation', 'course'],
                'tools': ['predict_trajectory'],
                'skills': ['trajectory_prediction']
            },
            'electrical': {
                'keywords': ['electrical', 'power', 'battery', 'generator', 'voltage', 'current'],
                'tools': ['get_aircraft_status'],
                'skills': ['electrical_monitoring']
            },
            'malfunction': {
                'keywords': ['malfunction', 'failure', 'fault', 'error', 'warning', 'caution', 'emergency'],
                'tools': ['get_aircraft_status'],
                'skills': ['malfunction_detection']
            },
            'status': {
                'keywords': ['status', 'health', 'check', 'systems', 'overall', 'condition'],
                'tools': ['get_aircraft_status'],
                'skills': []
            }
        }
    
    def _extract_keywords(self, conversation_history: List[Dict]) -> List[str]:
        """
        Extract keywords from conversation history
        
        Args:
            conversation_history: List of message dictionaries with 'role' and 'content'
        
        Returns:
            List of keywords found in conversation
        """
        keywords = []
        
        for message in conversation_history:
            content = message.get('content', '').lower()
            words = content.split()
            keywords.extend(words)
        
        return keywords
    
    def analyze_context(self, conversation_history: List[Dict]) -> Dict[str, List[str]]:
        """
        Analyze conversation to determine which tools/skills are relevant.
        Uses lightweight heuristics for fast determination.
        
        Args:
            conversation_history: List of conversation messages
        
        Returns:
            Dictionary with 'tools' and 'skills' lists of relevant IDs
        """
        keywords = self._extract_keywords(conversation_history)
        relevant_tools = set()
        relevant_skills = set()
        
        # Match keywords to tools and skills
        for category, mapping in self.keyword_mappings.items():
            category_keywords = mapping['keywords']
            
            # Check if any category keywords appear in conversation
            if any(kw in keywords for kw in category_keywords):
                relevant_tools.update(mapping['tools'])
                relevant_skills.update(mapping['skills'])
                print(f"  → Context match: {category} category")
        
        # If no specific match, include general status tool
        if not relevant_tools:
            relevant_tools.add('get_aircraft_status')
            print("  → No specific context match, including general status tool")
        
        return {
            'tools': list(relevant_tools),
            'skills': list(relevant_skills)
        }
    
    async def inject_tools(self, session_id: str, tool_names: List[str], skill_names: List[str]) -> Dict:
        """
        Inject specified tools and skills into agent's context for this session.
        Returns lightweight tool definitions and full skill instructions.
        
        Args:
            session_id: Session identifier
            tool_names: List of tool names to inject
            skill_names: List of skill IDs to inject
        
        Returns:
            Dictionary with tools and skills payloads
        """
        tools_payload = []
        skills_payload = []
        
        # Get tool definitions (lightweight signatures)
        for tool_name in tool_names:
            tool_def = self.mcp_adapter.get_tool_definition(tool_name)
            if tool_def:
                tools_payload.append({
                    'name': tool_def['name'],
                    'description': tool_def['description']
                })
        
        # Get full skill instructions (lazy-loaded)
        for skill_id in skill_names:
            skill = self.skills.get_skill(skill_id)
            if skill:
                skills_payload.append({
                    'skill_id': skill.skill_id,
                    'name': skill.name,
                    'description': skill.description,
                    'full_instructions': skill.full_instructions,
                    'category': skill.category,
                    'context_tokens': skill.context_tokens
                })
        
        print(f"  ✓ Injected {len(tools_payload)} tools and {len(skills_payload)} skills for session {session_id}")
        
        return {
            'tools': tools_payload,
            'skills': skills_payload,
            'session_id': session_id,
            'total_items': len(tools_payload) + len(skills_payload)
        }
    
    async def get_tools_for_conversation(self, session_id: str, conversation_history: List[Dict]) -> Dict:
        """
        Analyze conversation and return relevant tools/skills
        
        Args:
            session_id: Session identifier
            conversation_history: List of conversation messages
        
        Returns:
            Tools and skills payload ready for injection
        """
        # Analyze context
        context_analysis = self.analyze_context(conversation_history)
        
        # Inject relevant tools and skills
        payload = await self.inject_tools(
            session_id,
            context_analysis['tools'],
            context_analysis['skills']
        )
        
        return payload
    
    def get_all_available(self) -> Dict:
        """
        Get catalog of all available tools and skills (lightweight)
        
        Returns:
            Lightweight catalog with names and descriptions only
        """
        all_tools = self.mcp_adapter.list_tools()
        all_skills = self.skills.list_skills()
        
        return {
            'tools': all_tools,
            'skills': all_skills,
            'total_tools': len(all_tools),
            'total_skills': len(all_skills)
        }

