from importlib import reload
import sys
import pytest
import pytest_asyncio
import asyncio
import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from main import main
from tracos_adapter import TracOSAdapter
from client_erp_adapter import ClientERP
from models.tracOS_models import TracOSWorkorder
from models.customer_system_models import CustomerSystemWorkorder


# Test configuration
TEST_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
TEST_MONGO_DATABASE = "tractian_test"
TEST_MONGO_COLLECTION = "workorders_test"
TEST_DATA_INBOUND_DIR = Path("test_data/inbound")
TEST_DATA_OUTBOUND_DIR = Path("test_data/outbound")


@pytest_asyncio.fixture(scope="function")
async def mongo_setup():
    """Setup and teardown MongoDB test database"""
    client = AsyncIOMotorClient(TEST_MONGO_URI)
    db = client[TEST_MONGO_DATABASE]
    collection = db[TEST_MONGO_COLLECTION]
    
    # Clean up before test
    await collection.delete_many({})
    
    yield collection
    
    # Clean up after test
    await collection.delete_many({})
    client.close()


@pytest.fixture(scope="function")
def filesystem_setup():
    """Setup and teardown test directories"""
    # Create test directories
    TEST_DATA_INBOUND_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DATA_OUTBOUND_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clean directories
    for file in TEST_DATA_INBOUND_DIR.glob("*.json"):
        file.unlink()
    for file in TEST_DATA_OUTBOUND_DIR.glob("*.json"):
        file.unlink()
    
    yield
    
    # Clean up after test
    shutil.rmtree("test_data", ignore_errors=True)


@pytest.fixture(scope="function")
def set_test_env_vars(filesystem_setup):
    """Set environment variables for testing"""
    original_env = {}
    env_vars = {
        "MONGO_URI": TEST_MONGO_URI,
        "MONGO_DATABASE": TEST_MONGO_DATABASE,
        "MONGO_COLLECTION": TEST_MONGO_COLLECTION,
        "DATA_INBOUND_DIR": str(TEST_DATA_INBOUND_DIR),
        "DATA_OUTBOUND_DIR": str(TEST_DATA_OUTBOUND_DIR),
    }
    
    # Save original values and set test values
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
 # CRITICAL: Reload main module so it picks up new environment variables
    if 'main' in sys.modules:
        import main
        reload(main)
    
    yield
    
    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    
    # Reload main again to restore original config
    if 'main' in sys.modules:
        import main
        reload(main)


@pytest.mark.asyncio
async def test_e2e_inbound_flow_new_workorder(mongo_setup, set_test_env_vars):
    """
    Test inbound flow: Customer ERP -> TracOS
    Scenario: New workorder from customer system should be inserted into TracOS
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    
    # Create a customer workorder file
    customer_workorder = {
        "orderNo": 100,
        "isActive": False,
        "isCanceled": False,
        "isDeleted": False,
        "isDone": True,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Test workorder for E2E",
        "creationDate": base_time.isoformat(),
        "lastUpdateDate": base_time.isoformat(),
        "deletedDate": None,
    }
    
    with open(TEST_DATA_INBOUND_DIR / "100.json", "w") as f:
        json.dump(customer_workorder, f)
    
    # Run the main sync process
    await main()
    
    # Verify workorder was inserted into TracOS
    doc = await collection.find_one({"number": 100})
    assert doc is not None, "Workorder should be inserted into TracOS"
    assert doc["number"] == 100
    assert doc["status"] == "completed"
    assert doc["description"] == "Test workorder for E2E"
    assert doc["deleted"] is False
    assert doc["isSynced"] is True


@pytest.mark.asyncio
async def test_e2e_inbound_flow_update_workorder(mongo_setup, set_test_env_vars):
    """
    Test inbound flow: Customer ERP -> TracOS
    Scenario: Updated workorder from customer should update TracOS if customer version is newer
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    old_time = base_time - timedelta(hours=2)
    
    # Insert existing workorder in TracOS (older version)
    await collection.insert_one({
        "_id": ObjectId(),
        "number": 101,
        "status": "pending",
        "title": "Old workorder",
        "description": "Old description",
        "createdAt": old_time,
        "updatedAt": old_time,
        "deleted": False,
        "deletedAt": None,
        "isSynced": False,
        "syncedAt": None,
    })
    
    # Create newer customer workorder file
    customer_workorder = {
        "orderNo": 101,
        "isActive": False,
        "isCanceled": False,
        "isDeleted": False,
        "isDone": True,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Updated description",
        "creationDate": old_time.isoformat(),
        "lastUpdateDate": base_time.isoformat(),
        "deletedDate": None,
    }
    
    with open(TEST_DATA_INBOUND_DIR / "101.json", "w") as f:
        json.dump(customer_workorder, f)
    
    # Run the main sync process
    await main()
    
    # Verify workorder was updated in TracOS
    doc = await collection.find_one({"number": 101})
    assert doc is not None
    assert doc["status"] == "completed", "Status should be updated"
    assert doc["description"] == "Updated description", "Description should be updated"


@pytest.mark.asyncio
async def test_e2e_outbound_flow_new_workorder(mongo_setup, set_test_env_vars):
    """
    Test outbound flow: TracOS -> Customer ERP
    Scenario: Unsynced workorder in TracOS should be written to customer system
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    
    # Insert unsynced workorder in TracOS
    await collection.insert_one({
        "_id": ObjectId(),
        "number": 200,
        "status": "in_progress",
        "title": "Outbound test workorder",
        "description": "This should sync to customer",
        "createdAt": base_time,
        "updatedAt": base_time,
        "deleted": False,
        "deletedAt": None,
        "isSynced": False,
        "syncedAt": None,
    })
    
    # Run the main sync process
    await main()
    
    # Verify workorder was written to customer system
    outbound_file = TEST_DATA_OUTBOUND_DIR / "200.json"
    assert outbound_file.exists(), "Workorder file should be created in outbound directory"
    
    with open(outbound_file, "r") as f:
        customer_data = json.load(f)
    
    assert customer_data["orderNo"] == 200
    assert customer_data["isActive"] is True
    assert customer_data["summary"] == "This should sync to customer"
    assert customer_data["isSynced"] is True


@pytest.mark.asyncio
async def test_e2e_bidirectional_sync(mongo_setup, set_test_env_vars):
    """
    Test bidirectional sync: Both inbound and outbound flows in one run
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    
    # Setup: Create inbound customer workorder
    inbound_workorder = {
        "orderNo": 300,
        "isActive": True,
        "isCanceled": False,
        "isDeleted": False,
        "isDone": False,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Inbound workorder",
        "creationDate": base_time.isoformat(),
        "lastUpdateDate": base_time.isoformat(),
        "deletedDate": None,
    }
    
    with open(TEST_DATA_INBOUND_DIR / "300.json", "w") as f:
        json.dump(inbound_workorder, f)
    
    # Setup: Create unsynced TracOS workorder
    await collection.insert_one({
        "_id": ObjectId(),
        "number": 301,
        "status": "completed",
        "title": "Outbound workorder",
        "description": "This goes to customer",
        "createdAt": base_time,
        "updatedAt": base_time,
        "deleted": False,
        "deletedAt": None,
        "isSynced": False,
        "syncedAt": None,
    })
    
    # Run the main sync process
    await main()
    
    # Verify inbound: Customer workorder should be in TracOS
    inbound_doc = await collection.find_one({"number": 300})
    assert inbound_doc is not None
    assert inbound_doc["status"] == "in_progress"
    assert inbound_doc["description"] == "Inbound workorder"
    
    # Verify outbound: TracOS workorder should be in customer system
    outbound_file = TEST_DATA_OUTBOUND_DIR / "301.json"
    assert outbound_file.exists()
    
    with open(outbound_file, "r") as f:
        customer_data = json.load(f)
    
    assert customer_data["orderNo"] == 301
    assert customer_data["isDone"] is True
    assert customer_data["summary"] == "This goes to customer"


@pytest.mark.asyncio
async def test_e2e_malformed_json_handling(mongo_setup, set_test_env_vars):
    """
    Test that malformed JSON files are skipped without crashing
    """
    collection = mongo_setup
    
    # Create a malformed JSON file
    with open(TEST_DATA_INBOUND_DIR / "malformed.json", "w") as f:
        f.write('{"orderNo": 400, "status": incomplete')
    
    # Create a valid workorder
    base_time = datetime.now(timezone.utc)
    valid_workorder = {
        "orderNo": 401,
        "isActive": False,
        "isCanceled": False,
        "isDeleted": False,
        "isDone": True,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Valid workorder",
        "creationDate": base_time.isoformat(),
        "lastUpdateDate": base_time.isoformat(),
        "deletedDate": None,
    }
    
    with open(TEST_DATA_INBOUND_DIR / "401.json", "w") as f:
        json.dump(valid_workorder, f)
    
    # Run the main sync process - should not crash
    await main()
    
    # Verify only valid workorder was processed
    malformed_doc = await collection.find_one({"number": 400})
    assert malformed_doc is None, "Malformed workorder should not be inserted"
    
    valid_doc = await collection.find_one({"number": 401})
    assert valid_doc is not None, "Valid workorder should be inserted"


@pytest.mark.asyncio
async def test_e2e_schema_validation(mongo_setup, set_test_env_vars):
    """
    Test that workorders not compliant with schema are rejected
    """
    collection = mongo_setup
    
    # Create a workorder missing required fields
    invalid_workorder = {
        "orderNo": 500,
        "summary": "Missing status fields",
    }
    
    with open(TEST_DATA_INBOUND_DIR / "500.json", "w") as f:
        json.dump(invalid_workorder, f)
    
    # Run the main sync process
    await main()
    
    # Verify invalid workorder was not inserted
    doc = await collection.find_one({"number": 500})
    assert doc is None, "Invalid workorder should not be inserted"


@pytest.mark.asyncio
async def test_e2e_deleted_workorder_sync(mongo_setup, set_test_env_vars):
    """
    Test syncing of deleted workorders
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    deleted_time = base_time + timedelta(hours=1)
    
    # Create a deleted customer workorder
    deleted_workorder = {
        "orderNo": 600,
        "isActive": False,
        "isCanceled": False,
        "isDeleted": True,
        "isDone": False,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Deleted workorder",
        "creationDate": base_time.isoformat(),
        "lastUpdateDate": deleted_time.isoformat(),
        "deletedDate": deleted_time.isoformat(),
    }
    
    with open(TEST_DATA_INBOUND_DIR / "600.json", "w") as f:
        json.dump(deleted_workorder, f)
    
    # Run the main sync process
    await main()
    
    # Verify deleted workorder is properly synced
    doc = await collection.find_one({"number": 600})
    assert doc is not None
    assert doc["deleted"] is True
    assert doc["deletedAt"] is not None
    assert doc["status"] == "cancelled"


@pytest.mark.asyncio
async def test_e2e_multiple_workorders_batch(mongo_setup, set_test_env_vars):
    """
    Test processing multiple workorders in a single run
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    
    # Create multiple customer workorders
    for i in range(700, 705):
        workorder = {
            "orderNo": i,
            "isActive": False,
            "isCanceled": False,
            "isDeleted": False,
            "isDone": False,
            "isOnHold": False,
            "isPending": True,
            "isSynced": False,
            "summary": f"Batch workorder {i}",
            "creationDate": base_time.isoformat(),
            "lastUpdateDate": base_time.isoformat(),
            "deletedDate": None,
        }
        
        with open(TEST_DATA_INBOUND_DIR / f"{i}.json", "w") as f:
            json.dump(workorder, f)
    
    # Create multiple unsynced TracOS workorders
    for i in range(710, 715):
        await collection.insert_one({
            "_id": ObjectId(),
            "number": i,
            "status": "on_hold",
            "title": f"Outbound batch {i}",
            "description": f"Batch workorder {i}",
            "createdAt": base_time,
            "updatedAt": base_time,
            "deleted": False,
            "deletedAt": None,
            "isSynced": False,
            "syncedAt": None,
        })
    
    # Run the main sync process
    await main()
    
    # Verify all inbound workorders were processed
    for i in range(700, 705):
        doc = await collection.find_one({"number": i})
        assert doc is not None, f"Workorder {i} should be in TracOS"
        assert doc["status"] == "pending"
    
    # Verify all outbound workorders were written
    for i in range(710, 715):
        outbound_file = TEST_DATA_OUTBOUND_DIR / f"{i}.json"
        assert outbound_file.exists(), f"Workorder {i} should be in outbound directory"


@pytest.mark.asyncio
async def test_e2e_no_update_when_tracos_newer(mongo_setup, set_test_env_vars):
    """
    Test that TracOS workorder is NOT updated when it's newer than customer version
    """
    collection = mongo_setup
    base_time = datetime.now(timezone.utc)
    old_time = base_time - timedelta(hours=2)
    
    # Insert newer workorder in TracOS
    await collection.insert_one({
        "_id": ObjectId(),
        "number": 800,
        "status": "completed",
        "title": "Newer TracOS workorder",
        "description": "This should not be overwritten",
        "createdAt": old_time,
        "updatedAt": base_time,  # Newer
        "deleted": False,
        "deletedAt": None,
        "isSynced": False,
        "syncedAt": None,
    })
    
    # Create older customer workorder file
    customer_workorder = {
        "orderNo": 800,
        "isActive": True,
        "isCanceled": False,
        "isDeleted": False,
        "isDone": False,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Older customer version",
        "creationDate": old_time.isoformat(),
        "lastUpdateDate": old_time.isoformat(),  # Older
        "deletedDate": None,
    }
    
    with open(TEST_DATA_INBOUND_DIR / "800.json", "w") as f:
        json.dump(customer_workorder, f)
    
    # Run the main sync process
    await main()
    
    # Verify TracOS workorder was NOT updated
    doc = await collection.find_one({"number": 800})
    assert doc is not None
    assert doc["status"] == "completed", "Status should remain as TracOS version"
    assert doc["description"] == "This should not be overwritten"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
