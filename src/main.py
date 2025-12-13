"""Entrypoint for the application."""
from pathlib import Path
import asyncio
from client_erp_adapter import ClientERP

async def main():
    client = ClientERP()
    client.read_api_response(Path("./data/inbound/1.json"))
    print("Hello, World!")


if __name__ == "__main__":
    asyncio.run(main())
