"""One authenticated, read-only MCP tool using the official Python MCP SDK."""
import os
import httpx
from mcp.server.fastmcp import FastMCP
mcp=FastMCP("Unofficial AZ-900 study tools")

@mcp.tool()
async def get_my_readiness() -> dict:
    """Return the signed-in learner's practice readiness by AZ-900 topic."""
    token=os.getenv("STUDY_ACCESS_TOKEN")
    if not token:
        raise ValueError("Set STUDY_ACCESS_TOKEN to your unexpired API login token")
    async with httpx.AsyncClient(timeout=15) as client:
        result=await client.get(os.getenv("STUDY_API_URL","http://localhost:8000").rstrip("/")+"/readiness",headers={"Authorization":f"Bearer {token}"})
        result.raise_for_status()
        return result.json()

if __name__=="__main__": mcp.run(transport="stdio")
