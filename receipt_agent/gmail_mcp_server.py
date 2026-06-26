import sys
import logging
from mcp.server.fastmcp import FastMCP
from receipt_agent.gmail_client import fetch_raw_receipts

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

mcp = FastMCP("gmail-receipt-server")

@mcp.tool()
def fetch_raw_emails(query: str, max_results: int = 25) -> list[dict]:
    """Fetch raw receipt emails from Gmail matching the query."""
    return fetch_raw_receipts(query, max_results)

if __name__ == "__main__":
    mcp.run(transport="stdio")
