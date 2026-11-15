"""Smoke test: the milk example through the running MCP server and backend.

Not part of pytest: it needs Postgres, the backend (with OFFERS_IGNORE_CLOSING_TIME=true
against the live Valio Aimo mock), the MCP server and a dairy-restock agent token.

    SAINT_ELMO_AGENT_KEY=<token> uv run python scripts/smoke_quotes.py [mcp-url]

Calls get_offers, create_quote and get_quote for 1000 L of 463038 and checks each
answer. Creates one real quote, which binds nothing.
"""

import asyncio
import os
import sys
from datetime import date, timedelta

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

MILK = {"productCode": "463038", "quantity": 1000, "unit": "L"}


def next_weekday(days_ahead: int) -> date:
    day = date.today() + timedelta(days=days_ahead)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def check(condition: bool, what: str) -> None:
    print(f"  {'ok ' if condition else 'FAIL'} {what}")
    if not condition:
        raise SystemExit(1)


async def call(client: Client, tool: str, args: dict) -> dict:
    result = await client.call_tool(tool, args)
    text = "\n".join(b.text for b in result.content if b.type == "text")
    check(not result.is_error, f"{tool} succeeded" + (f": {text}" if result.is_error else ""))
    assert result.structured_content is not None
    return result.structured_content


async def main(url: str, key: str) -> None:
    deliver_by = next_weekday(3).isoformat()
    async with (
        httpx2.AsyncClient(headers={"X-Agent-Key": key}, timeout=60) as http,
        Client(streamable_http_client(url, http_client=http)) as client,
    ):
        print(f"get_offers 1000 L of 463038 by {deliver_by}")
        offers = await call(client, "get_offers", {"deliverBy": deliver_by, "items": [MILK]})
        offer = offers["items"][0]
        check(offer["quantity"]["salesUnits"] == 50, f"50 sales units ({offer['salesUnit']})")
        print(f"  reasonCodes {offer['reasonCodes']}")

        print("create_quote")
        quote = await call(
            client,
            "create_quote",
            {
                "deliverBy": deliver_by,
                "lines": [MILK],
                "buyerRequest": "1,000 litres of lactose-free milk",
                "rationale": "Smoke test: Valio Eila 10 l is lactose free.",
            },
        )
        line = quote["lines"][0]
        check(line["quantity"]["salesUnits"] == 50, "line is 50 KI")
        check(quote["totals"]["gross"] > 0, f"total {quote['totals']}")
        check(quote["status"] == "QUOTED", "status QUOTED")
        check(quote["deliverBy"] == deliver_by, "deliverBy echoed")
        policy = quote["policy"]
        print(f"  policy {policy['outcome']} (mandate v{policy['mandateVersion']})")
        for reason in policy["reasons"]:
            print(f"    {reason['severity']:<11} {reason['code']}: {reason['message']}")

        print(f"get_quote {quote['quoteId']}")
        again = await call(client, "get_quote", {"quoteId": quote["quoteId"]})
        check(again == quote, "same quote as created")

    print("smoke test passed")


if __name__ == "__main__":
    key = os.environ.get("SAINT_ELMO_AGENT_KEY")
    if not key:
        raise SystemExit("Set SAINT_ELMO_AGENT_KEY to a dairy-restock agent token.")
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001/mcp", key))
