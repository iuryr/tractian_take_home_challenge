"""Entrypoint for the application."""
from pathlib import Path
import asyncio
from client_erp_adapter import ClientERP

async def main():
    client = ClientERP()
    json_files = client.capture_json_filenames()
    for file in json_files:
        print(client.read_json_file(file))


if __name__ == "__main__":
    asyncio.run(main())
