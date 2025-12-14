import os
import json
from jsonschema import validate, ValidationError
from pathlib import Path
from loguru import logger
from typing import Any
from schemas.client_erp_schema import CLIENT_WORKORDER_SCHEMA

DATA_INBOUND_DIR = Path(os.getenv("DATA_INBOUND_DIR", "data/inbound"))

class ClientERP:
    def __init__(self):
        pass
    
    #TODO add tests
    def capture_json_filenames(self) -> list[Path]:
        #data_inbound_dir absolute, relative, not a dir
        if DATA_INBOUND_DIR.is_dir() is False:
            logger.warning("DATA_INBOUND_DIR environment variable does not resolve to a directory.")
            return []

        logger.info(f"Capturing full pathnames of json files inside {DATA_INBOUND_DIR}")
        try:
            return list(DATA_INBOUND_DIR.glob("*.json"))
        except PermissionError:
            logger.warning(f"No permission to read directory {DATA_INBOUND_DIR}")
            return []
    
    #TODO what if the file has more than one JSON
    def read_json_file(self, path: Path):
        """Read JSON file and return dict object if sucessfull"""
        
        try:
            logger.info(f"Reading file {path}")
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:
            logger.warning(f"No permission to read file {path}")
            return None
        except json.JSONDecodeError:
            logger.warning(f"{path} is a malformed JSON")
            return None

    def validate_schema(self, json_object: dict[str, Any], pathname: Path) -> bool:
        try:
            validate(instance=json_object, schema=CLIENT_WORKORDER_SCHEMA)
            return True
        except ValidationError as e:
            logger.warning(f"{pathname} is non compliant with client ERP schema")
            logger.warning(f"Error: {e.message}")
            logger.warning(f"Error: {e.relative_schema_path}")
            return False

