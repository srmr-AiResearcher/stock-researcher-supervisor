# Example run

This is an illustrative trace shape for:

```bash
python -m src.cli "Tesla's recent news and stock outlook"
```

The exact wording will differ every run (it's a live model talking to live
search/data APIs), but the **shape** of the trace — which agent runs, in
what order, how many handoffs happen — should look like this:

```
================================ Human Message =================================
Tesla's recent news and stock outlook

================================== Ai Message ==================================
Name: supervisor
Tool Calls:
  transfer_to_web_researcher

================================= Tool Message =================================
Name: transfer_to_web_researcher
Successfully transferred to web_researcher

================================== Ai Message ==================================
Name: web_researcher
Tool Calls:
  web_search
    query: Tesla recent news stock

================================= Tool Message =================================
Name: web_search
1. Tesla beats delivery estimates for Q3
   Shares rose after the company reported...
   source: https://example.com/article-1
...

================================== Ai Message ==================================
Name: web_researcher
Tesla delivered more vehicles than analysts expected this quarter...
Tool Calls:
  transfer_to_supervisor

================================= Tool Message =================================
Name: transfer_to_supervisor
Successfully transferred to supervisor

================================== Ai Message ==================================
Name: supervisor
Tool Calls:
  transfer_to_data_analyst

================================= Tool Message =================================
Name: transfer_to_data_analyst
Successfully transferred to data_analyst

================================== Ai Message ==================================
Name: data_analyst
Tool Calls:
  get_stock_summary
    ticker: TSLA

================================= Tool Message =================================
Name: get_stock_summary
Stock summary for TSLA (Tesla, Inc.)
Last price: $248.30
52-week high: $305.80
52-week low: $138.80
Market cap: 790000000000
Recent headlines:
  - Tesla beats delivery estimates for Q3
  ...

================================== Ai Message ==================================
Name: data_analyst
Tesla is currently trading at $248.30, well within its 52-week range...
Tool Calls:
  transfer_to_supervisor

================================= Tool Message =================================
Name: transfer_to_supervisor
Successfully transferred to supervisor

================================== Ai Message ==================================
Name: supervisor
Tool Calls:
  transfer_to_report_writer

================================= Tool Message =================================
Name: transfer_to_report_writer
Successfully transferred to report_writer

================================== Ai Message ==================================
Name: report_writer
## Summary
Tesla posted stronger-than-expected Q3 deliveries...

## Key findings
- Deliveries beat consensus by roughly 8%
- ...

## Market snapshot
- Last price: $248.30 | 52-week range: $138.80 - $305.80
- Market cap: ~$790B
Tool Calls:
  transfer_to_supervisor

================================= Tool Message =================================
Name: transfer_to_supervisor
Successfully transferred to supervisor

================================== Ai Message ==================================
Name: supervisor
## Summary
Tesla posted stronger-than-expected Q3 deliveries...

## Key findings
- Deliveries beat consensus by roughly 8%
- ...

## Market snapshot
- Last price: $248.30 | 52-week range: $138.80 - $305.80
- Market cap: ~$790B
```

Notice the pattern: every worker's last action is always
`transfer_to_supervisor` — none of them end the run or talk to each other
directly. Only the final `supervisor` turn has no tool call at all, which
is what lets the graph reach `END`.
