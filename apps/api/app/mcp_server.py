"""MCP is served by the authenticated API at /api/v1/mcp.

Run uvicorn app.main:app from apps/api. The demonstration-only stdio
server has been retired; all tools now use the authenticated tenant.
"""
from app.api.v1.advanced import TOOLS, mcp_rpc

__all__ = ["TOOLS", "mcp_rpc"]
