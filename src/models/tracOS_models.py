from datetime import datetime
from pydantic import BaseModel, ConfigDict
from bson import ObjectId
from typing import Literal

class TracOSWorkorder(BaseModel):
    _id: ObjectId
    status: Literal["pending", "in_progress", "completed", "on_hold", "cancelled"]
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
    )
