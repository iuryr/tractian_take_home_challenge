#!/usr/bin/env python3
import asyncio
import json
import os
from random import randint
from datetime import datetime, timedelta, timezone
import stat
from bson import ObjectId
from typing import Literal, TypedDict
from random import choice
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.collection import Collection
from loguru import logger

# ----- CONFIG -----
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "tractian")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "workorders")
DATA_INBOUND_DIR = os.getenv("DATA_INBOUND_DIR", "data/inbound")
# ------------------

# Create inbound workorders directory if it doesn't exist
if not os.path.exists(DATA_INBOUND_DIR):
    os.makedirs(DATA_INBOUND_DIR)

# Constants
NUMBER_OF_WORKORDERS_SAMPLES_ON_TRACOS: int = 10
NUMBER_OF_WORKORDERS_SAMPLES_ON_CUSTOMER_SYSTEM: int = 15


async def get_mongo_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(MONGO_URI)


class TracOSWorkorder(TypedDict):
    _id: ObjectId
    number: int
    status: Literal["pending", "in_progress", "completed", "on_hold", "cancelled"]
    title: str
    description: str
    createdAt: datetime
    updatedAt: datetime
    deleted: bool
    deletedAt: datetime | None = None
    isSynced: bool
    syncedAt: datetime | None = None


class CustomerSystemWorkorder(TypedDict):
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


# Global base time for sample creation
base = datetime.now(timezone.utc) - timedelta(days=30)


def create_tracos_sample_workorders() -> list[TracOSWorkorder]:
    """Generate n sample workorder documents."""
    samples: list[TracOSWorkorder] = []
    for i in range(1, NUMBER_OF_WORKORDERS_SAMPLES_ON_TRACOS + 1):
        samples.append(
            {
                "_id": ObjectId(),
                "number": i,
                "status": choice(
                    ["pending", "in_progress", "completed", "on_hold", "cancelled"]
                ),
                "title": f"Example workorder #{i}",
                "description": f"Example workorder #{i} description",
                "createdAt": (base + timedelta(days=i)).isoformat(),
                "updatedAt": (
                    base + timedelta(days=i, hours=randint(0, 10))
                ).isoformat(),
                "deleted": False,
                "isSynced": False,
                "syncedAt": None,
            }
        )
    return samples


def create_customer_system_sample_workorders() -> list[CustomerSystemWorkorder]:
    """Generate n sample workorder documents."""
    samples: list[CustomerSystemWorkorder] = []
    for i in range(1, NUMBER_OF_WORKORDERS_SAMPLES_ON_CUSTOMER_SYSTEM + 1):
        _status = choice(
            ["pending", "in_progress", "completed", "on_hold", "cancelled", "deleted"]
        )
        sample = {
            "orderNo": i,
            "isActive": _status == "in_progress",
            "isCanceled": _status == "cancelled",
            "isDeleted": _status == "deleted",
            "isDone": _status == "completed",
            "isOnHold": _status == "on_hold",
            "isPending": _status == "pending",
            "isSynced": False,
            "summary": f"Example workorder #{i}",
            "creationDate": (base + timedelta(days=i)).isoformat(),
            "lastUpdateDate": (
                base + timedelta(days=i, hours=randint(0, 10))
            ).isoformat(),
            "deletedDate": None,
        }
        if sample["isDeleted"]:
            sample["deletedDate"] = (base + timedelta(days=i, hours=1)).isoformat()
        samples.append(sample)
    return samples


async def create_tracos_workorder_on_mongo(
    collection: Collection,
    workorders: list[TracOSWorkorder],
) -> None:
    await collection.insert_many(workorders)


def create_customer_system_workorder_on_file_system(
    workorders: list[CustomerSystemWorkorder],
) -> None:
    for workorder in workorders:
        with open(f"{DATA_INBOUND_DIR}/{workorder['orderNo']}.json", "w") as f:
            json.dump(workorder, f)


def create_malformed_json_customer_workorder_on_filesystem():
    with open(f"{DATA_INBOUND_DIR}/malformed.json", "w") as f:
        f.write('{"field1": "value", "field2"}')
    return


def create_schema_uncompliant_customer_workorder_on_filesystem():
    with open(f"{DATA_INBOUND_DIR}/schema_uncompliant.json", "w") as f:
        json.dump({"isSchemacorrect": False}, f)
    return


def create_no_read_permission_json_on_filesystem():
    path = f"{DATA_INBOUND_DIR}/no_permission.json"
    with open(path, "w") as f:
        json.dump({"isSchemacorrect": False}, f)

    os.chmod(path, stat.S_IWUSR)


async def main():
    logger.info("Starting setup script")
    client = await get_mongo_client()
    db = client.get_database(MONGO_DATABASE)
    collection = db.get_collection(MONGO_COLLECTION)

    logger.info("Creating tracos workorders samples...")
    tracos_workorder_samples = create_tracos_sample_workorders()
    await create_tracos_workorder_on_mongo(collection, tracos_workorder_samples)
    logger.info("TracOS workorders samples created.")

    logger.info("Creating customer system workorders samples...")
    customer_system_workorder_samples = create_customer_system_sample_workorders()
    create_customer_system_workorder_on_file_system(customer_system_workorder_samples)
    create_malformed_json_customer_workorder_on_filesystem()
    create_schema_uncompliant_customer_workorder_on_filesystem()
    create_no_read_permission_json_on_filesystem()
    logger.info("Customer system workorders samples created.")

    logger.info("Setup complete.")


if __name__ == "__main__":
    asyncio.run(main())
