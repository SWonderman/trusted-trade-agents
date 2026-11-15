class ValioAimoError(Exception):
    """
    Base for every Valio Aimo API client error.
    """


class ValioAimoNotConfigured(ValioAimoError):
    """
    `VALIO_AIMO_API_URL` or `VALIO_AIMO_API_KEY` is not set. Never answered with fake data.
    """

    def __init__(self) -> None:
        super().__init__(
            "The Valio Aimo API is not configured: set VALIO_AIMO_API_URL and VALIO_AIMO_API_KEY"
        )


class ValioAimoUnavailable(ValioAimoError):
    """
    A call failed: a batch still failed after its retries, or failed with an error that
    is not retried (401 for a wrong key, 422, an unreadable body). No partial results.
    """

    def __init__(self, message: str, *, status_code: int | None, attempts: int) -> None:
        super().__init__(message)

        self.status_code: int | None = status_code
        self.attempts: int = attempts
