from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator
from bson import ObjectId
from typing import Literal

TracOSStatus = Literal["pending", "in_progress", "completed", "on_hold", "cancelled"]


class TracOSWorkorder(BaseModel):
    id: ObjectId | None = Field(default=None, alias="_id")
    number: int
    status: TracOSStatus
    title: str
    description: str
    createdAt: datetime
    updatedAt: datetime
    deleted: bool
    deletedAt: datetime | None = None
    isSynced: bool
    syncedAt: datetime | None = None

    @field_validator("updatedAt")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    model_config = ConfigDict(
        extra="forbid",             # additionalProperties: false
        validate_assignment=True,   # re-validate on attribute change
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
