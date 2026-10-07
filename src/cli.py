"""
Command-line entrypoint.

Usage:
    python -m src.cli "Tesla's recent news and stock outlook"
    python -m src.cli --quiet "AMD Q3 earnings reaction"
    python -m src.cli --save "Is Nvidia overvalued right now"
"""

import argparse
import datetime
import os

# Imported here (not re-exported from src/__init__.py) so that importing
# src.tools for unit tests doesn't cascade through graph.py -> agents.py,
# which constructs a ChatOpenAI client and would otherwise require
# OPENAI_API_KEY just to run `pytest`.
from .graph import app


def run(topic: str, verbose: bool = True) -> str:
    """Runs the graph once and returns the final message's text content."""
    final_message = None
    for step in app.stream(
        {"messages": [{"role": "user", "content": topic}]},
        stream_mode="values",
    ):
        last = step["messages"][-1]
        if verbose:
            last.pretty_print()
        final_message = last
    return final_message.content if final_message else ""


def main():
    parser = argparse.ArgumentParser(description="Multi-agent research supervisor")
    parser.add_argument(
        "topic",
        help="Research topic, e.g. 'Tesla Q3 earnings and stock outlook'",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Only print the final report, not the full trace"
    )
    parser.add_argument(
        "--save", action="store_true", help="Save the final report to reports/<timestamp>.md"
    )
    args = parser.parse_args()

    report = run(args.topic, verbose=not args.quiet)

    if args.quiet:
        print(report)

    if args.save:
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() else "_" for c in args.topic)[:40]
        path = f"reports/{timestamp}_{safe_topic}.md"
        with open(path, "w") as f:
            f.write(report)
        print(f"\nSaved report to {path}")


if __name__ == "__main__":
    main()
