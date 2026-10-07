"""
Wires the four agents into one supervisor-style graph.

Topology: workers ALWAYS report back to the supervisor (default edges
point to "supervisor", not END). Only the supervisor can end the run.
This is deliberately different from a swarm, where workers could hand off
directly to each other — see README.md for why this use case calls for a
supervisor instead.
"""

from langgraph.graph import StateGraph, START, END, MessagesState

from .agents import (
    supervisor_agent,
    web_researcher_agent,
    data_analyst_agent,
    report_writer_agent,
)

builder = StateGraph(MessagesState)
builder.add_node("supervisor", supervisor_agent)
builder.add_node("web_researcher", web_researcher_agent)
builder.add_node("data_analyst", data_analyst_agent)
builder.add_node("report_writer", report_writer_agent)

builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", END)                 # only the supervisor ends the task
builder.add_edge("web_researcher", "supervisor")    # workers ALWAYS report back
builder.add_edge("data_analyst", "supervisor")
builder.add_edge("report_writer", "supervisor")

app = builder.compile()
