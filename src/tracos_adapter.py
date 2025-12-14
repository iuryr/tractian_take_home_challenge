import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "tractian")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "workorders")

class TracOSAdapter:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DATABASE]
        self.collection = self.db[MONGO_COLLECTION]
