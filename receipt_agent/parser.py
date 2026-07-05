import re
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

def parse_receipt(raw: dict) -> dict:
    """Parses a raw email dictionary to extract metadata and receipt details like total and merchant.
    
    Args:
        raw: Dict containing:
            - "id": unique message ID
            - "subject": email subject string
            - "date": raw email Date header string
            - "html": HTML content of the email
            
    Returns:
        A dictionary with extracted receipt information.
    """
    html_content = raw.get("html", "")
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator="\n")
    
    # 1. Parse date to ISO format yyyy-mm-dd
    parsed_date = None
    raw_date = raw.get("date", "")
    if raw_date:
        try:
            dt = parsedate_to_datetime(raw_date)
            parsed_date = dt.strftime("%Y-%m-%d")
        except Exception:
            # Best effort fallback or regex extraction
            match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw_date)
            if match:
                parsed_date = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    
    # 2. Extract total amount
    total = None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Let's search for dollar amount pattern: $ followed by digits and optionally cents
    # or just numbers with decimals.
    amount_pattern = r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+\.[0-9]{2})"
    
    # Target lines matching /total|order total|grand total/i
    target_keywords = re.compile(r"total|order total|grand total", re.IGNORECASE)
    
    found_totals = []
    for line in lines:
        if target_keywords.search(line):
            matches = re.findall(amount_pattern, line)
            for m in matches:
                try:
                    val = float(m.replace(",", ""))
                    found_totals.append(val)
                except ValueError:
                    continue

    if found_totals:
        total = found_totals[0]
    else:
        # Fall back to the largest dollar amount found anywhere in the text
        all_matches = re.findall(amount_pattern, text)
        all_amounts = []
        for m in all_matches:
            try:
                val = float(m.replace(",", ""))
                all_amounts.append(val)
            except ValueError:
                continue
        if all_amounts:
            total = max(all_amounts)

    # 3. Determine merchant from From header domain (most reliable)
    # Falls back to scanning the subject for common brand keywords.
    subject = raw.get("subject", "")
    merchant = None
    from_header = raw.get("from_header", "")
    if from_header:
        # Extract the email address from "Display Name <addr@domain.com>" or bare "addr@domain.com"
        addr_match = re.search(r"[\w.+-]+@([\w.-]+)", from_header)
        if addr_match:
            domain = addr_match.group(1).lower()
            # Map well-known sending domains to friendly brand names
            _DOMAIN_MAP = {
                "apple.com": "Apple",
                "email.apple.com": "Apple",
                "amazon.com": "Amazon",
                "amazon.co.uk": "Amazon",
                "google.com": "Google",
                "netflix.com": "Netflix",
                "uber.com": "Uber",
                "ubereats.com": "Uber Eats",
                "doordash.com": "DoorDash",
                "paypal.com": "PayPal",
                "stripe.com": "Stripe",
                "shopify.com": "Shopify",
            }
            # Exact match first, then suffix match
            merchant = _DOMAIN_MAP.get(domain)
            if not merchant:
                for key, brand in _DOMAIN_MAP.items():
                    if domain.endswith("." + key) or domain == key:
                        merchant = brand
                        break
            if not merchant:
                # Capitalize the second-level domain as the merchant name
                parts = domain.rstrip(".").split(".")
                merchant = parts[-2].capitalize() if len(parts) >= 2 else parts[0].capitalize()

    if not merchant:
        # Fallback: scan subject for known brand keywords
        subject_lower = subject.lower()
        if "apple" in subject_lower:
            merchant = "Apple"
        elif "amazon" in subject_lower:
            merchant = "Amazon"
        elif "google" in subject_lower:
            merchant = "Google"
        else:
            merchant = "Unknown"

    return {
        "id": raw.get("id"),
        "date": parsed_date,
        "subject": subject,
        "total": total,
        "currency": "USD",  # default context currency
        "merchant": merchant
    }
