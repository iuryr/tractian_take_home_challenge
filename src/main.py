"""Entrypoint for the application."""
from pathlib import Path
import asyncio
from typing import Any
from client_erp_adapter import ClientERP

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

    for obj in compliant_payloads:
        print(obj)

if __name__ == "__main__":
    asyncio.run(main())
