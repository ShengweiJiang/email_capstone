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

    # 3. Determine merchant
    subject = raw.get("subject", "")
    merchant = "Apple" if "apple" in subject.lower() else "Unknown"
    
    return {
        "id": raw.get("id"),
        "date": parsed_date,
        "subject": subject,
        "total": total,
        "currency": "USD",  # default context currency
        "merchant": merchant
    }
