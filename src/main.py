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


def validate_schema(
    json_object: dict[str, Any], pathname: Path, objectschema: dict[str, Any]
) -> bool:
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
    valid_json_payloads: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]

    for payload in json_payloads:
        if validate_schema(payload[1], payload[0], CLIENT_WORKORDER_SCHEMA) is True:
            valid_json_payloads.append(payload[1])
    return valid_json_payloads


def prepare_domain_client_objects(
    json_payloads: list[dict[str, Any]]
) -> list[CustomerSystemWorkorder]:
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
        elif tracos_workorder.updatedAt > obj.updatedAt:
            await tracos.update_workorder(obj)


async def translate_and_sync_to_client(
    unsynced_tracos_orders: list[TracOSWorkorder],
    tracos: TracOSAdapter,
    client: ClientERP,
) -> None:
    for order in unsynced_tracos_orders:
        client_workoder = tracos_to_client(order)
        client_workoder_dict = client_workoder.model_dump(mode="json")
        try:
            validate(instance=client_workoder_dict, schema=CLIENT_WORKORDER_SCHEMA)
            if client.write_json_file(DATA_OUTBOUND_DIR, client_workoder_dict):
                await tracos.mark_workorder_as_synced(order)
        except ValidationError as e:
            logger.warning(
                f"Translated object of workorder{client_workoder_dict['orderNo']} is non compliant with client ERP schema"
            )
            logger.warning(f"Error: {e.message}")
            logger.warning(f"Error: {e.relative_schema_path}")
    return


async def main():
    tracos = TracOSAdapter()
    client = ClientERP()

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
    await translate_and_sync_to_client(unsynced_tracos_orders, tracos, client)


if __name__ == "__main__":
    asyncio.run(main())
