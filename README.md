# ReceiptPilot — Gmail Receipt Spending Analyzer

A secure, **local multi-agent AI system** that finds purchase receipts buried in your
Gmail, parses them, and turns them into a clear spending report.

Built with **Google's Agent Development Kit (ADK)** for the **Concierge** track.

> **Privacy first:** Everything runs locally. The agent uses **read-only** Gmail
> access, and no credentials or tokens are ever committed to this repository.

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
| **Multi-agent orchestration** | A `SequentialAgent` (`receipt_pipeline`) coordinates two sub-agents: `collector_agent` (fetches & stores receipts) and `analyst_agent` (produces the spending analysis). |
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
     ┌──────────┴──────────┐                     synthesizes spending
     │                     │                      report from stored
┌────▼──────────┐   ┌──────▼────────┐             receipts (via state)
│  MCPToolset   │   │ store_receipts│
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
   which queries Gmail (read-only) for receipt emails in the chosen date range.
2. Parsed receipts are saved with **`store_receipts`** into `ToolContext.state`,
   making them available to the next agent.
3. `analyst_agent` reads the stored receipts from state and generates the final
   spending summary (totals, per-merchant breakdown, monthly trend).

> **A note on models:** `analyst_agent` runs on **Claude (Haiku) via `LiteLlm`**
> after hitting Gemini free-tier quota limits — which also gives the pipeline a
> clean fallback path. Set the appropriate API key below.
> <!-- TODO: confirm the exact model string and key name you actually use in code,
>      e.g. ANTHROPIC_API_KEY for Claude, or GOOGLE_API_KEY if any agent still uses Gemini. -->

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
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

### 1. Prerequisites
- Python 3.10+
- A Google Cloud project with the **Gmail API** enabled
- API key for your analyst model (see "A note on models" above)

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

### 4. Environment variables
Copy the template and fill in your key(s):
```bash
cp .env.example .env
```
```
# .env  (example — do NOT commit this file)
ANTHROPIC_API_KEY=your_key_here
# GOOGLE_API_KEY=your_key_here   # only if an agent still uses Gemini
```

> `credentials.json`, `token.json`, and `.env` are all listed in `.gitignore`
> and must never be committed.

---

## How to run

### Option A — Streamlit front end (recommended for the demo)
```bash
streamlit run app.py
```
Then in the browser:
1. **Step 1 — Verify Gmail Access:** starts the Gmail MCP server and confirms the
   `get_spending_receipts` tool is exposed.
2. **Step 2 — Analyze Spending:** pick a date range / sender filter and run the
   multi-agent pipeline. You'll get total spend, a receipt table, and a monthly chart.

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

## Security notes

- **Read-only Gmail scope** (`gmail.readonly`) — least-privilege access.
- **OAuth 2.0** authorization; no passwords stored.
- **Secrets excluded from version control:** `credentials.json`, `token.json`, `.env`
  (and any `*.log` files) are gitignored.
- Runs **entirely locally** — receipt data is not sent to any third-party service
  beyond the LLM API used for analysis.

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
- **LiteLlm** — model abstraction (Claude Haiku for the analyst agent)
- **Gmail API** — read-only receipt retrieval
- **Streamlit** — local web front end

---

## License

<!-- TODO: add a license if you want one (e.g. MIT), or state "For educational /
     Kaggle capstone purposes." -->
