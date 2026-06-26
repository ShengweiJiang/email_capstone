import unittest
from receipt_agent.parser import parse_receipt

class TestReceiptParser(unittest.TestCase):
    def test_parse_date_standard(self):
        raw = {
            "id": "1",
            "subject": "Test Subject",
            "date": "Thu, 25 Jun 2026 21:09:42 -0400",
            "html": "<html><body>No total here</body></html>"
        }
        res = parse_receipt(raw)
        self.assertEqual(res["date"], "2026-06-25")

    def test_parse_date_fallback(self):
        raw = {
            "id": "2",
            "subject": "Test Subject",
            "date": "2026/06/25",
            "html": "<html><body>No total here</body></html>"
        }
        res = parse_receipt(raw)
        self.assertEqual(res["date"], "2026-06-25")

    def test_parse_total_with_keyword(self):
        raw = {
            "id": "3",
            "subject": "Test Subject",
            "date": "Thu, 25 Jun 2026 21:09:42 -0400",
            "html": "<html><body>Some text\nOrder Total: $45.67\nOther amount $100.00</body></html>"
        }
        res = parse_receipt(raw)
        self.assertEqual(res["total"], 45.67)

    def test_parse_total_fallback_to_largest(self):
        raw = {
            "id": "4",
            "subject": "Test Subject",
            "date": "Thu, 25 Jun 2026 21:09:42 -0400",
            "html": "<html><body>Items for $12.50 and $99.99 inside here.</body></html>"
        }
        res = parse_receipt(raw)
        self.assertEqual(res["total"], 99.99)

    def test_parse_merchant_apple(self):
        raw = {
            "id": "5",
            "subject": "Your Apple Invoice",
            "date": "Thu, 25 Jun 2026 21:09:42 -0400",
            "html": "<html><body>Total: $9.99</body></html>"
        }
        res = parse_receipt(raw)
        self.assertEqual(res["merchant"], "Apple")

    def test_parse_merchant_unknown(self):
        raw = {
            "id": "6",
            "subject": "Your Spotify Invoice",
            "date": "Thu, 25 Jun 2026 21:09:42 -0400",
            "html": "<html><body>Total: $10.99</body></html>"
        }
        res = parse_receipt(raw)
        self.assertEqual(res["merchant"], "Unknown")

if __name__ == "__main__":
    unittest.main()
