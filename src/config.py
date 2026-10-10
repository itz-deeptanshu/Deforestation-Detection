from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config():
    """Read config.yaml from the project root and return it as a dict."""
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)