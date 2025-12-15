"""Entrypoint for the application."""
import asyncio
import os
from pathlib import Path
from typing import Any
from jsonschema import ValidationError, validate
from loguru import logger

from client_erp_adapter import ClientERP
from tracos_adapter import TracOSAdapter
from translator import client_to_tracos, tracos_to_client

from models.customer_system_models import CustomerSystemWorkorder
from models.tracOS_models import TracOSWorkorder
from schemas.client_erp_schema import CLIENT_WORKORDER_SCHEMA

DATA_OUTBOUND_DIR = Path(os.getenv("DATA_OUTBOUND_DIR", "data/outbound"))
DATA_INBOUND_DIR = Path(os.getenv("DATA_INBOUND_DIR", "data/inbound"))

def validate_schema(json_object: dict[str, Any], pathname: Path, objectschema : dict[str, Any]) -> bool:
    try:
        validate(instance=json_object, schema=objectschema)
        return True
    except ValidationError as e:
        logger.warning(f"{pathname} is non compliant with client ERP schema")
        logger.warning(f"Error: {e.message}")
        logger.warning(f"Error: {e.relative_schema_path}")
        return False

def read_and_validate_json_payloads(client: ClientERP) -> list[dict[str, Any]]:
    valid_json_payloads: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]

    json_filenames = client.capture_json_filenames(DATA_INBOUND_DIR)
    for filename in json_filenames:
        candidate_json = client.read_json_file(filename)
        if candidate_json is None:
            continue
        if validate_schema(candidate_json, filename, CLIENT_WORKORDER_SCHEMA) is True:  # pyright: ignore[reportAny]
            valid_json_payloads.append(candidate_json)  # pyright: ignore[reportAny]
    return valid_json_payloads

def prepare_domain_client_objects(json_payloads: list[dict[str, Any]])-> list[CustomerSystemWorkorder] :
    client_objects : list[CustomerSystemWorkorder] = []
    for doc in json_payloads:
        workorder = CustomerSystemWorkorder.model_validate(doc)
        client_objects.append(workorder)
    return client_objects

async def translate_and_sync_to_tracos(client_objects : list[CustomerSystemWorkorder], tracos: TracOSAdapter)-> None:
    for obj in client_objects:
        client_workorder_translated = client_to_tracos(obj)
        tracos_workorder = await tracos.capture_workorder(client_workorder_translated.number)
        if tracos_workorder is None:
            await tracos.insert_workorder(client_workorder_translated)
        elif tracos_workorder.updatedAt > client_workorder_translated.updatedAt:
            await tracos.update_workorder(client_workorder_translated)


async def main():
    tracos = TracOSAdapter()
    client = ClientERP()

###INBOUND FLOW
    json_payloads : list[dict[str, Any]] = read_and_validate_json_payloads(client)  # pyright: ignore[reportExplicitAny]
    #transform json payload into domain object and store
    client_objects = prepare_domain_client_objects(json_payloads)

    #for each domain object, check if it needs to be inserted or updated
    await translate_and_sync_to_tracos(client_objects, tracos)

### OUTBOUND


    unsynced_tracos_orders = await tracos.capture_unsynced_workorders()
    for order in unsynced_tracos_orders:
        client_workoder = tracos_to_client(order)
        client_workoder_dict = client_workoder.model_dump(mode="json")
        try:
            validate(instance=client_workoder_dict, schema=CLIENT_WORKORDER_SCHEMA)
            if client.write_json_file(DATA_OUTBOUND_DIR, client_workoder_dict):
                await tracos.mark_workorder_as_synced(order)
        except ValidationError as e:
            logger.warning(f"Translated object of workorder{client_workoder_dict['orderNo']} is non compliant with client ERP schema")
            logger.warning(f"Error: {e.message}")
            logger.warning(f"Error: {e.relative_schema_path}")


if __name__ == "__main__":
    asyncio.run(main())
