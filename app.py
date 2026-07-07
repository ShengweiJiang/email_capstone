import streamlit as st
import time
import os
import threading
import json
import traceback
import logging
import sys
import dotenv
import asyncio
# 1. Load environment variables
dotenv.load_dotenv(override=True)

# 2. Configure loggers to suppress noisy non-spec MCP 'method=log' notification warning.
# @cablate/mcp-gmail emits a non-spec 'method=log' startup message which triggers a
# pydantic validation WARNING from the root logger. It is benign — filter it out.
class _McpLogNotifFilter(logging.Filter):
    def filter(self, record):
        return "Failed to validate notification" not in record.getMessage()

logging.getLogger("mcp").setLevel(logging.ERROR)
logging.getLogger("google_adk").setLevel(logging.ERROR)
logging.getLogger().addFilter(_McpLogNotifFilter())

# 3. Apply Windows Event Loop Policy for background threads (crucial for subprocess spawning on Windows)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 4. Dynamic ADK Framework and project imports
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from receipt_agent.agent import root_agent

# Page layout and SEO configuration
st.set_page_config(
    page_title="Gmail Receipt Spending Analyzer",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Invisible semantic title tag (SEO Best Practice)
st.markdown("""
<div style="display:none;">
    <h1>Gmail Receipt Spending Analyzer</h1>
    <p>Analyze your purchase receipt spending patterns from Gmail using a secure, local, multi-agent AI system.</p>
</div>
""", unsafe_allow_html=True)

# Premium UI styling
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<style>
    /* Main app body background and font */
    .stApp {
        background: radial-gradient(circle at top right, #1e1b4b 0%, #090d16 100%);
        font-family: 'Outfit', sans-serif;
        color: #f1f5f9;
    }
    
    /* Premium Title and Subtitle */
    .main-title {
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: -0.025em;
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2.5rem;
        font-weight: 400;
    }
    
    /* Modern Glassmorphic Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 26px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    .card-header {
        font-size: 1.35rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .card-description {
        color: #cbd5e1;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 20px;
    }
    
    /* Status Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.025em;
    }
    .badge-success {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .badge-warning {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .badge-error {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }
    .badge-info {
        background: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.25);
    }

    /* High-visibility stat cards */
    .stats-row {
        display: flex;
        gap: 16px;
        margin: 8px 0 20px 0;
    }
    .stat-card {
        flex: 1;
        background: linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(139,92,246,0.15) 100%);
        border: 1px solid rgba(139, 92, 246, 0.35);
        border-radius: 14px;
        padding: 18px 20px;
        text-align: center;
    }
    .stat-label {
        color: #a5b4fc;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        margin-bottom: 6px;
    }
    .stat-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 800;
        text-shadow: 0 0 24px rgba(139, 92, 246, 0.45);
    }
    
    /* Premium Styled Streamlit Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(139, 92, 246, 0.35) !important;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    }
    div.stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Output spending report styling */
    .report-container {
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 24px;
        margin-top: 16px;
        line-height: 1.7;
    }
    
    .report-container h1, .report-container h2, .report-container h3 {
        color: #f8fafc;
        margin-top: 18px;
        margin-bottom: 10px;
        font-weight: 700;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 6px;
    }
    
    .report-container p {
        color: #cbd5e1;
        margin-bottom: 14px;
    }
    
    .report-container ul, .report-container ol {
        margin-left: 20px;
        margin-bottom: 14px;
        color: #cbd5e1;
    }
    
    .report-container li {
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Layout Title
st.markdown('<div class="main-title">Gmail Receipt Spending Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Secure local AI agent analyzing purchase receipts from your Gmail</div>', unsafe_allow_html=True)

# Helper to verify OAuth setup exists (custom MCP server uses credentials.json/token.json,
# not env vars — see gmail_client.py's OAuth flow)
def check_oauth_credentials():
    return os.path.exists("credentials.json")

# Initialize state variables
if "step1_state" not in st.session_state:
    st.session_state.step1_state = "idle"
    st.session_state.step1_error = None
    st.session_state.step1_start_time = 0.0
    st.session_state.step1_result = {}

if "step2_state" not in st.session_state:
    st.session_state.step2_state = "idle"
    st.session_state.step2_error = None
    st.session_state.step2_output = None
    st.session_state.step2_start_time = 0.0
    st.session_state.step2_result = {}

# Background thread for Step 1: Verify Gmail Access (Probe MCP Server)
def run_step1_thread(result_holder):
    import asyncio

    async def probe_mcp():
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.session import ClientSession

        if not os.path.exists("credentials.json"):
            raise ValueError(
                "credentials.json not found in the root directory. "
                "Download it from Google Cloud Console (see README)."
            )

        # ROOT CAUSE (from parent+child diagnostics in mcp_server_stderr.log):
        #   1. This Streamlit process runs on the SYSTEM Python, not .venv —
        #      it only sees venv packages via the PYTHONPATH env var.
        #   2. command=sys.executable therefore launched the system Python
        #      for the child too (which has mcp globally but not google-auth).
        #   3. MCP SDK's env=None does NOT mean "inherit everything": it
        #      builds a minimal whitelisted environment (PATH, SYSTEMROOT,
        #      etc.) that silently DROPS PYTHONPATH — so the child lost its
        #      only link to the venv's site-packages.
        # Fix: prefer the venv's own python for the child (it natively sees
        # its site-packages, no PYTHONPATH needed), and pass a full explicit
        # environment copy to bypass the SDK's whitelist behavior.
        venv_dir = os.environ.get("VIRTUAL_ENV")
        if venv_dir:
            candidate = os.path.join(
                venv_dir,
                "Scripts" if sys.platform == "win32" else "bin",
                "python.exe" if sys.platform == "win32" else "python",
            )
            child_python = candidate if os.path.exists(candidate) else sys.executable
        else:
            child_python = sys.executable

        server_params = StdioServerParameters(
            command=child_python,
            args=["-m", "receipt_agent.gmail_mcp_server"],
            env=dict(os.environ),  # full explicit copy — env=None would apply MCP's minimal whitelist and drop PYTHONPATH
        )

        # DIAGNOSTIC: capture the subprocess's stderr into a file. The child
        # process has been dying before completing the MCP handshake, and its
        # own traceback (the actual root cause) is invisible in Streamlit.
        # After a failed verification, open mcp_server_stderr.log in the
        # project root to see the child's real error.
        errlog_file = open("mcp_server_stderr.log", "w", encoding="utf-8")

        # Parent-side diagnostics, written to the same log. Child stderr said
        # "No module named google.auth" yet it DID import mcp — meaning the
        # child sees a site-packages that has mcp but not google-auth, i.e.
        # possibly NOT this project's .venv. Record which interpreter this
        # Streamlit process actually runs on, and what it can resolve.
        import importlib.util
        errlog_file.write(f"[parent] sys.executable = {sys.executable}\n")
        errlog_file.write(f"[parent] sys.prefix     = {sys.prefix}\n")
        errlog_file.write(f"[parent] cwd            = {os.getcwd()}\n")
        errlog_file.write(f"[parent] PYTHONPATH     = {os.environ.get('PYTHONPATH')!r}\n")
        errlog_file.write(f"[parent] VIRTUAL_ENV    = {os.environ.get('VIRTUAL_ENV')!r}\n")
        for _mod in ("google.auth", "mcp", "google.adk"):
            try:
                _spec = importlib.util.find_spec(_mod)
                errlog_file.write(f"[parent] find_spec({_mod!r}) -> {_spec.origin if _spec else None}\n")
            except Exception as _e:
                errlog_file.write(f"[parent] find_spec({_mod!r}) raised {type(_e).__name__}: {_e}\n")
        errlog_file.write("[parent] --- child stderr below ---\n")
        errlog_file.flush()

        async with stdio_client(server_params, errlog=errlog_file) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                result_holder["status"] = "success"
                result_holder["tools"] = [t.name for t in tools_result.tools]

    # Explicitly instantiate a ProactorEventLoop for this thread, rather than
    # relying on asyncio.run() + the module-level WindowsProactorEventLoopPolicy.
    # Root cause (confirmed via standalone repro scripts): Tornado, which
    # Streamlit runs on, forces asyncio's event loop policy to
    # WindowsSelectorEventLoopPolicy on Windows for its own socket handling.
    # SelectorEventLoop does not support subprocess spawning on Windows, so
    # asyncio.run() here would silently create the wrong loop type inside
    # Streamlit's process — even though the identical code works fine in a
    # plain script or a bare threading.Thread outside Streamlit. Explicitly
    # constructing ProactorEventLoop() bypasses the (possibly-overridden)
    # policy entirely and guarantees subprocess support.
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(probe_mcp())
    except Exception as e:
        import traceback
        result_holder["status"] = "error"
        result_holder["error"] = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
    finally:
        loop.close()

# Background thread for Step 2: Analyze receipts (ADK sequential agent pipeline)
def run_step2_thread(result_holder, query, start_date, end_date, sender_raw):
    import asyncio

    async def execute_adk():
        # Ensure credentials.json exists before running the pipeline
        if not os.path.exists("credentials.json"):
            raise ValueError(
                "credentials.json not found in the root directory. "
                "Download it from Google Cloud Console (see README)."
            )

        # Initialize Runner & Session Service.
        # ADK 2.3.0 requires app_name when using the agent= kwarg directly.
        session_service = InMemorySessionService()
        runner = Runner(
            app_name="receipt_pipeline",
            agent=root_agent,
            session_service=session_service,
            auto_create_session=True
        )
        
        date_desc = f"{start_date} to {end_date}"
        sender_desc = sender_raw if sender_raw.strip() else "(any sender)"
        user_message = types.Content(
            parts=[
                types.Part.from_text(
                    text=f"Collect receipts using Gmail query: {query} and then analysis will follow. Note: The analysis covers {date_desc} from {sender_desc}."
                )
            ]
        )
        
        analyst_output = ""
        receipts_from_pipeline = []
        async for event in runner.run_async(
            user_id="user",
            session_id="session",
            new_message=user_message
        ):
            # Capture receipts returned by collect_and_parse_receipts tool response
            if (event.author == "collector_agent"
                    and event.content
                    and event.content.parts):
                for part in event.content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        resp = part.function_response.response
                        if isinstance(resp, dict) and "receipts" in resp:
                            receipts_from_pipeline = resp["receipts"]
            # Capture analyst narrative
            if event.author == "analyst_agent" and not event.partial:
                if event.content and event.content.parts:
                    analyst_output = "".join(part.text for part in event.content.parts if part.text)
                    
        if analyst_output:
            result_holder["status"] = "success"
            result_holder["output"] = analyst_output
            result_holder["receipts"] = receipts_from_pipeline
        else:
            result_holder["status"] = "error"
            result_holder["error"] = "The pipeline completed, but the analyst agent did not produce any spending summary. Please verify you have receipt emails in the queried Gmail history."
            
    # See run_step1_thread for the full explanation: Tornado (Streamlit's
    # server) forces WindowsSelectorEventLoopPolicy on Windows, which breaks
    # subprocess spawning. Explicit ProactorEventLoop instantiation bypasses
    # that policy override entirely.
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(execute_adk())
    except Exception as e:
        err_str = str(e)
        # ContextWindowExceededError means too many emails were fetched.
        # Surface a clear, actionable message rather than a raw traceback.
        if "ContextWindowExceeded" in type(e).__name__ or "prompt is too long" in err_str or "tokens >" in err_str:
            result_holder["status"] = "error"
            result_holder["error"] = (
                "⚠️ Context window exceeded: The Gmail search returned too many emails for the model to process at once.\n\n"
                "**Fix:** Narrow your date range or use a more specific sender filter.\n"
            )
        else:
            import traceback
            result_holder["status"] = "error"
            result_holder["error"] = f"{type(e).__name__}: {err_str}\n\n{traceback.format_exc()}"
    finally:
        loop.close()

# Poll Step 1
if st.session_state.step1_state == "verifying":
    if "status" in st.session_state.step1_result:
        status = st.session_state.step1_result["status"]
        if status == "success":
            st.session_state.step1_state = "success"
            st.session_state.step1_error = None
            st.rerun()
        elif status == "error":
            st.session_state.step1_state = "error"
            st.session_state.step1_error = st.session_state.step1_result.get("error", "Unknown error")
            st.rerun()
    else:
        elapsed = time.time() - st.session_state.step1_start_time
        if elapsed > 90.0:
            st.session_state.step1_state = "timeout"
            st.rerun()
        else:
            time.sleep(0.5)
            st.rerun()

# Poll Step 2
if st.session_state.step2_state == "running":
    if "status" in st.session_state.step2_result:
        status = st.session_state.step2_result["status"]
        if status == "success":
            st.session_state.step2_state = "success"
            st.session_state.step2_output = st.session_state.step2_result.get("output", "")
            st.session_state.step2_error = None
            st.rerun()
        elif status == "error":
            st.session_state.step2_state = "error"
            st.session_state.step2_error = st.session_state.step2_result.get("error", "Unknown error")
            st.rerun()
    else:
        elapsed = time.time() - st.session_state.step2_start_time
        if elapsed > 90.0:
            st.session_state.step2_state = "timeout"
            st.rerun()
        else:
            time.sleep(0.5)
            st.rerun()

# ==================== STEP 1 CARD ====================
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="card-header">🔑 Step 1: Verify Gmail Access</div>', unsafe_allow_html=True)

if not check_oauth_credentials():
    st.error("⚠️ credentials.json is missing! Download it from Google Cloud Console and place it in the project root.")
    st.button("Verify Gmail Access", key="btn_verify_disabled", disabled=True)

else:
    if st.session_state.step1_state == "idle":
        st.markdown('<p class="card-description">Verify that credentials.json is present and that we can successfully probe our custom Gmail MCP server (gmail_mcp_server.py).</p>', unsafe_allow_html=True)
        st.markdown('<div><span class="badge badge-warning">Status: Not Checked</span></div><br>', unsafe_allow_html=True)
        
        if st.button("Verify Gmail Access", key="btn_verify_gmail"):
            st.session_state.step1_state = "verifying"
            st.session_state.step1_start_time = time.time()
            st.session_state.step1_result = {}
            t = threading.Thread(target=run_step1_thread, args=(st.session_state.step1_result,))
            t.daemon = True
            t.start()
            st.rerun()

    elif st.session_state.step1_state == "verifying":
        elapsed = int(time.time() - st.session_state.step1_start_time)
        st.markdown(f'<div class="badge badge-info">Status: Probing MCP Server... ({elapsed}s elapsed)</div><br><br>', unsafe_allow_html=True)
        st.spinner("Probing Gmail MCP Server...")

    elif st.session_state.step1_state == "success":
        st.markdown('<p class="card-description">Gmail credentials verified! The MCP server started successfully and exposed the following tools:</p>', unsafe_allow_html=True)
        tools = st.session_state.step1_result.get("tools", [])
        st.code(", ".join(tools))
        st.markdown('<div><span class="badge badge-success">Status: Verified</span></div><br>', unsafe_allow_html=True)
        
        if st.button("Re-verify Access", key="btn_reverify_gmail"):
            st.session_state.step1_state = "verifying"
            st.session_state.step1_start_time = time.time()
            st.session_state.step1_result = {}
            t = threading.Thread(target=run_step1_thread, args=(st.session_state.step1_result,))
            t.daemon = True
            t.start()
            st.rerun()

    elif st.session_state.step1_state == "error":
        st.markdown('<div class="badge badge-error">Status: Verification Failed</div><br><br>', unsafe_allow_html=True)
        st.error(st.session_state.step1_error)
        
        if st.button("Try Verification Again", key="btn_retry_step1"):
            st.session_state.step1_state = "idle"
            st.session_state.step1_error = None
            st.rerun()

    elif st.session_state.step1_state == "timeout":
        st.markdown('<div class="badge badge-error">Status: Timeout (No response after 90 seconds)</div><br><br>', unsafe_allow_html=True)
        
        if st.button("Try Verification Again", key="btn_retry_step1_timeout"):
            st.session_state.step1_state = "idle"
            st.session_state.step1_error = None
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# ==================== STEP 2 CARD ====================
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="card-header">📊 Step 2: Analyze Spending</div>', unsafe_allow_html=True)

is_verified = (st.session_state.step1_state == "success")

if not is_verified:
    st.markdown('<p class="card-description" style="opacity: 0.6;">Verify Gmail Access in Step 1 to enable spending analysis.</p>', unsafe_allow_html=True)
    st.button("Analyze Spending", key="btn_step2_disabled", disabled=True)

else:
    import datetime
    inputs_disabled = (st.session_state.step2_state == "running")

    # ---- DATE RANGE PICKER ----
    today = datetime.date.today()
    # Initialize date range in session state on first load
    if "step2_date_range" not in st.session_state:
        st.session_state.step2_date_range = (today - datetime.timedelta(days=30), today)

    st.markdown("**Date range**")
    # Quick-select preset buttons
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        if st.button("7 days", key="preset_7d", disabled=inputs_disabled):
            st.session_state.step2_date_range = (today - datetime.timedelta(days=7), today)
            st.rerun()
    with qcol2:
        if st.button("30 days", key="preset_30d", disabled=inputs_disabled):
            st.session_state.step2_date_range = (today - datetime.timedelta(days=30), today)
            st.rerun()
    with qcol3:
        if st.button("90 days", key="preset_90d", disabled=inputs_disabled):
            st.session_state.step2_date_range = (today - datetime.timedelta(days=90), today)
            st.rerun()
    with qcol4:
        if st.button("This year", key="preset_year", disabled=inputs_disabled):
            st.session_state.step2_date_range = (datetime.date(today.year, 1, 1), today)
            st.rerun()

    date_val = st.date_input(
        "Custom range",
        value=st.session_state.step2_date_range,
        max_value=today,
        disabled=inputs_disabled,
        key="step2_date_input"
    )
    # date_input returns a tuple when value is a tuple; guard against single-date selection
    if isinstance(date_val, (list, tuple)) and len(date_val) == 2:
        start_date, end_date = date_val
        st.session_state.step2_date_range = (start_date, end_date)
    else:
        start_date, end_date = st.session_state.step2_date_range

    # Gmail uses after:YYYY/MM/DD before:YYYY/MM/DD; before is exclusive so add 1 day
    after_str = start_date.strftime("%Y/%m/%d")
    before_str = (end_date + datetime.timedelta(days=1)).strftime("%Y/%m/%d")

    # ---- FLEXIBLE SENDER FILTER ----
    sender_raw = st.text_input(
        "Sender filter (optional, comma-separated)",
        value="no_reply@email.apple.com",
        placeholder="e.g. noreply@amazon.com, no_reply@email.apple.com",
        disabled=inputs_disabled
    )

    # Build the Gmail query
    senders = [s.strip() for s in sender_raw.split(",") if s.strip()]
    if senders:
        if len(senders) == 1:
            from_clause = f"from:{senders[0]}"
        else:
            from_clause = "from:(" + " OR ".join(senders) + ")"
        query = f"{from_clause} subject:receipt after:{after_str} before:{before_str}"
    else:
        # No sender → broader subject filter to avoid unrelated mail
        query = f"subject:(receipt OR invoice OR \"order confirmation\") after:{after_str} before:{before_str}"

    st.caption(f"📬 Gmail query: `{query}`")

    if st.session_state.step2_state == "idle":
        st.markdown('<p class="card-description">Trigger the multi-agent AI pipeline. The system will use the MCP server to confirm access, then fetch and parse receipts via the Gmail MCP server and synthesize a spending report.</p>', unsafe_allow_html=True)
        if st.button("Analyze Spending", key="btn_analyze_spending"):
            st.session_state.step2_state = "running"
            st.session_state.step2_start_time = time.time()
            st.session_state.step2_result = {}
            t = threading.Thread(
                target=run_step2_thread,
                args=(st.session_state.step2_result, query, start_date, end_date, sender_raw)
            )
            t.daemon = True
            t.start()
            st.rerun()

    elif st.session_state.step2_state == "running":
        elapsed = int(time.time() - st.session_state.step2_start_time)
        st.markdown(f'<div class="badge badge-info">Status: Running spending pipeline... ({elapsed}s elapsed)</div><br><br>', unsafe_allow_html=True)
        st.spinner("Running sequential agents...")

    elif st.session_state.step2_state == "success":
        st.markdown('<div><span class="badge badge-success">Status: Analysis Complete!</span></div><br>', unsafe_allow_html=True)

        # ---- DETERMINISTIC STATS (Python-computed, not LLM) ----
        receipts = st.session_state.step2_result.get("receipts", [])
        try:
            import pandas as pd
            if receipts:
                df = pd.DataFrame(receipts)
                df["total"] = pd.to_numeric(df.get("total", pd.Series(dtype=float)), errors="coerce")
                df = df.dropna(subset=["total"])

                total_spent = df["total"].sum()
                receipt_count = len(df)

                # Month grouping for avg and chart
                df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
                df["month"] = df["date_parsed"].dt.to_period("M")
                monthly = df.groupby("month")["total"].sum()
                distinct_months = monthly.nunique()
                # Average over months that HAVE data (not divided by 12)
                avg_per_month = total_spent / distinct_months if distinct_months >= 1 else total_spent

                # ---- HIGH-VISIBILITY METRIC CARDS ----
                avg_display = f"${avg_per_month:,.2f}" if distinct_months >= 2 else "—"
                st.markdown(f"""
                <div class="stats-row">
                    <div class="stat-card">
                        <div class="stat-label">💰 Total Spent</div>
                        <div class="stat-value">${total_spent:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">🧾 Receipts</div>
                        <div class="stat-value">{receipt_count}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">📅 Avg / Month</div>
                        <div class="stat-value">{avg_display}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ---- RECEIPT DETAILS TABLE ----
                st.markdown("#### 🧾 Receipt Details")
                detail_df = df[["date", "merchant", "subject", "total"]].copy()
                detail_df = detail_df.sort_values("date", ascending=False)
                detail_df["total"] = detail_df["total"].map(lambda x: f"${x:,.2f}")
                detail_df.columns = ["Date", "Merchant", "Subject", "Amount"]
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

                # ---- MONTHLY CHART: full-year x-axis + average reference line ----
                st.markdown("#### 📈 Monthly Spending")
                valid_dates = df["date_parsed"].dropna()
                if not valid_dates.empty:
                    years = valid_dates.dt.year.unique()
                    if len(years) == 1:
                        year = int(years[0])
                        all_months = pd.period_range(start=f"{year}-01", end=f"{year}-12", freq="M")
                    else:
                        all_months = pd.period_range(
                            start=valid_dates.min().to_period("M"),
                            end=valid_dates.max().to_period("M"),
                            freq="M",
                        )
                    chart_series = monthly.reindex(all_months, fill_value=0.0)

                    try:
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=[str(m) for m in chart_series.index],
                            y=chart_series.values,
                            marker_color="#8b5cf6",
                            name="Monthly spend",
                        ))
                        fig.add_hline(
                            y=avg_per_month,
                            line_dash="dash",
                            line_color="#f472b6",
                            annotation_text=f"avg ${avg_per_month:,.0f}/mo",
                            annotation_position="top right",
                        )
                        fig.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#cbd5e1",
                            margin=dict(l=10, r=10, t=10, b=10),
                            height=320,
                            yaxis_title="Spending ($)",
                            xaxis_title=None,
                            showlegend=False,
                        )
                        fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)")
                        fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
                        st.plotly_chart(fig, use_container_width=True)
                    except ImportError:
                        # Fallback: no plotly installed — basic bar chart, no avg line
                        chart_df = chart_series.reset_index()
                        chart_df.columns = ["Month", "Spending ($)"]
                        chart_df["Month"] = chart_df["Month"].astype(str)
                        st.bar_chart(chart_df.set_index("Month")["Spending ($)"])
                        st.caption(f"Average: ${avg_per_month:,.2f}/mo (install plotly for the reference line)")
        except Exception:
            pass  # Stats are best-effort; don't crash the whole page

        # ---- ANALYST NARRATIVE (insight only) ----
        st.markdown('<div class="report-container">', unsafe_allow_html=True)
        st.markdown("#### 💡 Insight")
        # Escape $ so paired dollar amounts (e.g. "$50.57 to $111.04") aren't
        # interpreted as LaTeX math delimiters by Streamlit's markdown renderer.
        st.markdown(st.session_state.step2_output.replace("$", "\\$"))
        st.markdown('</div><br>', unsafe_allow_html=True)

        if st.button("Run Analysis Again", key="btn_re_analyze"):
            st.session_state.step2_state = "running"
            st.session_state.step2_start_time = time.time()
            st.session_state.step2_result = {}
            t = threading.Thread(
                target=run_step2_thread,
                args=(st.session_state.step2_result, query, start_date, end_date, sender_raw)
            )
            t.daemon = True
            t.start()
            st.rerun()

    elif st.session_state.step2_state == "error":
        st.markdown(f'<div class="badge badge-error">Status: Execution Failed</div>', unsafe_allow_html=True)
        st.error(st.session_state.step2_error)

        if st.button("Try Spending Analysis Again", key="btn_retry_step2"):
            st.session_state.step2_state = "idle"
            st.session_state.step2_error = None
            st.rerun()

    elif st.session_state.step2_state == "timeout":
        st.markdown('<div class="badge badge-error">Status: Timeout (No response after 90 seconds)</div><br><br>', unsafe_allow_html=True)

        if st.button("Try Spending Analysis Again", key="btn_retry_step2_timeout"):
            st.session_state.step2_state = "idle"
            st.session_state.step2_error = None
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)