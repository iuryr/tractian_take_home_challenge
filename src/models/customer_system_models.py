from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, model_validator, field_validator

class CustomerSystemWorkorder(BaseModel):
    orderNo: int
    isActive: bool
    isCanceled: bool
    isDeleted: bool
    isDone: bool
    isOnHold: bool
    isPending: bool
    isSynced: bool
    summary: str
    creationDate: datetime
    lastUpdateDate: datetime
    deletedDate: datetime | None = None

    # --- UTC enforcement ---
    @field_validator(
        "creationDate",
        "lastUpdateDate",
        "deletedDate",
        mode="after",
    )
    @classmethod
    def ensure_utc(cls, value : datetime | None):
        if value is None:
            return value

        if value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware and in UTC")

        if value.tzinfo != timezone.utc:
            raise ValueError("Datetime must be in UTC")

        return value

    @model_validator(mode="after")
    def validate_exactly_one_status(self):
        status_flags = (
            self.isActive,
            self.isCanceled,
            self.isDeleted,
            self.isDone,
            self.isOnHold,
            self.isPending,
        )

        if sum(status_flags) != 1:
            raise ValueError(
                "Exactly one of isActive, isCanceled, isDeleted, "
                "isDone, isOnHold, or isPending must be True"
            )

        return self

    model_config = ConfigDict(
        extra="forbid",             # additionalProperties: false
        validate_assignment=True,   # re-validate on attribute change
    )
