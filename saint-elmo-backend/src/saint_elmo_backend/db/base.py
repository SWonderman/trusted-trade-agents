from typing import Annotated

from sqlalchemy import BigInteger, MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

int_pk = Annotated[int, mapped_column(BigInteger, primary_key=True)]

_POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=_POSTGRES_INDEXES_NAMING_CONVENTION)


class Base(AsyncAttrs, DeclarativeBase):
    metadata = metadata

    id: Mapped[int_pk]
