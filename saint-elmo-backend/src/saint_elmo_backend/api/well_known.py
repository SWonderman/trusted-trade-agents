from fastapi import APIRouter

from saint_elmo_backend.agents import tokens as agent_tokens

router = APIRouter(prefix="/.well-known", tags=["Keys"])


@router.get("/jwks.json")
async def jwks() -> dict[str, list[dict[str, str]]]:
    """
    The public key that verifies Agent tokens (RFC 7517 JWK Set), matched by the token's `kid`.
    """

    return {"keys": [agent_tokens.public_jwk()]}
