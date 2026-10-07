# Stock-researcher-supervisor

A multi-agent research assistant built on LangGraph, using a **supervisor**
architecture: one dispatcher agent coordinates three specialist workers to
turn a one-line topic into a short, sourced research brief.

```
$ python -m src.cli --quiet --save "Tesla Q3 2025 earnings and stock outlook"

## Summary
Tesla reported Q3 2025 deliveries ahead of analyst expectations, driven by
strong Model Y refresh demand in North America...

## Key findings
- Deliveries up 8% YoY, beating consensus estimates (source: reuters.com)
- Margins under pressure from price cuts earlier in the year
- Full self-driving revenue recognition cited as a tailwind

## Market snapshot
- Last price: $248.30 | 52-week range: $138.80 - $305.80
- Market cap: ~$790B
- Recent headline: "Tesla beats delivery estimates for Q3"

Saved report to reports/20260110_143022_Tesla_Q3_2025_earnings_and_s.md
```

This is a companion project to a LangGraph learning course — see
[How it works](#how-it-works) below for how the pieces fit together, or
jump straight to [Quickstart](#quickstart) to run it.

## Why a supervisor, not a swarm

LangGraph supports two common multi-agent topologies:

- **Swarm**: workers hand off directly to each other. Good when *which*
  specialist should act next is obvious from the topic alone (a support
  ticket is either billing or technical, say).
- **Supervisor**: one dispatcher agent decides what happens next, every
  turn, and workers always report back to it rather than to each other.

This project uses a supervisor because the task has a genuine **sequence**
a human editor would also follow: gather background first, pull numbers
*only if relevant*, then write — and that ordering benefits from living in
one place (the supervisor's prompt) rather than being distributed across
three workers each guessing what comes next.

## Architecture

```
                 ┌──────────────┐
      START ───▶ │  supervisor   │ ───▶ END (presents the final brief)
                 └──────┬────────┘
             dispatches │   ▲ reports back
          ┌─────────────┼────────────────┐
          ▼             ▼                ▼
  ┌───────────────┐ ┌──────────────┐ ┌────────────────┐
  │ web_researcher │ │ data_analyst │ │ report_writer   │
  │ web_search     │ │ get_stock_   │ │ (no tools — just│
  │ fetch_page     │ │ summary      │ │  synthesizes)    │
  └───────────────┘ └──────────────┘ └────────────────┘
```

- **`supervisor`** — no domain tools. Decides, each turn, which worker to
  dispatch next, following the sequence in its own prompt.
- **`web_researcher`** — real DuckDuckGo search (via the `ddgs` package)
  plus a page-fetch tool for when a snippet isn't enough detail.
- **`data_analyst`** — real stock data via `yfinance` (price, 52-week
  range, market cap, recent headlines). Only dispatched when the topic
  involves a public company.
- **`report_writer`** — no domain tools; synthesizes whatever is already
  in the conversation into a short markdown brief.

Every worker's only way back is a `transfer_to_supervisor` handoff tool —
structurally, a worker cannot end the run or talk to another worker
directly. Only the supervisor's default edge points to `END`.

## How it works

Each agent is a `create_react_agent` (one prompt, one small toolbox). The
outer graph (`src/graph.py`) treats each agent as a single node. A
"handoff" is a tool that returns a `Command(goto=<agent>, graph=Command.PARENT)`
instead of data — this is what lets an agent redirect the whole
conversation to a specific sibling node instead of just answering with a
result. See `src/agents.py` for the `create_handoff_tool` factory every
agent's transfer tools are built from.

If any of this is unfamiliar, it's covered step by step, from first
principles, in the companion learning course this project builds on.

## Quickstart

```bash
git clone <this-repo-url>
cd ai-research-supervisor
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your real OPENAI_API_KEY into .env
```

Run it:

```bash
# Full trace printed (every agent's turns and tool calls)
python -m src.cli "Nvidia's latest earnings and what analysts are saying"

# Just the final report
python -m src.cli --quiet "What's happening with the Fed's interest rate decisions"

# Save the final report to reports/<timestamp>_<topic>.md
python -m src.cli --save "Is Palantir stock overvalued right now"
```

Run the tests (no network or API key needed — see [Testing](#testing)):

```bash
pytest
```

## Configuration

All configuration is via environment variables in `.env`:

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | yes | — | Used by every agent |
| `RESEARCH_MODEL` | no | `gpt-4o-mini` | Model name for all four agents |

## Testing

```
tests/test_tools.py
```

covers the pure-logic formatting functions (`format_search_results`,
`summarize_stock_data`) with no network calls and no API key required —
these are the parts of `src/tools.py` that are safe and fast to unit test.
The actual network-calling tools (`web_search`, `fetch_page`,
`get_stock_summary`) are thin wrappers around those functions plus a
third-party API call, and are exercised by actually running the CLI rather
than by unit tests, since mocking three different external services would
test the mocks more than the code.

## Project layout

```
ai-research-supervisor/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── tools.py      # web_search, fetch_page, get_stock_summary (+ pure helpers)
│   ├── agents.py      # supervisor + 3 workers, handoff tool factory
│   ├── graph.py        # wires the 4 agents into one supervisor graph
│   └── cli.py          # command-line entrypoint
├── tests/
│   └── test_tools.py   # unit tests for the pure helper functions
└── examples/
    └── sample_run.md    # an example full trace, for reference
```

## Known limitations

- `yfinance` scrapes Yahoo Finance's unofficial endpoints, which
  occasionally change shape or rate-limit; `get_stock_summary` degrades
  gracefully (returns an "unavailable" field rather than crashing) but may
  be temporarily unreliable.
- `ddgs` (DuckDuckGo search) can rate-limit aggressive use; this project
  calls it at most once or twice per run, which is normally fine for
  interactive use.
- The supervisor's sequencing is enforced by its prompt, not by code —
  like any LLM-driven decision, it's reliable in practice but not
  mathematically guaranteed. See the "Known gotchas" lessons in the
  companion course (parallel tool calls + handoffs, prompt vs. hard
  constraints) if you extend this project and hit similar issues.

## Extending this project

- Add a **fourth worker** (e.g. `sentiment_analyst` using a news-sentiment
  API) — copy the `data_analyst` pattern in `src/agents.py` and add one
  line to `src/graph.py`.
- Swap `report_writer`'s output format for HTML or a Slack-formatted
  message instead of markdown.
- Add a `checkpointer` (`langgraph.checkpoint.memory.MemorySaver`) to let a
  research session resume later instead of running start-to-finish each time.
