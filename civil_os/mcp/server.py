"""TSD-001 §8 — MCP (Model Context Protocol) in-process server."""
from __future__ import annotations


from typing import TYPE_CHECKING, Any, Callable, Optional


if TYPE_CHECKING:
    pass




class MCPServer:
    """§8 — in-process MCP server (stand-in for real MCP transport).

    Mirrors the MCP contract:
    - tools: callable handlers with required/optional arguments
    - resources: text/JSON/binary data by URI
    - specification: schema describing the server
    """


    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: dict[str, dict] = {}
        self.resources: dict[str, dict] = {}
        self.handlers: dict[str, Callable] = {}


    def register_tool(
        self,
        tool_name: str,
        description: str,
        handler: Callable,
        required_args: list[str] = None,
        optional_args: list[str] = None,
    ) -> None:
        """Register a tool (callable with arguments)."""
        self.tools[tool_name] = {
            "description": description,
            "required_args": required_args or [],
            "optional_args": optional_args or [],
        }
        self.handlers[tool_name] = handler


    def register_resource(
        self,
        uri: str,
        content_type: str,
        content: str,
        description: str = "",
    ) -> None:
        """Register a resource (text/JSON/binary by URI)."""
        self.resources[uri] = {
            "content_type": content_type,
            "content": content,
            "description": description,
        }


    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool (shallow argument validation, then delegate to handler)."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")


        tool_spec = self.tools[tool_name]
        handler = self.handlers[tool_name]


        # Shallow validation: check required args are present
        for required_arg in tool_spec.get("required_args", []):
            if required_arg not in arguments:
                raise ValueError(f"Missing required argument: {required_arg}")


        return handler(**arguments)


    def get_resource(self, uri: str) -> Optional[dict]:
        """Retrieve a resource by URI."""
        return self.resources.get(uri)


    def specification(self) -> dict:
        """Return the MCP specification for this server."""
        return {
            "name": self.name,
            "version": self.version,
            "tools": self.tools,
            "resources": self.resources,
        }


    def list_tools(self) -> list[dict]:
        """List all tools."""
        return [
            {
                "name": name,
                "description": spec["description"],
                "arguments": {
                    "type": "object",
                    "properties": {
                        arg: {"type": "string"}
                        for arg in spec.get("required_args", [])
                        + spec.get("optional_args", [])
                    },
                    "required": spec.get("required_args", []),
                },
            }
            for name, spec in self.tools.items()
        ]


    def list_resources(self) -> list[dict]:
        """List all resources."""
        return [
            {
                "uri": uri,
                "name": uri,
                "description": spec["description"],
                "mimeType": spec["content_type"],
            }
            for uri, spec in self.resources.items()
        ]
