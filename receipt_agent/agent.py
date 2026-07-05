import sys
import os
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .tools import store_receipts


def _child_python() -> str:
    """Interpreter for the MCP server subprocess.

    The hosting process (Streamlit / adk web) may itself be running on the
    SYSTEM Python while only seeing venv packages via the PYTHONPATH env var
    (observed in this project's setup). Using sys.executable would then launch
    a child on the system interpreter — and since the MCP SDK's env=None
    applies a minimal whitelist that silently drops PYTHONPATH, that child
    can't resolve venv-only packages (seen as 'No module named google.auth').
    Preferring the venv's own python avoids all of this: it natively resolves
    its site-packages with no PYTHONPATH needed."""
    venv_dir = os.environ.get("VIRTUAL_ENV")
    if venv_dir:
        candidate = os.path.join(
            venv_dir,
            "Scripts" if sys.platform == "win32" else "bin",
            "python.exe" if sys.platform == "win32" else "python",
        )
        if os.path.exists(candidate):
            return candidate
    return sys.executable


# --- Custom MCP server (gmail_mcp_server.py) ---
# Launched as a module (`python -m receipt_agent.gmail_mcp_server`) rather than
# as a bare script, since gmail_mcp_server.py imports from the receipt_agent
# package (`from receipt_agent.gmail_client import fetch_raw_receipts`).
# Running it as a bare script would raise ModuleNotFoundError.
gmail_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=_child_python(),
            args=["-m", "receipt_agent.gmail_mcp_server"],
            env=dict(os.environ),  # full explicit copy — env=None would apply MCP's minimal whitelist and drop PYTHONPATH
        ),
        timeout=30,
    )
)


collector_agent = LlmAgent(
    name="collector_agent",
    model=LiteLlm(model="anthropic/claude-haiku-4-5"),
    instruction=(
        "Extract the Gmail query parameter from the user message. Call the "
        "get_spending_receipts MCP tool with that query — it fetches AND parses "
        "matching receipt emails in one step. Then call store_receipts, passing "
        "through the exact 'receipts' list that get_spending_receipts returned, "
        "so it gets saved into state for the analyst_agent to read. Do not "
        "modify, summarize, or fabricate the receipt data — pass it through as-is."
    ),
    tools=[gmail_toolset, store_receipts]
)

analyst_agent = LlmAgent(
    name="analyst_agent",
    model=LiteLlm(model="anthropic/claude-haiku-4-5"),
    instruction=(
        "spending analyst; read parsed receipts from state key 'receipts' using "
    "ADK templating {receipts?}. Your ENTIRE reply must be at most 2 sentences: "
    "one sentence naming the dominant spending pattern (which merchant/category "
    "dominates and roughly what share), and optionally one sentence flagging "
    "anything unusual. No headers, no bullet points, no totals — exact numbers "
    "are displayed separately. If receipts is empty, say so in one sentence. "
    "Never fabricate amounts."
    )
)

root_agent = SequentialAgent(
    name="receipt_pipeline",
    sub_agents=[collector_agent, analyst_agent]
)