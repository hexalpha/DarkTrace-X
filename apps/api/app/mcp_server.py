"""Optional, separately deployed MCP server for read-only, defensive analyst workflows."""

from mcp.server.fastmcp import FastMCP

from app.services.intelligence import intelligence_service

mcp = FastMCP("DarkTrace X Intelligence")


@mcp.tool()
def lookup_indicator(value: str) -> list[dict[str, object]]:
    """Return tenant-demo IOC metadata. Production validates identity and tenant context at the transport boundary."""
    results = intelligence_service.list_iocs("demo-tenant", value)
    return [item.model_dump(mode="json") for item in results]


@mcp.tool()
def current_priority_alerts() -> list[dict[str, object]]:
    """Return current defensive priority alerts; no side effects or external source access."""
    return [item.model_dump(mode="json") for item in intelligence_service.list_alerts("demo-tenant")]


if __name__ == "__main__":
    mcp.run()

