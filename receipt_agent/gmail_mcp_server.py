import sys
import logging
from mcp.server.fastmcp import FastMCP
from receipt_agent.gmail_client import fetch_raw_receipts
from receipt_agent.parser import parse_receipt

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

mcp = FastMCP("gmail-receipt-server")

@mcp.tool()
def get_spending_receipts(query: str, max_results: int = 25) -> dict:
    """Fetch AND parse Gmail receipt emails matching the query in a single call.

    This replaces the old two-step design (a lightweight MCP existence-check
    followed by a separate Python re-fetch), which queried the Gmail API twice
    for the same data. Now the full pipeline — fetch raw emails, cap oversized
    HTML at 100KB, and run them through parse_receipt() — happens once, here,
    and only compact structured results are sent back to the LLM.

    Args:
        query: Gmail search query (e.g. "after:2026-02-01 before:2026-02-11 receipt").
        max_results: Max number of messages to fetch (default: 25).

    Returns:
        dict with "status", "count", and "receipts" — a list of parsed receipt
        dicts (each with date, subject, total, currency, merchant). No raw HTML
        is included, keeping this small enough to safely return to the LLM.
    """
    try:
        raw_emails = fetch_raw_receipts(query, max_results)
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to fetch emails: {str(e)}"}

    parsed_receipts = []
    for email in raw_emails:
        html = email.get("html", "")
        if len(html) > 100000:
            email["html"] = html[:100000] + "\n...[TRUNCATED]..."
        try:
            parsed = parse_receipt(email)
            if parsed and (parsed.get("total") is not None or parsed.get("merchant") != "Unknown"):
                parsed_receipts.append(parsed)
        except Exception:
            continue

    return {
        "status": "success",
        "count": len(parsed_receipts),
        "receipts": parsed_receipts,
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")

if __name__ == "__main__":
    mcp.run(transport="stdio")