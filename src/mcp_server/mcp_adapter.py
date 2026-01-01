"""
MCP Abstraction Layer
Isolates FastMCP-specific code to ease version migration from v2 to v3

This adapter pattern allows seamless migration when FastMCP 3.0 is released
without requiring changes to tool definitions or business logic.
"""
from typing import Callable, Any, Dict, List, Optional
from abc import ABC, abstractmethod

# Version check for future migration preparation
try:
    from fastmcp import __version__ as fastmcp_version
    FASTMCP_MAJOR_VERSION = int(fastmcp_version.split('.')[0])
    print(f"✓ FastMCP v{fastmcp_version} detected")
except Exception as e:
    FASTMCP_MAJOR_VERSION = 2
    fastmcp_version = "2.x.x (assumed)"
    print(f"⚠ Could not detect FastMCP version: {e}")


class MCPServerAdapter(ABC):
    """
    Abstract adapter for MCP server operations.
    Concrete implementations handle version-specific logic.
    """
    
    @abstractmethod
    def create_server(self, name: str) -> Any:
        """Create MCP server instance"""
        pass
    
    @abstractmethod
    def register_tool(self, func: Callable, **kwargs) -> None:
        """Register a tool with the MCP server"""
        pass
    
    @abstractmethod
    def get_tool_definition(self, tool_name: str) -> Optional[Dict]:
        """Get tool definition/signature"""
        pass
    
    @abstractmethod
    def run_server(self, **kwargs) -> None:
        """Start the MCP server"""
        pass
    
    @abstractmethod
    def list_tools(self) -> List[Dict]:
        """List all registered tools"""
        pass


class FastMCPv2Adapter(MCPServerAdapter):
    """FastMCP 2.x implementation"""
    
    def __init__(self):
        from fastmcp import FastMCP
        self.FastMCP = FastMCP
        self._server = None
        self._tools_registry = {}  # Track registered tools
    
    def create_server(self, name: str) -> Any:
        """Create FastMCP 2.x server instance"""
        self._server = self.FastMCP(name)
        print(f"✓ FastMCP v2 server '{name}' created")
        return self._server
    
    def register_tool(self, func: Callable, **kwargs) -> None:
        """Register a tool using v2.x decorator pattern"""
        if self._server:
            # Store tool metadata
            tool_name = func.__name__
            self._tools_registry[tool_name] = {
                'name': tool_name,
                'description': func.__doc__ or '',
                'function': func
            }
            
            # Use v2.x tool decorator
            decorated_func = self._server.tool()(func)
            print(f"  ✓ Tool registered: {tool_name}")
    
    def get_tool_definition(self, tool_name: str) -> Optional[Dict]:
        """Get tool definition from v2 registry"""
        return self._tools_registry.get(tool_name)
    
    def list_tools(self) -> List[Dict]:
        """List all registered tools (lightweight catalog)"""
        return [
            {
                'name': tool['name'],
                'description': tool['description'].split('\n')[0] if tool['description'] else ''
            }
            for tool in self._tools_registry.values()
        ]
    
    def run_server(self, **kwargs) -> None:
        """Start the FastMCP v2 server"""
        if self._server:
            print(f"✓ Starting FastMCP v2 server with {len(self._tools_registry)} tools...")
            self._server.run(**kwargs)


class FastMCPv3Adapter(MCPServerAdapter):
    """
    FastMCP 3.x implementation (placeholder for future migration)
    Update this when v3 API is finalized
    """
    
    def __init__(self):
        raise NotImplementedError(
            "FastMCP 3.0 adapter not yet implemented. "
            "Please use FastMCP 2.x (fastmcp>=2.11.0,<3.0.0)"
        )
    
    def create_server(self, name: str) -> Any:
        """Will be implemented based on v3 API"""
        pass
    
    def register_tool(self, func: Callable, **kwargs) -> None:
        """Will be implemented based on v3 API"""
        pass
    
    def get_tool_definition(self, tool_name: str) -> Optional[Dict]:
        """Will be implemented based on v3 API"""
        pass
    
    def list_tools(self) -> List[Dict]:
        """Will be implemented based on v3 API"""
        pass
    
    def run_server(self, **kwargs) -> None:
        """Will be implemented based on v3 API"""
        pass


def get_mcp_adapter() -> MCPServerAdapter:
    """
    Factory function to get appropriate MCP adapter based on installed version.
    Automatically switches to v3 adapter when available.
    
    Returns:
        MCPServerAdapter: Version-specific adapter instance
        
    Raises:
        ValueError: If unsupported FastMCP version is detected
    """
    if FASTMCP_MAJOR_VERSION == 2:
        print("→ Using FastMCP v2 adapter")
        return FastMCPv2Adapter()
    elif FASTMCP_MAJOR_VERSION >= 3:
        print("→ Using FastMCP v3 adapter")
        return FastMCPv3Adapter()
    else:
        raise ValueError(
            f"Unsupported FastMCP version: {fastmcp_version}. "
            "Please install fastmcp>=2.11.0,<3.0.0"
        )

