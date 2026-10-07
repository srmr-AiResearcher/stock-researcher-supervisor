"""
Agent and handoff-tool definitions for the research supervisor system.

This follows the supervisor pattern: one supervisor agent dispatches work
to specialist workers, and every worker always reports back to the
supervisor rather than to each other. See README.md for the architecture
diagram and rationale.
"""

from __future__ import annotations

import datetime
import os
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.tools import tool, InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Command

from .tools import web_search, fetch_page, get_stock_summary

load_dotenv()

MODEL_NAME = os.environ.get("RESEARCH_MODEL", "gpt-4o-mini")
model = ChatOpenAI(model=MODEL_NAME, temperature=0)

# Computed once when the CLI process starts. Every agent's prompt below
# includes this explicitly, because an LLM has NO other way to know what
# "today" is — without this, "the latest earnings" silently falls back to
# whatever report the model remembers most confidently from training data,
# which is often an old one, not an actually-recent one.
TODAY = datetime.date.today().strftime("%B %d, %Y")


def create_handoff_tool(*, agent_name: str, description: str):
    """Builds a tool that, when called, redirects execution to a sibling
    node in the OUTER graph (graph=Command.PARENT) instead of returning
    data. This is the handoff mechanism every agent below uses."""
    tool_name = f"transfer_to_{agent_name}"

    @tool(tool_name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": tool_name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,
            update={"messages": state["messages"] + [tool_message]},
            graph=Command.PARENT,
        )

    return handoff_tool


transfer_to_web_researcher = create_handoff_tool(
    agent_name="web_researcher",
    description="Assign web research on the topic to the web researcher agent.",
)
transfer_to_data_analyst = create_handoff_tool(
    agent_name="data_analyst",
    description="Assign stock/financial data lookup to the data analyst agent. "
                 "Only use this if the topic clearly involves a publicly "
                 "traded company.",
)
transfer_to_report_writer = create_handoff_tool(
    agent_name="report_writer",
    description="Assign writing the final report to the report writer "
                 "agent, once enough research (and data, if relevant) has "
                 "been gathered.",
)
transfer_to_supervisor = create_handoff_tool(
    agent_name="supervisor",
    description="Report back to the supervisor once your part of the task is done.",
)

# ---------------------------------------------------------------------------
# Supervisor: no domain tools of its own — its only job is dispatching.
# ---------------------------------------------------------------------------

SUPERVISOR_TOOLS = [transfer_to_web_researcher, transfer_to_data_analyst, transfer_to_report_writer]
supervisor_agent = create_react_agent(
    model=model.bind_tools(SUPERVISOR_TOOLS, parallel_tool_calls=False),
    tools=SUPERVISOR_TOOLS,
    prompt=(
        f"Today's date is {TODAY}. "
        "You are the supervisor coordinating a research team to produce a "
        "short research brief on whatever topic the user gives you.\n\n"
        "Follow these steps in order:\n"
        "1. transfer_to_web_researcher to gather recent news/background on "
        "the topic.\n"
        "2. If the topic clearly involves a publicly traded company (a "
        "stock ticker is mentioned or obviously implied), "
        "transfer_to_data_analyst to pull current stock data. Skip this "
        "step for topics that aren't about a specific public company.\n"
        "3. Once you have enough material in the conversation, "
        "transfer_to_report_writer to produce the final brief.\n"
        "4. Once the report writer reports back with the brief, present it "
        "as your OWN final answer, verbatim. Do not transfer again after that."
    ),
    name="supervisor",
)

# ---------------------------------------------------------------------------
# Web researcher: real DuckDuckGo search + page fetch.
# ---------------------------------------------------------------------------

WEB_RESEARCHER_TOOLS = [web_search, fetch_page, transfer_to_supervisor]
web_researcher_agent = create_react_agent(
    model=model.bind_tools(WEB_RESEARCHER_TOOLS, parallel_tool_calls=False),
    tools=WEB_RESEARCHER_TOOLS,
    prompt=(
        f"Today's date is {TODAY}. Include recency terms (e.g. the current "
        f"month/year) in your web_search queries so results aren't stale.\n\n"
        "You are the web researcher. Use web_search to find recent, "
        "relevant information about the topic the supervisor gave you. "
        "Use fetch_page on the most promising result's URL if you need "
        "more detail than the search snippet gives you — don't fetch more "
        "than one or two pages.\n\n"
        "CRITICAL: base your summary ONLY on what the search results and "
        "fetched pages actually say — never fill in facts, figures, or "
        "quarters from your own training knowledge, even if you feel "
        "confident about them. Your training data is frozen at some past "
        "cutoff and 'the latest X' in your memory is almost certainly "
        "outdated compared to today's date above. If the search results "
        "don't clearly cover something recent, say explicitly 'I could not "
        "confirm recent information on this' rather than substituting an "
        "older report you happen to remember. Cite source URLs for "
        "whatever you do report. Then transfer_to_supervisor with that "
        "summary. Never write the final report yourself."
    ),
    name="web_researcher",
)

# ---------------------------------------------------------------------------
# Data analyst: real Yahoo Finance data via yfinance.
# ---------------------------------------------------------------------------

DATA_ANALYST_TOOLS = [get_stock_summary, transfer_to_supervisor]
data_analyst_agent = create_react_agent(
    model=model.bind_tools(DATA_ANALYST_TOOLS, parallel_tool_calls=False),
    tools=DATA_ANALYST_TOOLS,
    prompt=(
        "You are the data analyst. Figure out the stock ticker symbol for "
        "the company under discussion and call get_stock_summary with it. "
        "Summarize the numbers in your own words, then transfer_to_supervisor "
        "with that summary."
    ),
    name="data_analyst",
)

# ---------------------------------------------------------------------------
# Report writer: no domain tools — synthesizes what's already in the
# conversation into a final markdown brief.
# ---------------------------------------------------------------------------

REPORT_WRITER_TOOLS = [transfer_to_supervisor]
report_writer_agent = create_react_agent(
    model=model.bind_tools(REPORT_WRITER_TOOLS, parallel_tool_calls=False),
    tools=REPORT_WRITER_TOOLS,
    prompt=(
        f"Today's date is {TODAY}. If any figure in the conversation seems "
        "to describe an event clearly older than what 'latest' should mean "
        "relative to today, note that explicitly in the brief rather than "
        "presenting it as current.\n\n"
        "You are the report writer. Using ONLY the research and data "
        "already present in the conversation (never invent facts), write "
        "a concise markdown research brief with these sections: "
        "'## Summary', '## Key findings', and, if stock data is present "
        "in the conversation, '## Market snapshot'. Keep it under 300 "
        "words. Then transfer_to_supervisor, putting the FULL report text "
        "as the content of that message."
    ),
    name="report_writer",
)
