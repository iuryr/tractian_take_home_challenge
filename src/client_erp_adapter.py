import os
import json
from pathlib import Path
from loguru import logger

DATA_INBOUND_DIR = Path(os.getenv("DATA_INBOUND_DIR", "data/inbound"))

class ClientERP:
    def __init__(self):
        pass
    
    #TODO what if the file has more than one JSON
    def read_api_response(self, path: Path):
        """Read JSON file and return dict object if sucessfull"""
        
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:
            logger.warning(f"No permission to read file {path}")
            return None
        except json.JSONDecodeError:
            logger.warning(f"{path} is a malformed JSON")
            return None
