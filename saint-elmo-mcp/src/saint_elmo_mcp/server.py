from mcp.server.mcpserver import MCPServer

from saint_elmo_mcp.backend import BackendClient
from saint_elmo_mcp.tools import catalog

INSTRUCTIONS = """\
Saint Elmo lets you, a purchasing agent for a professional kitchen, find and
order products from Valio Aimo within the mandate your organisation set for you.

The full flow (tools are added as the backend grows, so use the ones you have):
1. get_my_mandate: read your limits and requirements before proposing anything.
2. search_products: narrow the catalog to candidates (no live prices or stock).
3. get_offers: live price and availability for a shortlist.
4. create_quote: price a basket and see the policy outcome before committing.
5. place_order: commit a quote. If it is pending approval, a human decides;
   poll get_order_status. You can never approve your own orders.

Rules of thumb:
- Turn relative dates ("by Monday") into ISO dates yourself and check the date
  echoed back in responses.
- State quantities in the buyer's terms (e.g. 1000 L). The backend converts
  them to sales units and shows the conversion; don't do unit arithmetic yourself.
- Unknown is not "free from": a product without allergen or claim data has not
  been shown to be safe.
- A rejection or "needs approval" result is an answer with reason codes, not an
  error. Read the reason codes and revise your proposal, or explain it to the buyer.
"""


def build_server(backend: BackendClient) -> MCPServer:
    mcp = MCPServer(
        name="saint-elmo",
        title="Saint Elmo: Valio Aimo purchasing gateway",
        instructions=INSTRUCTIONS,
        version="0.1.0",
    )
    catalog.register(mcp, backend)
    return mcp
