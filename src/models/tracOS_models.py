from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(
        extra="forbid",             # additionalProperties: false
        validate_assignment=True,   # re-validate on attribute change
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
