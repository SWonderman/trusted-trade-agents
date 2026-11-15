"""
Imports every model module so their tables register on `Base.metadata`.

Add each new `models` module here. Two things depend on it:

- Alembic autogenerate only sees tables whose models were imported (`alembic/env.py`).
- At runtime, SQLAlchemy resolves string relationships such as `Agent.mandate` only
  once the target model is registered, so every entrypoint needs all models loaded
  before its first query. Standalone `python -m` entrypoints import this module
  directly, and `db/tests/test_entrypoints.py` checks them. The API and tests don't
  import it: they load every model module indirectly through the routers.
"""

from saint_elmo_backend.accounts import models as accounts_models  # noqa: F401
from saint_elmo_backend.agents import models as agents_models  # noqa: F401
from saint_elmo_backend.audit import models as audit_models  # noqa: F401
from saint_elmo_backend.catalog import models as catalog_models  # noqa: F401
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.mandates import models as mandates_models  # noqa: F401
from saint_elmo_backend.orders import models as orders_models  # noqa: F401
from saint_elmo_backend.quotes import models as quotes_models  # noqa: F401

__all__ = ["Base"]
