from google.adk.tools import ToolContext
from .parser import parse_receipt
from .gmail_client import fetch_raw_receipts

def store_receipts(receipts: list[dict], tool_context: ToolContext) -> dict:
    """Stores already-parsed receipt data into tool_context.state["receipts"].

    Use this AFTER calling the get_spending_receipts MCP tool. Pass through the
    exact "receipts" list that tool returned — do not re-fetch or re-parse.
    This exists purely to bridge MCP tool output (which the LLM sees as text)
    into ADK session state (which analyst_agent reads), without a second Gmail
    API round-trip.

    Args:
        receipts: The parsed receipt list returned by get_spending_receipts
                  (each dict has date, subject, total, currency, merchant).
        tool_context: ADK ToolContext for state sharing across agents.

    Returns:
        A dict with status and the count of receipts stored.
    """
    if not isinstance(receipts, list):
        return {
            "status": "error",
            "error_message": f"Expected receipts to be a list, got {type(receipts).__name__ if receipts is not None else 'None'}"
        }

    tool_context.state["receipts"] = receipts

    return {
        "status": "success",
        "count": len(receipts),
        # Echo the receipts back so the Streamlit frontend (app.py), which
        # watches collector_agent tool responses for a "receipts" key, can
        # populate its deterministic stats/details card. Without this the
        # card renders empty.
        "receipts": receipts
    }


# --- Legacy tools (kept for reference / app.py compatibility) ---
# These duplicate what get_spending_receipts (in gmail_mcp_server.py) now does
# in a single MCP call. collector_agent no longer uses them directly, since
# routing through both meant Gmail was queried twice for the same data.

def fetch_receipts(emails: list[dict], tool_context: ToolContext) -> dict:
    """Parses retrieved email contents and writes to tool_context.state["receipts"].
    
    Args:
        emails: List of email dictionaries retrieved via MCP.
        tool_context: ToolContext for state sharing across agents.
        
    Returns:
        A dict containing status, count, and lists of receipts or error details.
    """
    if not isinstance(emails, list):
        return {
            "status": "error",
            "error_message": f"Expected emails to be a list, got {type(emails).__name__ if emails is not None else 'None'}"
        }
        
    parsed_receipts = []
    for email in emails:
        if not isinstance(email, dict):
            continue
            
        # Normalize the email format for parse_receipt
        normalized = {
            "id": email.get("id") or email.get("message_id") or email.get("messageId") or "",
            "subject": email.get("subject") or email.get("title") or "",
            "date": email.get("date") or email.get("internalDate") or email.get("receivedAt") or "",
            "html": email.get("html") or email.get("body") or email.get("text") or email.get("snippet") or ""
        }
        
        try:
            parsed = parse_receipt(normalized)
            parsed_receipts.append(parsed)
        except Exception:
            # Continue parsing other receipts if one fails
            continue
            
    tool_context.state["receipts"] = parsed_receipts
    
    return {
        "status": "success",
        "count": len(parsed_receipts),
        "receipts": parsed_receipts
    }


def collect_and_parse_receipts(query: str, max_results: int = 25, tool_context: ToolContext = None) -> dict:
    """Fetches raw receipt emails using Python Gmail client, parses them, 
    stores them in tool_context.state, and returns only a compact summary.
    
    Args:
        query: Gmail search query.
        max_results: Max receipts to fetch (default: 25).
        tool_context: ADK ToolContext.
    """
    if tool_context is None:
        tool_context = ToolContext()
        
    try:
        raw_emails = fetch_raw_receipts(query, max_results)
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to fetch emails: {str(e)}"
        }
        
    parsed_receipts = []
    parse_failures = 0
    merchants_seen = set()
    dates = []
    
    for email in raw_emails:
        # Defense in depth: cap size of raw HTML processed to 100KB
        html = email.get("html", "")
        if len(html) > 100000:
            email["html"] = html[:100000] + "\n...[TRUNCATED]..."
            
        try:
            parsed = parse_receipt(email)
            if parsed and (parsed.get("total") is not None or parsed.get("merchant") != "Unknown"):
                parsed_receipts.append(parsed)
                if parsed.get("merchant"):
                    merchants_seen.add(parsed["merchant"])
                if parsed.get("date"):
                    dates.append(parsed["date"])
            else:
                parse_failures += 1
        except Exception:
            parse_failures += 1
            
    # Save the parsed receipts to state key "receipts"
    tool_context.state["receipts"] = parsed_receipts
    
    # Calculate date range
    date_range = "None"
    if dates:
        sorted_dates = sorted(dates)
        date_range = f"{sorted_dates[0]} to {sorted_dates[-1]}"
        
    return {
        "status": "success",
        "count": len(parsed_receipts),
        "date_range": date_range,
        "merchants_seen": list(merchants_seen),
        "parse_failures": parse_failures,
        # Include full parsed list so the caller (app.py) can compute deterministic stats
        # without needing to re-read from ADK session state.
        "receipts": parsed_receipts
    }