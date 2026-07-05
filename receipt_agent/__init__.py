# Intentionally empty.
#
# Do NOT add `from . import agent` here.
#
# gmail_mcp_server.py is launched as its own subprocess via
# `python -m receipt_agent.gmail_mcp_server`. Because it lives inside this
# package, Python always runs this __init__.py first before loading it.
# If this file eagerly imported agent.py, every MCP server subprocess launch
# would re-trigger agent.py's module-level `gmail_toolset = MCPToolset(...)`,
# which is itself configured to launch *another* `gmail_mcp_server` subprocess
# — creating unbounded recursive subprocess spawning (and immediate crashes,
# surfacing as "Connection closed" before the MCP handshake could complete).
#
# ADK's `adk web` / `adk run` CLI discovers root_agent by importing
# `receipt_agent.agent` directly — it does not require this __init__.py to
# pre-import it.