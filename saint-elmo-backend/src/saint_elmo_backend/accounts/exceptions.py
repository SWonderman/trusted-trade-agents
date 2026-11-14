class AccountError(Exception):
    """Base class for accounts-domain errors."""


class InvalidCredentialsError(AccountError):
    """Unknown email, wrong password, or an inactive user or buyer organization."""
