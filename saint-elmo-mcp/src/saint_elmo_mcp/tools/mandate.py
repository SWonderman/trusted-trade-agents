from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response
from saint_elmo_mcp.schemas import Mandate

GET_MY_MANDATE_DESCRIPTION = """\
Read the mandate your buyer organisation set for you: your spend limits,
assortment, product requirements, substitution, delivery and approval rules,
and how much of this period's spend is left. Call this first, before searching
or quoting, so you can pre-check a proposal instead of having it rejected.
You can read the mandate but never change it; only a buyer admin can.

- Pass the mandate's requirements as filters on search_products
  (requiredClaims, requiredLabels, requiredDiets, excludedAllergens with
  allergenStrictness, categoryCodes). The mandate won't let you drop them later.
- An empty allow-list (allowedCategoryCodes, allowedVendors,
  allowedCountriesOfOrigin) means anything is allowed; block-lists still apply.
- An order total above autoApproveUpTo needs a human to approve it. One above
  maxOrderTotal or periodSpend.remaining is rejected.
- Amounts are in EUR excluding VAT. Saint Elmo applies the mandate again to
  every quote and order, recording the `version` it judged against.
- `MANDATE_NOT_FOUND`: you have no mandate. You can't fix this; tell the buyer
  to contact a buyer admin.
- `PERMISSION_DENIED`: your agent key lacks the mandate:read scope.
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=GET_MY_MANDATE_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get my mandate",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_my_mandate(ctx: Context) -> Mandate:
        # No ids: the backend works the mandate out from the agent key
        data = await backend.get("/api/v1/agents/me/mandate", agent_key=agent_key(ctx))
        return parse_response(Mandate, data)
