"""Entrypoint for the application."""
from pathlib import Path
import asyncio
from typing import Any
from client_erp_adapter import ClientERP
from models.customer_system_models import CustomerSystemWorkorder

async def main():
    client = ClientERP()
    json_files = client.capture_json_filenames()
    compliant_payloads: list[dict[str, Any]] = []
    for file in json_files:
        candidate = client.read_json_file(file)
        if candidate is None:
            continue
        if client.validate_schema(candidate, file) is True:
            compliant_payloads.append(candidate)

    domain_objects = []
    for obj in compliant_payloads:
        workorder = CustomerSystemWorkorder.model_validate(obj)
        print(workorder)
        domain_objects.append(workorder)
        # print(obj)
    print(domain_objects)


if __name__ == "__main__":
    asyncio.run(main())
