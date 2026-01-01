"""
MCP API Endpoints
RESTful API for FastMCP server interaction

Provides HTTP endpoints for MCP operations:
- Tool catalog listing
- Dynamic tool injection based on conversation context
- Tool execution
- Skill retrieval
"""
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ..mcp_server.server import get_adapter
from ..mcp_server.tool_injector import DynamicToolInjector
from ..skills.registry import SkillRegistry
from .session_manager import is_session_valid

router = APIRouter(prefix="/mcp", tags=["MCP"])

# Initialize components
skill_registry = SkillRegistry()
mcp_adapter = get_adapter()
tool_injector = DynamicToolInjector(mcp_adapter, skill_registry)


class ToolInjectRequest(BaseModel):
    """Request to inject tools based on conversation"""
    conversation: List[Dict[str, str]]  # List of {role, content} messages


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool"""
    tool: str
    params: Dict[str, Any]


@router.get("/tools/list")
async def list_tools(x_session_id: Optional[str] = Header(None)):
    """
    Get lightweight catalog of all available tools and skills
    
    Headers:
        X-Session-ID: Optional session identifier
    
    Returns:
        Catalog of tools (names + brief descriptions) and skills
    """
    # Verify session if provided
    if x_session_id and not is_session_valid(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled session"
        )
    
    catalog = tool_injector.get_all_available()
    
    return {
        "tools": catalog['tools'],
        "skills": catalog['skills'],
        "metadata": {
            "total_tools": catalog['total_tools'],
            "total_skills": catalog['total_skills'],
            "description": "Aerospace monitoring tools and skills catalog"
        }
    }


@router.post("/tools/inject")
async def inject_tools(
    request: ToolInjectRequest,
    x_session_id: str = Header(...)
):
    """
    Analyze conversation and inject relevant tools/skills
    
    Progressive disclosure: Returns only tools/skills relevant to conversation,
    reducing context consumption by ~95% compared to loading everything upfront.
    
    Headers:
        X-Session-ID: Session identifier (required)
    
    Body:
        conversation: List of message objects with role and content
    
    Returns:
        Injected tools and skills with full instructions
    """
    # Verify session
    if not is_session_valid(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled session"
        )
    
    try:
        # Analyze conversation and get relevant tools/skills
        payload = await tool_injector.get_tools_for_conversation(
            x_session_id,
            request.conversation
        )
        
        return {
            "status": "success",
            "session_id": x_session_id,
            "tools": payload['tools'],
            "skills": payload['skills'],
            "metadata": {
                "injected_items": payload['total_items'],
                "context_efficiency": "~95% reduction vs loading all tools upfront"
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool injection failed: {str(e)}"
        )


@router.post("/tools/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    x_session_id: str = Header(...)
):
    """
    Execute a tool on the backend
    
    Headers:
        X-Session-ID: Session identifier (required)
    
    Body:
        tool: Tool name
        params: Tool parameters
    
    Returns:
        Tool execution result
    """
    # Verify session
    if not is_session_valid(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled session"
        )
    
    try:
        # Get tool definition
        tool_def = mcp_adapter.get_tool_definition(request.tool)
        
        if not tool_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {request.tool}"
            )
        
        # Execute tool
        tool_function = tool_def['function']
        result = await tool_function(**request.params)
        
        return {
            "status": "success",
            "tool": request.tool,
            "result": result
        }
    
    except TypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters for tool {request.tool}: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: str,
    x_session_id: Optional[str] = Header(None)
):
    """
    Get full skill instructions (lazy-loaded)
    
    Args:
        skill_id: Skill identifier
    
    Headers:
        X-Session-ID: Optional session identifier
    
    Returns:
        Complete skill with full procedural instructions
    """
    # Verify session if provided
    if x_session_id and not is_session_valid(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled session"
        )
    
    skill = skill_registry.get_skill(skill_id)
    
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill not found: {skill_id}"
        )
    
    return {
        "skill_id": skill.skill_id,
        "name": skill.name,
        "description": skill.description,
        "full_instructions": skill.full_instructions,
        "category": skill.category,
        "context_tokens": skill.context_tokens,
        "prerequisites": skill.prerequisites
    }


@router.get("/skills")
async def list_skills(
    category: Optional[str] = None,
    x_session_id: Optional[str] = Header(None)
):
    """
    List all skills (lightweight catalog)
    
    Query params:
        category: Optional category filter
    
    Headers:
        X-Session-ID: Optional session identifier
    
    Returns:
        Lightweight skill catalog (without full instructions)
    """
    # Verify session if provided
    if x_session_id and not is_session_valid(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled session"
        )
    
    skills = skill_registry.list_skills(category=category)
    categories = skill_registry.get_categories()
    
    return {
        "skills": skills,
        "categories": categories,
        "total": len(skills),
        "filtered_by": category if category else "none"
    }


@router.get("/status")
async def get_mcp_status():
    """
    Get MCP server status
    
    Returns:
        MCP server health and configuration
    """
    tools = mcp_adapter.list_tools()
    all_skills = skill_registry.list_skills()
    
    return {
        "status": "operational",
        "server_name": "aerospace-control-mcp",
        "tools_registered": len(tools),
        "skills_available": len(all_skills),
        "skill_categories": skill_registry.get_categories(),
        "features": {
            "progressive_disclosure": True,
            "lazy_loading": True,
            "multi_agent_support": True,
            "context_efficiency": "~95% reduction in initial token usage"
        }
    }

