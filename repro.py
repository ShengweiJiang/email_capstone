"""Minimal standalone repro: connect to gmail_mcp_server.py the exact same
way app.py does, but with NO Streamlit, NO background thread, NO manual
event loop juggling — just a plain script run directly from a terminal.

Run from E:\\email_capstone with:
    uv run python repro.py

This isolates whether the "Connection closed" error is:
  (a) caused by something in the MCP client/server pairing itself, or
  (b) caused by something specific to running inside Streamlit's
      background-thread environment.
"""
import asyncio
import sys
import os

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession


async def main():
    print(f"[repro] sys.executable = {sys.executable}")
    print(f"[repro] cwd = {os.getcwd()}")
    print(f"[repro] credentials.json exists = {os.path.exists('credentials.json')}")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "receipt_agent.gmail_mcp_server"],
        env=None,
    )

    print("[repro] launching gmail_mcp_server as subprocess...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        print("[repro] stdio pipes opened, starting ClientSession...")
        async with ClientSession(read_stream, write_stream) as session:
            print("[repro] initializing session...")
            await session.initialize()
            print("[repro] initialize() succeeded, listing tools...")
            tools = await session.list_tools()
            print("[repro] SUCCESS. Tools:", [t.name for t in tools.tools])


if __name__ == "__main__":
    asyncio.run(main())
