# ReceiptPilot — Gmail Receipt Spending Analyzer

A secure, **local multi-agent AI system** that finds purchase receipts buried in your
Gmail, parses them, and turns them into a clear spending report.

Built with **Google's Agent Development Kit (ADK)** for the **Concierge** track.

> **Privacy first:** Everything runs locally. The agent uses **read-only** Gmail
> access, and no credentials or tokens are ever committed to this repository.

---

## 🎬 Demo

<!-- Replace with your video link before submission -->
▶️ **Demo video:** [Watch here](YOUR_VIDEO_LINK_HERE)

---

## Why it exists

Receipts pile up in your inbox as scattered "Your receipt from ..." emails. Adding
them up by hand is tedious and error-prone. ReceiptPilot automates the whole loop:
it confirms Gmail access, fetches the relevant receipt emails, parses each one for
merchant / date / amount, and synthesizes a spending summary — end to end, with no
manual data entry.

---

## Core concepts demonstrated

This project is built around the three evaluation concepts:

| Concept | How it's demonstrated |
|---|---|
| **Multi-agent orchestration** | A `SequentialAgent` (`receipt_pipeline`) coordinates two sub-agents: `collector_agent` (fetches & stores receipts) and `analyst_agent` (produces the spending insight). |
| **MCP integration** | A custom **Gmail MCP server** (`gmail_mcp_server.py`) exposes the `get_spending_receipts` tool. The agent connects to it through ADK's **`MCPToolset`** — visible in traces as `gen_ai.tool.type = MCPTool`. |
| **Security** | **Read-only** Gmail scope (`gmail.readonly`), OAuth-based authorization, and strict `.gitignore` so `credentials.json`, `token.json`, and `.env` never leave the local machine. |

---

## Architecture

```
                       ┌────────────────────────────┐
                       │   receipt_pipeline          │
                       │   (SequentialAgent)         │
                       └──────────────┬─────────────┘
                                      │
                ┌─────────────────────┴────────────────────┐
                │                                           │
        ┌───────▼─────────┐                        ┌────────▼────────┐
        │ collector_agent │                        │ analyst_agent   │
        └───────┬─────────┘                        └────────┬────────┘
                │                                           │
     ┌──────────┴──────────┐                     reads receipts from
     │                     │                      state and writes a
┌────▼──────────┐   ┌──────▼────────┐             short qualitative
│  MCPToolset   │   │ store_receipts│             spending insight
│  ↓            │   │ (writes to    │
│ Gmail MCP     │   │  ToolContext  │
│ server        │   │  .state)      │
│ get_spending_ │   └───────────────┘
│ receipts      │
└────┬──────────┘
     │  (read-only)
┌────▼──────────┐
│   Gmail API   │
└───────────────┘
```

**Flow:**
1. `collector_agent` calls **`get_spending_receipts`** through the **MCP server**,
   which queries Gmail (read-only) for receipt emails in the chosen date range and
   parses each one (merchant / date / amount) server-side, returning only compact
   structured data to the LLM.
2. Parsed receipts are saved with **`store_receipts`** into `ToolContext.state`,
   making them available to the next agent.
3. `analyst_agent` reads the stored receipts from state and generates a **short
   qualitative insight** (dominant merchant/category, anything unusual).

> **Anti-hallucination by design:** the LLM never computes or reports numbers.
> All figures shown in the UI — total spend, receipt count, average per month,
> the receipt table, and the monthly chart — are **computed deterministically in
> Python (pandas)** by the Streamlit front end from the parsed receipt data. The
> analyst agent is deliberately restricted to a 1–2 sentence qualitative summary,
> so a fabricated dollar amount can never reach the user.

**Models:** Both agents run on **Claude Haiku 4.5 via ADK's `LiteLlm`**
(`anthropic/claude-haiku-4-5`), adopted after hitting Gemini free-tier quota
limits. `LiteLlm` also demonstrates ADK's model-agnostic design — swapping
providers is a one-line change. Only `ANTHROPIC_API_KEY` is required.

---

## Project structure

```
email_capstone/
├── app.py                       # Streamlit front end
├── receipt_agent/               # ADK agent package
│   ├── agent.py                 # receipt_pipeline + collector_agent + analyst_agent
│   ├── gmail_mcp_server.py      # Custom Gmail MCP server (exposes get_spending_receipts)
│   ├── gmail_client.py          # Gmail API wrapper (read-only)
│   ├── parser.py                # Receipt parsing (merchant / date / amount)
│   ├── tools.py                 # store_receipts and other tools
│   └── __init__.py
├── tests/                       # Unit tests
│   ├── test_parser.py
│   └── test_tools.py
├── repro.py                     # Standalone MCP-connection debug script (see Troubleshooting)
├── thread_repro.py              # Same probe inside a background thread
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

### 1. Prerequisites
- Python 3.10+
- A Google Cloud project with the **Gmail API** enabled
- An **Anthropic API key** for the agents

### 2. Clone & install
```bash
git clone https://github.com/ShengweiJiang/email_capstone.git
cd email_capstone

python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Gmail OAuth credentials
1. In the [Google Cloud Console](https://console.cloud.google.com/), enable the
   **Gmail API**.
2. Create an **OAuth 2.0 Client ID** (Desktop app) and download the JSON.
3. Save it as **`credentials.json`** in the project root.
4. On first run you'll be prompted to authorize; this creates **`token.json`**.

> The requested scope is **`https://www.googleapis.com/auth/gmail.readonly`** —
> the agent can read receipt emails but cannot modify, send, or delete anything.

**Optional — skip the interactive OAuth popup:** if you already have a refresh
token, set `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and `GMAIL_REFRESH_TOKEN`
in your `.env`. `gmail_client.py` will build `token.json` from these
automatically, so no browser window is opened (useful for demos and headless runs).

### 4. Environment variables
Copy the template and fill in your key:
```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```
```
# .env  (example — do NOT commit this file)
ANTHROPIC_API_KEY=your_key_here

# Optional: non-interactive Gmail auth (see above)
# GMAIL_CLIENT_ID=...
# GMAIL_CLIENT_SECRET=...
# GMAIL_REFRESH_TOKEN=...
```

> `credentials.json`, `token.json`, `.env`, and `*.log` files are all listed in
> `.gitignore` and must never be committed.

---

## How to run

### Option A — Streamlit front end (recommended for the demo)
```bash
streamlit run app.py
```
Then in the browser:
1. **Step 1 — Verify Gmail Access:** starts the Gmail MCP server as a subprocess
   and confirms the `get_spending_receipts` tool is exposed.
2. **Step 2 — Analyze Spending:** pick a date range / sender filter and run the
   multi-agent pipeline. The MCP server fetches and parses matching receipts;
   you'll get total spend, a receipt table, a monthly chart (all computed
   deterministically in Python), plus a short AI-generated insight.

> If Streamlit reports `ModuleNotFoundError: No module named 'google.adk'`, launch
> it with the virtual-environment interpreter explicitly:
> ```bash
> .\.venv\Scripts\python.exe -m streamlit run app.py
> ```

### Option B — ADK dev UI (to inspect traces)
```bash
adk web
```
Open the dev UI, select the `receipt_agent` app, and send a prompt such as:
```
summarize my spending from gmail, and date is from 2-1-2026 to 2-10-2026
```
The **Traces** tab shows the `receipt_pipeline → collector_agent → analyst_agent`
execution, including the `get_spending_receipts` span with `gen_ai.tool.type = MCPTool`.

### Option C — command line
```bash
adk run receipt_agent
```

---

## Troubleshooting

**"Connection closed" when starting the MCP server on Windows (inside Streamlit).**
Streamlit runs on Tornado, which forces asyncio's event loop policy to
`WindowsSelectorEventLoopPolicy` — and `SelectorEventLoop` cannot spawn
subprocesses on Windows. The identical code works in a plain script but fails
inside Streamlit. Fix (already applied in `app.py`): background threads
explicitly construct a `ProactorEventLoop` instead of relying on
`asyncio.run()`. `repro.py` and `thread_repro.py` are the standalone probes
used to isolate this root cause.

**Child process crashes with `No module named google.auth`.**
The MCP SDK's `env=None` builds a minimal whitelisted environment that silently
drops `PYTHONPATH`, so a child launched on the system interpreter loses access
to venv-only packages. Fix (already applied): the MCP server subprocess is
launched with the **venv's own Python** and a **full explicit environment copy**
(`env=dict(os.environ)`).

**Diagnosing MCP server failures.** After a failed Step 1 verification, open
`mcp_server_stderr.log` in the project root — it captures the child process's
real traceback, which is otherwise invisible in Streamlit.

**"Context window exceeded" during analysis.** The Gmail search returned too
many emails for the model to process at once. Narrow the date range or use a
more specific sender filter. (Oversized email HTML is also capped at 100 KB
per message server-side.)

---

## Security notes

- **Read-only Gmail scope** (`gmail.readonly`) — least-privilege access.
- **OAuth 2.0** authorization; no passwords stored.
- **Secrets excluded from version control:** `credentials.json`, `token.json`, `.env`
  (and any `*.log` files) are gitignored.
- Runs **entirely locally** — receipt data is not sent to any third-party service
  beyond the LLM API used for analysis. Raw email HTML never reaches the LLM;
  only compact parsed fields (date, subject, total, currency, merchant) do.

---

## Tests

Unit tests cover the receipt parser and the tools layer:
```bash
pytest tests/
```

---

## Tech stack

- **Google Agent Development Kit (ADK)** — agent orchestration (`SequentialAgent`)
- **Model Context Protocol (MCP)** — custom Gmail server via `MCPToolset`
- **LiteLlm** — model abstraction (Claude Haiku 4.5 for both agents)
- **Gmail API** — read-only receipt retrieval
- **Streamlit + pandas + Plotly** — local front end with deterministic stats & charts

---

## License

For educational / Kaggle capstone purposes.
