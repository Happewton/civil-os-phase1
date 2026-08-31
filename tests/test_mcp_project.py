"""Tests for MCP server."""
import pytest
from civil_os.mcp import MCPServer, create_mcp_project_server
from civil_os.cpo import CivilProjectOrchestrator


def test_mcp_server_creation():
    """Test basic MCP server creation."""
    server = MCPServer("test-server", version="1.0.0")
    assert server.name == "test-server"
    assert server.version == "1.0.0"


def test_mcp_tool_registration():
    """Test MCP tool registration."""
    server = MCPServer("test")
    
    def my_handler(arg1: str) -> str:
        return f"Result: {arg1}"
    
    server.register_tool(
        "test_tool",
        "Test description",
        my_handler,
        required_args=["arg1"],
    )
    
    assert "test_tool" in server.tools
    result = server.call_tool("test_tool", {"arg1": "hello"})
    assert result == "Result: hello"


def test_mcp_tool_validation():
    """Test MCP tool argument validation."""
    server = MCPServer("test")
    
    def my_handler(required_arg: str) -> str:
        return required_arg
    
    server.register_tool(
        "test_tool",
        "Test",
        my_handler,
        required_args=["required_arg"],
    )
    
    # Missing required argument should fail
    with pytest.raises(ValueError):
        server.call_tool("test_tool", {})


def test_mcp_resource_registration():
    """Test MCP resource registration."""
    server = MCPServer("test")
    server.register_resource(
        "resource://test",
        "application/json",
        '{"test": "data"}',
        description="Test resource",
    )
    
    resource = server.get_resource("resource://test")
    assert resource is not None
    assert resource["content_type"] == "application/json"


def test_mcp_project_server_creation(cpo):
    """Test mcp-project server creation."""
    server = create_mcp_project_server(cpo)
    
    assert server.name == "mcp-project"
    assert "create_project" in server.tools
    assert "register_site" in server.tools
    assert "assemble_ecp" in server.tools
    assert "create_task" in server.tools


def test_mcp_project_create_project_tool(cpo):
    """Test create_project tool."""
    server = create_mcp_project_server(cpo)
    
    result = server.call_tool("create_project", {
        "name": "Test Project",
        "project_type": "water",
        "country": "SA",
        "latitude": 24.7,
        "longitude": 46.7,
    })
    
    assert "project_id" in result
    assert result["name"] == "Test Project"


def test_mcp_project_list_projects_tool(cpo):
    """Test list_projects tool."""
    # Create a project first
    cpo.create_project(
        name="Test Project",
        project_type="water",
        country="SA",
        latitude=24.7,
        longitude=46.7,
    )
    
    server = create_mcp_project_server(cpo)
    result = server.call_tool("list_projects", {})
    
    assert "projects" in result
    assert len(result["projects"]) >= 1


def test_mcp_server_specification():
    """Test MCP server specification output."""
    server = MCPServer("test-server", version="1.0.0")
    server.register_tool("tool1", "Description 1", lambda: "result", required_args=["arg1"])
    server.register_resource("resource://1", "text/plain", "content")
    
    spec = server.specification()
    assert spec["name"] == "test-server"
    assert "tool1" in spec["tools"]
    assert "resource://1" in spec["resources"]
