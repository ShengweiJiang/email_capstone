from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from .tools import fetch_receipts

gmail_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "receipt_agent.gmail_mcp_server"]
        ),
        timeout=30,
    )
)


collector_agent = LlmAgent(
    name="collector_agent",
    model=LiteLlm(model="anthropic/claude-haiku-4-5"),
    instruction=(
        "first use the Gmail MCP tool to search for receipt emails, "
        "then call fetch_receipts with the retrieved content to parse and store them"
    ),
    tools=[gmail_toolset, fetch_receipts]
)

analyst_agent = LlmAgent(
    name="analyst_agent",
    model=LiteLlm(model="anthropic/claude-haiku-4-5"),
    instruction=(
        "spending analyst; read parsed receipts from state key 'receipts' using "
        "ADK templating {receipts?}; output total spent, breakdown by merchant "
        "and by month, and the largest single purchase; if empty say so; "
        "never fabricate amounts."
    )
)

root_agent = SequentialAgent(
    name="receipt_pipeline",
    sub_agents=[collector_agent, analyst_agent]
)