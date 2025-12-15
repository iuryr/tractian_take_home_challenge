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

def validate_schema(json_object: dict[str, Any], pathname: Path, schema : dict[str, Any]) -> bool:
    try:
        validate(instance=json_object, schema=CLIENT_WORKORDER_SCHEMA)
        return True
    except ValidationError as e:
        logger.warning(f"{pathname} is non compliant with client ERP schema")
        logger.warning(f"Error: {e.message}")
        logger.warning(f"Error: {e.relative_schema_path}")
        return False

async def main():
    tracos = TracOSAdapter()
    client = ClientERP()

###INBOUND
    #capture filenames
    json_files = client.capture_json_filenames()
    #read json files
    compliant_payloads: list[dict[str, Any]] = []
    for file in json_files:
        candidate = client.read_json_file(file)
        if candidate is None:
            continue
        #append valid json to list
        if validate_schema(candidate, file) is True:
            compliant_payloads.append(candidate)

    #transform json into domain object and store
    domain_objects : list[CustomerSystemWorkorder] = []
    for obj in compliant_payloads:
        workorder = CustomerSystemWorkorder.model_validate(obj)
        # print(workorder)
        domain_objects.append(workorder)
        # print(obj)
    # print(domain_objects)
    #for each domain object, check if it needs to be inserted or updated
    for obj in domain_objects:
        client_workorder_translated = client_to_tracos(obj)
        tracos_workorder = await tracos.capture_workorder(client_workorder_translated.number)
        if tracos_workorder is None:
            await tracos.insert_workorder(client_workorder_translated)
        elif tracos_workorder.updatedAt > client_workorder_translated.updatedAt:
            await tracos.update_workorder(client_workorder_translated)

### OUTBOUND

    from jsonschema import validate
    from schemas.client_erp_schema import CLIENT_WORKORDER_SCHEMA

    unsynced_tracos_orders = await tracos.capture_unsynced_workorders()
    for order in unsynced_tracos_orders:
        client_workoder = tracos_to_client(order)
        client_workoder_dict = client_workoder.model_dump(mode="json")
        validate(instance = client_workoder_dict, schema=CLIENT_WORKORDER_SCHEMA)
        if client.write_json_file(DATA_OUTBOUND_DIR, client_workoder_dict):
            await tracos.mark_workorder_as_synced(order)

if __name__ == "__main__":
    asyncio.run(main())
