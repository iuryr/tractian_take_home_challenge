import json
from pathlib import Path
from loguru import logger
from typing import Any


class ClientERP:
    def __init__(self):
        pass

    # TODO add tests
    def capture_json_filenames(self, dir: Path) -> list[Path]:
        # data_inbound_dir absolute, relative, not a dir
        if dir.is_dir() is False:
            logger.warning(
                "DATA_INBOUND_DIR environment variable does not resolve to a directory."
            )
            return []

        logger.info(f"Capturing full pathnames of json files inside {dir}")
        try:
            return list(dir.glob("*.json"))
        except PermissionError:
            logger.warning(f"No permission to read directory {dir}")
            return []

    # TODO what if the file has more than one JSON
    def read_json_file(
        self, path: Path
    ) -> dict[str, Any] | None:  # pyright: ignore[reportExplicitAny]
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

    # TODO check if there are exceptions to handle
    def write_json_file(self, dir: Path, content: dict[str, Any]) -> bool:
        print(content)
        filepath: Path = dir / f"{content['orderNo']}.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(content, f)
                logger.info(f"Order #{content['orderNo']} contents saved in {filepath}")
                return True
        except FileNotFoundError:
            logger.warning(f"Directory does not exist: {dir}")
            return False

        except PermissionError:
            logger.warning(f"No permission to write file {filepath}")
            return False
