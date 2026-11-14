from enum import StrEnum


class QuoteStatus(StrEnum):
    QUOTED = "QUOTED"
    # Past `expiresAt`: no order can be placed from it any more
    EXPIRED = "EXPIRED"
