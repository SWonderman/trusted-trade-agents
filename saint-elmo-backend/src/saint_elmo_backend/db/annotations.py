import uuid

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import DateTime, Numeric, Uuid, func, text
from sqlalchemy.orm import mapped_column

money = Annotated[Decimal, mapped_column(Numeric(19, 4))]

created_at = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
]

updated_at = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
]

deleted_at = Annotated[
    datetime | None,
    mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    ),
]

public_id = Annotated[
    uuid.UUID,
    mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        server_default=text("gen_random_uuid()"),
    ),
]
