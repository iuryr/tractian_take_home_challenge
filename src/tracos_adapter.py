import os
import sys
from functools import wraps
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from loguru import logger

from pydantic_core import ValidationError

from models.tracOS_models import TracOSWorkorder

#MongoDB constants
CONNECTTIMEOUTMS=5000
SOCKETTIMEOUTMS=5000
TIMEOUTMS=5000

def retry_on_mongodb_error(func):
    """Decorator for MongoDB error handling with one extra retry"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PyMongoError as e:
            logger.error(f"MongoDB error in {func.__name__}: {e}")
            logger.info(f"Retrying {func.__name__}...")
            try:
                return await func(*args, **kwargs)
            except PyMongoError as retry_error:
                logger.error(f"Retry failed: {retry_error}")
                logger.critical("Shutting down due to MongoDB errors")
                sys.exit(1)

    return wrapper


class TracOSAdapter:
    def __init__(self, uri:str, db:str, collection:str):
        self.client = AsyncIOMotorClient(
            uri,
            tz_aware=True,
            tzinfo=timezone.utc,
            connectTimeoutMS=CONNECTTIMEOUTMS,
            socketTimeoutMS=SOCKETTIMEOUTMS,
            timeoutMS=TIMEOUTMS,
        )
        self.db = self.client[db]
        self.collection = self.db[collection]

    @retry_on_mongodb_error
    async def check_connection(self):
            await self.collection.find_one({}, projection={"_id": 1})
            logger.info("MongoDB instance, database and collection are recheable. Proceeding...")

    # TODO add tests
    @retry_on_mongodb_error
    async def capture_workorder(self, orderNo: int) -> TracOSWorkorder | None:
        logger.info(
            f"Querying {self.collection.name} collection for workorder #{orderNo}"
        )
        doc = await self.collection.find_one({"number": orderNo})

        if doc is None:
            logger.info(
                f"Workorder {orderNo} not found in {self.collection.name} collection"
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

    @retry_on_mongodb_error
    async def insert_workorder(self, order: TracOSWorkorder) -> None:
        synced_order = order.model_copy(
            update={"isSynced": True, "syncedAt": datetime.now(timezone.utc)}
        )

        document = synced_order.model_dump(by_alias=True, exclude_none=True)
        try:
            result = await self.collection.insert_one(document)
            logger.success(
                f"Added workorder #{order.number} to MongoDB instance: _id: {result.inserted_id}"
            )
        except Exception as e:
            logger.warning(f"Exception: {e}")

    @retry_on_mongodb_error
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
                logger.success(f"Updated workorder #{order.number} in MongoDB")

        except Exception as e:
            logger.warning(f"Exception: {e}")

    # TODO tests and exceptions
    @retry_on_mongodb_error
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

    @retry_on_mongodb_error
    async def mark_workorder_as_synced(self, orderNo: int) -> None:
        try:
            logger.info(f"Marking order #{orderNo} as synced in MongoDB")
            await self.collection.update_one(
                {"_id": orderNo},
                {"$set": {"isSynced": True, "syncedAt": datetime.now(timezone.utc)}},
            )
            logger.success(f"Successfully marked order #{orderNo} as synced in MongoDB")
        except Exception as e:
            logger.warning(f"Exception: {e}")
