class InvalidJWTError(Exception):
    """
    The token is malformed, forged, expired, from another issuer, for another audience,
    or misses a required claim.
    """
