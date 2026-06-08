from pathlib import Path

import yaml


def load_yaml(filename: str) -> dict:
    path = Path(__file__).parent.parent / "schemas" / filename
    with path.open(mode="r", encoding="utf-8") as file:
        return yaml.safe_load(file)
