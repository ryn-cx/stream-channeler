# TODO: Validate
"""Generate a short_name -> clear_name mapping from the JustWatch providers API.

Usage:
    python scripts/generate-source-names.py
"""

import json
from pathlib import Path

import httpx

PROVIDERS_URL = "https://apis.justwatch.com/content/providers/locale/en_US"
OUTPUT_FILE = Path("frontend/src/data/justwatch-source-names.json")


def main() -> None:
    response = httpx.get(PROVIDERS_URL)
    response.raise_for_status()
    data = response.json()

    mapping = {entry["short_name"]: entry["clear_name"] for entry in data}

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w") as file:
        json.dump(mapping, file, separators=(",", ":"))

    print(f"Wrote {len(mapping)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
