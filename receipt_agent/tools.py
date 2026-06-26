from google.adk.tools import ToolContext
from .parser import parse_receipt

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

