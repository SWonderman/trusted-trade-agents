# The audit trail is read back from quotes and orders: the same products, fake Valio
# Aimo API and agents
from saint_elmo_backend.quotes.tests.conftest import (  # noqa: F401
    authenticate,
    client,
    fake_api,
    organization,
    quoted_products,
)
