# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SkySentinel is an intelligent aerospace surveillance system that integrates real-time aircraft data from OpenSky Network with AI agent capabilities via FastMCP (Model Context Protocol). The backend serves as both a REST API for aircraft data and an MCP server for AI agent orchestration.

## Common Development Commands

### Running the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Run the FastAPI server
python app/main.py

# Or use uvicorn directly with auto-reload
uvicorn app.main:app --reload

# Or use the provided script
./run.sh
```

### Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For development with additional tools
pip install -e ".[dev]"

# Check FastMCP compatibility (before upgrading)
python scripts/check_fastmcp_compatibility.py
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov=app

# Run specific test file
pytest tests/mcp/test_specific.py
```

### Environment Configuration

Create a `.env` file in the project root with:

```env
# OpenSky OAuth2 credentials (recommended for 10x higher rate limits)
OPENSKY_CLIENT_ID=your_client_id_here
OPENSKY_CLIENT_SECRET=your_client_secret_here

# Server configuration
HOST=0.0.0.0
PORT=8000
```

Get OAuth2 credentials from: https://opensky-network.org/my-opensky

## Architecture Overview

### Directory Structure

- `app/` - Legacy FastAPI application (primary entry point)
  - `main.py` - Main FastAPI app with OpenSky integration and MCP/agent endpoints
  - `oauth2_client.py` - OpenSky OAuth2 client with automatic token refresh

- `src/` - New modular architecture for AI agent ecosystem
  - `mcp_server/` - FastMCP server implementation
  - `agents/` - Multi-agent coordination
  - `api/` - RESTful API endpoints for MCP operations
  - `skills/` - Procedural knowledge registry

- `tests/` - Test suite
- `scripts/` - Utility scripts

### Key Architectural Patterns

#### 1. Dual-Mode API Architecture

The application serves two distinct purposes:
- **REST API Mode**: Traditional HTTP endpoints for aircraft data (GeoJSON format)
- **MCP Server Mode**: Model Context Protocol server for AI agent integration

Both modes are integrated into a single FastAPI application via router inclusion (see `app/main.py:515-544`).

#### 2. OpenSky Network Integration

- **OAuth2 Flow**: Automatic token management with 5-minute buffer before expiration (`app/oauth2_client.py`)
- **Automatic Retry**: Transparent token refresh on 401 errors (max 2 retries)
- **Caching Layer**: 45-second TTL in-memory cache to reduce API consumption by ~73%
- **Default Bounding Box**: Georgia state coverage (24.9 sq deg = 1 credit vs 4 credits for global queries)

The unified fetch function `fetch_opensky_api()` handles authentication, retry logic, rate limit tracking, and caching (`app/main.py:114-187`).

#### 3. Progressive Disclosure Pattern (MCP Integration)

**Problem**: Loading all MCP tools and skills upfront consumes massive context tokens (~5000+ tokens).

**Solution**: Three-tier lazy loading system:

1. **Initial Catalog** (~10 tokens per item): Names and brief descriptions only
2. **Context-Aware Injection**: Analyze conversation to determine relevant tools/skills
3. **On-Demand Loading**: Full instructions loaded only when agent decides to use them

Implementation:
- `src/mcp_server/tool_injector.py` - Analyzes conversation context
- `src/skills/registry.py` - Skill catalog with lazy-loaded instructions
- `src/api/mcp_endpoints.py` - REST endpoints for catalog/injection/execution

**Result**: ~95% reduction in initial context token usage.

#### 4. FastMCP Adapter Pattern

**Purpose**: Isolate version-specific FastMCP code to enable seamless v2→v3 migration.

The adapter abstracts FastMCP operations behind a common interface (`src/mcp_server/mcp_adapter.py`):
- `FastMCPv2Adapter` - Current implementation (fastmcp>=2.11.0,<3.0.0)
- `FastMCPv3Adapter` - Placeholder for future v3 migration

This pattern allows upgrading FastMCP without changing tool definitions or business logic.

**Important**: Always use `mcp_adapter` instead of importing FastMCP directly.

#### 5. Agent Message Bus

WebSocket-based pub/sub system for multi-agent coordination (`src/agents/message_bus.py`):

- **Topic-based subscriptions**: Agents subscribe to specific event topics
- **Direct messaging**: Point-to-point communication between agents
- **Capability-based collaboration**: Request agents with specific capabilities
- **Lifecycle management**: Automatic cleanup on disconnect

Accessible via WebSocket at `/ws/agents/{agent_id}`.

#### 6. Session Management

AI sessions track agent state and API credentials (`src/api/session_manager.py`):

- **In-memory storage** (development) - Replace with Redis for production
- **Session lifecycle**: Create, toggle (enable/disable), retrieve, delete
- **Encrypted key storage**: API keys stored as encrypted hashes (never plaintext)
- **Session validation**: All MCP endpoints validate session via `X-Session-ID` header

### Data Flow

```
External Request
    ↓
FastAPI Router (app/main.py)
    ↓
    ├─→ REST API Endpoints → OpenSky OAuth2 Client → OpenSky Network API
    │                            ↓
    │                        Cache Layer (45s TTL)
    │                            ↓
    │                    GeoJSON Transformation → Response
    │
    └─→ MCP Endpoints → Session Validation
                           ↓
                    Tool Injector (analyzes conversation)
                           ↓
                    MCP Adapter → Tool Registry & Skill Registry
                           ↓
                    Progressive Disclosure → Tool Execution
```

### MCP Tools Available

The MCP server provides aerospace monitoring tools (`src/mcp_server/server.py`):

1. **analyze_fuel_consumption** - Fuel analysis with anomaly detection
2. **detect_pressure_anomaly** - Cabin pressure monitoring and alerts
3. **predict_trajectory** - Aircraft path prediction with weather factors
4. **get_aircraft_status** - Multi-system health aggregation

Each tool has comprehensive docstrings that serve as the tool description in MCP context.

### Rate Limiting Strategy

OpenSky Network charges by request:
- **Anonymous**: 400 credits/day
- **OAuth2**: 4000 credits/day (10x upgrade)

Cost per request varies by area:
- 0-25 sq deg = 1 credit
- 25-100 sq deg = 2 credits
- 100-400 sq deg = 3 credits
- >400 sq deg or global = 4 credits

**Optimization Strategy**:
1. Default to Georgia state bounding box (24.9 sq deg = 1 credit)
2. 45-second cache reduces requests by ~73%
3. Combined savings: ~91% reduction in API consumption

Rate limit info is returned in all responses via `rate_limit` field.

## Important Implementation Notes

### Environment Variables

The application uses two sets of credentials:
- **OpenSky OAuth2** (`OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET`) - Required for 10x rate limits
- If OAuth2 not configured, falls back to anonymous mode with reduced limits

### Python Path Considerations

The `app/main.py` file modifies `sys.path` to enable imports from `src/` module:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

This allows importing from `src.api`, `src.agents`, etc. without requiring package installation.

### Dependency Pinning Strategy

FastMCP is pinned to v2.x line (`fastmcp>=2.11.0,<3.0.0`) to prevent breaking changes from v3.0. The adapter pattern enables controlled migration when ready.

### CORS Configuration

CORS is enabled for all origins (`allow_origins=["*"]`) to support frontend integration. Restrict this in production deployments.

### Cache Considerations

The 45-second cache (`_api_cache` in `app/main.py:49-56`) is in-memory and per-process:
- Cache is not shared across multiple worker processes
- Cache is lost on application restart
- For production with multiple workers, use Redis or similar

### Session Storage

Session storage (`_sessions` in `src/api/session_manager.py:42`) is in-memory. The code explicitly notes:

```python
# TODO: Replace with Redis for production deployment
```

For production, implement Redis-backed session storage to support multiple instances.

### WebSocket Connection Management

Agent WebSocket connections (`/ws/agents/{agent_id}`) maintain persistent connections:
- Automatic cleanup on disconnect (`message_bus.unregister_agent`)
- Broadcasting to all subscribed agents except sender
- Error handling for failed message delivery

## API Endpoint Reference

### Primary Data Endpoints

- `GET /api/v1/airspace?limit=50` - Georgia state aircraft data (default, 1 credit)
- `GET /api/v1/airspace/region` - Custom bounding box query (variable credits)
- `GET /api/v1/states/authenticated` - Full authenticated access (requires OAuth2)
- `GET /api/v1/states/aircraft?icao24=<code>` - Specific aircraft by ICAO24
- `GET /api/v1/status` - Backend and OpenSky API status

### MCP/AI Agent Endpoints

- `GET /mcp/tools/list` - Lightweight tool catalog
- `POST /mcp/tools/inject` - Context-aware tool injection
- `POST /mcp/tools/execute` - Execute tool on backend
- `GET /mcp/skills` - List all skills
- `GET /mcp/skills/{skill_id}` - Get full skill instructions (lazy-loaded)
- `GET /mcp/status` - MCP server status

### Session Management Endpoints

- `POST /api/v1/ai-session/create` - Create new AI session
- `POST /api/v1/ai-session/{id}/toggle` - Enable/disable AI features
- `GET /api/v1/ai-session/{id}` - Get session info
- `DELETE /api/v1/ai-session/{id}` - Delete session
- `GET /api/v1/ai-session/` - List all sessions (debug)

### WebSocket Endpoints

- `WS /ws/agents/{agent_id}` - Agent message bus connection

All MCP and session endpoints require `X-Session-ID` header for authentication.

## Working with the Codebase

### Adding New MCP Tools

1. Define tool function in `src/mcp_server/server.py` with comprehensive docstring
2. Register tool with adapter: `mcp_adapter.register_tool(your_function)`
3. Tool automatically appears in catalog and can be injected via conversation analysis

### Adding New Skills

1. Create skill definition in `src/skills/registry.py` within `_load_aerospace_skills()`
2. Include: skill_id, name, short description, full instructions, category, context_tokens
3. Skill automatically appears in catalog and can be lazy-loaded

### Modifying OpenSky Integration

The unified fetch function (`app/main.py:fetch_opensky_api()`) is the single point for all OpenSky API calls. Modifications to authentication, caching, or retry logic should be made here.

### Extending the Agent Message Bus

Add new message types by handling additional `action` values in `handle_agent_websocket()` function (`src/agents/message_bus.py:242-305`).

## Testing Strategy

Test structure:
- Unit tests for individual components
- Integration tests for API endpoints
- MCP tool execution tests

Run tests with proper Python path:
```bash
PYTHONPATH=/Users/dperezalvarez/Documents/pocs/skysentinel-backend python -m pytest
```

## Docker Deployment

The included Dockerfile creates a production-ready container:

```bash
docker build -t skysentinel-backend .
docker run -p 8000:8000 \
  -e OPENSKY_CLIENT_ID=your_id \
  -e OPENSKY_CLIENT_SECRET=your_secret \
  skysentinel-backend
```

For Cloud Run or similar platforms, the application auto-detects `PORT` environment variable.
