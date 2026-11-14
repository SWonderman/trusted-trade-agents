class InvalidCredentialsError(Exception):
    """
    Unknown email, wrong password, an invalid user session, or an inactive user or buyer
    organization.

    Deliberately one error: callers learn nothing about which check failed.
    """
