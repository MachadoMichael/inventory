import enum


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"


class ReleaseReason(str, enum.Enum):
    COMPENSATION = "COMPENSATION"
    EXPIRATION = "EXPIRATION"
    ORDER_CANCELLED = "ORDER_CANCELLED"


class MovementType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"
    DISPATCH = "DISPATCH"
    ADJUSTMENT = "ADJUSTMENT"
