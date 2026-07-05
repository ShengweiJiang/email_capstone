"""Same probe as repro.py, but run inside a threading.Thread — exactly like
app.py's run_step1_thread does — WITHOUT Streamlit in the picture at all.

Run from E:\\email_capstone with:
    uv run python thread_repro.py

If this SUCCEEDS: the bug is Streamlit-process-specific (e.g. Tornado's own
event loop / atexit hooks interfering), not threading+asyncio+subprocess
in general.

If this FAILS the same way: the bug is the combination of
threading.Thread + asyncio.run() + Windows subprocess spawning itself,
regardless of Streamlit — meaning the real fix is to stop using a raw
background thread for this operation.
"""
import asyncio
import sys
import os
import threading
import time

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

result = {}


def run_step1_thread(result_holder):
    async def probe_mcp():
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "receipt_agent.gmail_mcp_server"],
            env=None,
        )
        print("[thread_repro] launching subprocess...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("[thread_repro] stdio pipes opened...")
            async with ClientSession(read_stream, write_stream) as session:
                print("[thread_repro] initializing...")
                await session.initialize()
                tools_result = await session.list_tools()
                result_holder["status"] = "success"
                result_holder["tools"] = [t.name for t in tools_result.tools]

    try:
        asyncio.run(probe_mcp())
    except Exception as e:
        import traceback
        result_holder["status"] = "error"
        result_holder["error"] = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"


if __name__ == "__main__":
    print(f"[thread_repro] main thread = {threading.current_thread().name}")
    t = threading.Thread(target=run_step1_thread, args=(result,), daemon=True)
    t.start()
    t.join(timeout=30)
    print("[thread_repro] RESULT:", result)