"""
Imports every model module so their tables register on `Base.metadata`.

Alembic autogenerate only sees tables whose models were imported, so add each new
`models` module here.
"""

from saint_elmo_backend.db.base import Base

from saint_elmo_backend.catalog import models as catalog_models  # noqa: F401

__all__ = ["Base"]
