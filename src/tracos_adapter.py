import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any
from loguru import logger

from pydantic_core import ValidationError

from models.tracOS_models import TracOSWorkorder

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "tractian")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "workorders")

class TracOSAdapter:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DATABASE]
        self.collection = self.db[MONGO_COLLECTION]

    #TODO add tests
    async def capture_workorder(self, orderNo: int) -> TracOSWorkorder | None:
        logger.info(f"Querying {MONGO_COLLECTION} collection for workorder number {orderNo}")
        doc = await self.collection.find_one({"number": orderNo})

        if doc is None:
            logger.info(f"Workorder {orderNo} not found in {MONGO_COLLECTION} collection")
            return None

        try:
            workorder = TracOSWorkorder.model_validate(doc)
        except ValidationError as e:
            logger.error("Retrieved MongoDB document not compliant with TracOSWorkorder")
            logger.error(f"Errors:{e.errors()}")
            return None

        return workorder
