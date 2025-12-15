import os
from datetime import datetime, timezone
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
        self.client = AsyncIOMotorClient(MONGO_URI, tz_aware=True, tzinfo=timezone.utc)
        self.db = self.client[MONGO_DATABASE]
        self.collection = self.db[MONGO_COLLECTION]

    # TODO add tests
    async def capture_workorder(self, orderNo: int) -> TracOSWorkorder | None:
        logger.info(
            f"Querying {MONGO_COLLECTION} collection for workorder number {orderNo}"
        )
        doc = await self.collection.find_one({"number": orderNo})

        if doc is None:
            logger.info(
                f"Workorder {orderNo} not found in {MONGO_COLLECTION} collection"
            )
            return None

        try:
            workorder = TracOSWorkorder.model_validate(doc)
        except ValidationError as e:
            logger.error(
                "Retrieved MongoDB document not compliant with TracOSWorkorder"
            )
            logger.error(f"Errors:{e.errors()}")
            return None

        return workorder

    async def insert_workorder(self, order: TracOSWorkorder) -> None:
        synced_order = order.model_copy(
            update={"isSynced": True, "syncedAt": datetime.now(timezone.utc)}
        )

        document = synced_order.model_dump(by_alias=True, exclude_none=True)
        try:
            result = await self.collection.insert_one(document)
            logger.info(
                f"Added new document to MongoDB instance: _id: {result.inserted_id}"
            )
        except Exception as e:
            logger.warning(f"Exception: {e}")

    async def update_workorder(self, order: TracOSWorkorder) -> None:
        synced_order = order.model_copy(
            update={"isSynced": True, "syncedAt": datetime.now(timezone.utc)}
        )

        document = synced_order.model_dump(
            by_alias=True, exclude_none=True, exclude={"_id"}
        )

        try:
            result = await self.collection.update_one(
                {"number": order.number}, {"$set": document}
            )
            if result.modified_count == 1:
                logger.info(f"Updated {order.number} workorder in DB")

        except Exception as e:
            logger.warning(f"Exception: {e}")

    # TODO tests and exceptions
    async def capture_unsynced_workorders(self) -> list[TracOSWorkorder]:
        unsynced_orders = []
        logger.info("Querying TracOS database for all unsynced workorders")
        cursor = self.collection.find({"isSynced": False})

        async for doc in cursor:
            try:
                workorder = TracOSWorkorder.model_validate(doc)
                logger.info(f"Unsynced workorder #{doc['number']} captured")
                unsynced_orders.append(workorder)
            except ValidationError as e:
                logger.warning(f"Invalid workorder document skipped: {e}")

        return unsynced_orders

    async def mark_workorder_as_synced(self, order: TracOSWorkorder) -> None:
        try:
            logger.info(f"Marking order #{order.number} as synced in MongoDB")
            await self.collection.update_one(
                {"_id": order.id},
                {"$set": {"isSynced": True, "syncedAt": datetime.now(timezone.utc)}},
            )
            logger.info(
                f"Sucessfully marked order #{order.number} as synced in MongoDB"
            )
        except Exception as e:
            logger.warning(f"Exception: {e}")
