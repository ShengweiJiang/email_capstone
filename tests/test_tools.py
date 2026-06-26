import unittest
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from receipt_agent.tools import fetch_receipts

class TestReceiptTools(unittest.TestCase):
    def test_fetch_receipts_success(self):
        # Mock retrieved emails
        emails = [
            {
                "id": "123",
                "subject": "Your Apple Order",
                "date": "Fri, 26 Jun 2026 12:00:00 +0000",
                "html": "<html><body>Total: $15.99</body></html>"
            }
        ]
        
        # Mock ToolContext
        tool_context = MagicMock(spec=ToolContext)
        tool_context.state = {}
        
        res = fetch_receipts(emails=emails, tool_context=tool_context)
        
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["count"], 1)
        self.assertEqual(len(res["receipts"]), 1)
        self.assertEqual(res["receipts"][0]["total"], 15.99)
        self.assertEqual(res["receipts"][0]["merchant"], "Apple")
        self.assertEqual(tool_context.state["receipts"], res["receipts"])

    def test_fetch_receipts_failure(self):
        # Passing invalid type for emails to check error handling
        tool_context = MagicMock(spec=ToolContext)
        tool_context.state = {}
        
        res = fetch_receipts(emails="not a list", tool_context=tool_context)
        self.assertEqual(res["status"], "error")
        self.assertIn("Expected emails to be a list", res["error_message"])

if __name__ == "__main__":
    unittest.main()

