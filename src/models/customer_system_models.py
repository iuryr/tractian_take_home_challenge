from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator

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
