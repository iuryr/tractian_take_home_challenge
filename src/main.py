"""Entrypoint for the application."""
import asyncio
import os
from pathlib import Path
from typing import Any
from jsonschema import ValidationError, validate
from loguru import logger
from dotenv import load_dotenv

from adapters.client_erp_adapter import ClientERP
from adapters.tracos_adapter import TracOSAdapter
from services.translator import client_to_tracos, tracos_to_client

from models.customer_system_models import CustomerSystemWorkorder
from models.tracOS_models import TracOSWorkorder
from schemas.client_erp_schema import CLIENT_WORKORDER_SCHEMA

# ----- CONFIG -----
load_dotenv()
DATA_INBOUND_DIR = Path(os.getenv("DATA_INBOUND_DIR", "data/inbound"))
DATA_OUTBOUND_DIR = Path(os.getenv("DATA_OUTBOUND_DIR", "data/outbound"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "tractian")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "workorders")

logger.info(f"VARIABLE VALUE FOR CONFERENCE -> DATA_INBOUND_DIR: {DATA_INBOUND_DIR}")
logger.info(f"VARIABLE VALUE FOR CONFERENCE -> DATA_OUTBOUND_DIR: {DATA_OUTBOUND_DIR}")
logger.info(f"VARIABLE VALUE FOR CONFERENCE -> MONGO_URI: {MONGO_URI}")
logger.info(f"VARIABLE VALUE FOR CONFERENCE -> MONGO_DATABASE: {MONGO_DATABASE}")
logger.info(f"VARIABLE VALUE FOR CONFERENCE -> MONGO_COLLECTION: {MONGO_COLLECTION}")
# ------------------

#create outbound directory if it does not exist
if not os.path.exists(DATA_OUTBOUND_DIR):
    logger.info(f"Creating outbound directory {DATA_OUTBOUND_DIR}")
    os.makedirs(DATA_OUTBOUND_DIR)


def validate_schema(
    json_object: dict[str, Any], pathname: Path, objectschema: dict[str, Any]
) -> bool:
    """Validates an object against a provided json schema. pathname is the name of json file that generated such object"""
    try:
        validate(instance=json_object, schema=objectschema)
        return True
    except ValidationError as e:
        logger.warning(f"{pathname} is non compliant with client ERP schema")
        logger.warning(f"Error: {e.message}")
        logger.warning(f"Error: {e.relative_schema_path}")
        return False


def read_json_payloads(
    client: ClientERP,
) -> list[tuple[Path, dict[str, Any]]]:  # pyright: ignore[reportExplicitAny]
    json_payloads: list[tuple[Path, dict[str, Any]]] = []
    json_filenames = client.capture_json_filenames(DATA_INBOUND_DIR)
    for filename in json_filenames:
        candidate_json = client.read_json_file(filename)
        if candidate_json:
            json_payloads.append((filename, candidate_json))
    return json_payloads


def validate_json_payloads(
    json_payloads: list[tuple[Path, dict[str, Any]]]
) -> list[dict[str, Any]]:
    """"Given a list of objects, a new list with only that ones that are compliant to a schema"""
    valid_json_payloads: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]

    for payload in json_payloads:
        if validate_schema(payload[1], payload[0], CLIENT_WORKORDER_SCHEMA) is True:
            valid_json_payloads.append(payload[1])
    return valid_json_payloads


def prepare_domain_client_objects(
    json_payloads: list[dict[str, Any]]
) -> list[CustomerSystemWorkorder]:
    """From a list of objects creates a list CustomerSystemWorkorder"""
    client_objects: list[CustomerSystemWorkorder] = []
    for doc in json_payloads:
        workorder = CustomerSystemWorkorder.model_validate(doc)
        client_objects.append(workorder)
    return client_objects


async def sync_to_tracos(
    client_objs_translated_to_tracos: list[TracOSWorkorder], tracos: TracOSAdapter
) -> None:
    for obj in client_objs_translated_to_tracos:
        tracos_workorder = await tracos.capture_workorder(obj.number)
        if tracos_workorder is None:
            await tracos.insert_workorder(obj)
        #if data on DB is older (came before) than inbound data, then update
        elif tracos_workorder.updatedAt < obj.updatedAt:
            await tracos.update_workorder(obj)


async def sync_to_client(
    client_objs: list[CustomerSystemWorkorder], tracos: TracOSAdapter, client: ClientERP
) -> None:
    for obj in client_objs:
        client_workoder_dict = obj.model_dump(mode="json")
        try:
            validate(instance=client_workoder_dict, schema=CLIENT_WORKORDER_SCHEMA)
            if client.write_json_file(DATA_OUTBOUND_DIR, client_workoder_dict):
                await tracos.mark_workorder_as_synced(obj.orderNo)
        except ValidationError as e:
            logger.warning(
                f"Translated object of workorder{client_workoder_dict['orderNo']} is non compliant with client ERP schema"
            )
            logger.warning(f"Error: {e.message}")
            logger.warning(f"Error: {e.relative_schema_path}")
    return


async def main():
    tracos = TracOSAdapter(MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION)
    client = ClientERP()

    await tracos.check_connection()

    # INBOUND FLOW
    json_payloads = read_json_payloads(client)
    valid_json_payloads = validate_json_payloads(json_payloads)
    client_objects = prepare_domain_client_objects(valid_json_payloads)

    client_obj_as_tracos_obj = []
    for obj in client_objects:
        client_obj_as_tracos_obj.append(client_to_tracos(obj))

    await sync_to_tracos(client_obj_as_tracos_obj, tracos)

    # OUTBOUND FLOW
    unsynced_tracos_orders = await tracos.capture_unsynced_workorders()
    tracos_obj_as_client_obj = []
    for obj in unsynced_tracos_orders:
        tracos_obj_as_client_obj.append(tracos_to_client(obj))

    await sync_to_client(tracos_obj_as_client_obj, tracos, client)


if __name__ == "__main__":
    asyncio.run(main())
