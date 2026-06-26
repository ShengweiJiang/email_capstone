import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service():
    """Authenticates the user and returns the Gmail API service instance."""
    creds = None
    # Token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "credentials.json not found in the root directory. Please download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def extract_html_part(payload) -> str:
    """Recursively walks the MIME payload tree to extract the first text/html part."""
    mime_type = payload.get("mimeType", "")
    
    # Check if this part is text/html
    if mime_type == "text/html" and "data" in payload.get("body", {}):
        try:
            raw_data = payload["body"]["data"]
            decoded_bytes = base64.urlsafe_b64decode(raw_data.encode("UTF-8"))
            return decoded_bytes.decode("UTF-8", errors="replace")
        except Exception:
            return ""
            
    # If multipart, recurse into parts
    if "parts" in payload:
        for part in payload["parts"]:
            html_content = extract_html_part(part)
            if html_content:
                return html_content
                
    return ""

def fetch_raw_receipts(query: str, max_results: int = 25) -> list[dict]:
    """Fetches raw emails from Gmail matching the query.
    
    Args:
        query: Gmail search query.
        max_results: Max number of messages to fetch.
        
    Returns:
        List of dicts: {"id": str, "subject": str, "date": str, "html": str}
    """
    service = get_gmail_service()
    
    # Retrieve message list matching query
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])
    
    raw_emails = []
    for msg_info in messages:
        msg_id = msg_info["id"]
        # Fetch the full email payload
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        date_header = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
        
        payload = msg.get("payload", {})
        html_content = extract_html_part(payload)
        
        # If no HTML part was found, fallback to body text/data if present
        if not html_content and "body" in payload and "data" in payload["body"]:
            try:
                raw_data = payload["body"]["data"]
                decoded_bytes = base64.urlsafe_b64decode(raw_data.encode("UTF-8"))
                html_content = decoded_bytes.decode("UTF-8", errors="replace")
            except Exception:
                pass
                
        raw_emails.append({
            "id": msg_id,
            "subject": subject,
            "date": date_header,
            "html": html_content
        })
        
    return raw_emails
