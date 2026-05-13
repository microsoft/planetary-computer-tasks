#!/usr/bin/env python3
"""Add the storage extension and storage:schemes to all dataset collection template.json files."""

import json
import sys
from pathlib import Path

STORAGE_EXTENSION = "https://stac-extensions.github.io/storage/v2.0.0/schema.json"
REPO_ROOT = Path(__file__).parent.parent


def process_template(path: Path) -> str:
    """Return 'skipped', 'updated', or 'missing_fields:<list>'."""
    with open(path) as f:
        collection = json.load(f)

    if STORAGE_EXTENSION in collection.get("stac_extensions", []):
        return "skipped"

    account = collection.get("msft:storage_account")
    container = collection.get("msft:container")
    region = collection.get("msft:region")

    missing = [
        field
        for field, value in [
            ("msft:storage_account", account),
            ("msft:container", container),
            ("msft:region", region),
        ]
        if not value
    ]
    if missing:
        return f"missing_fields:{','.join(missing)}"

    # Add storage extension
    extensions = collection.setdefault("stac_extensions", [])
    extensions.append(STORAGE_EXTENSION)

    # Add storage:schemes
    collection["storage:schemes"] = {
        "azure": {
            "type": "ms-azure",
            "platform": "https://{account}.blob.core.windows.net",
            "account": account,
            "container": container,
            "region": region,
        }
    }

    with open(path, "w") as f:
        json.dump(collection, f, indent=4)
        f.write("\n")

    return "updated"


def main() -> None:
    templates = sorted(REPO_ROOT.rglob("datasets/**/template.json"))
    print(f"Found {len(templates)} template.json files under datasets/\n")

    counts: dict[str, int] = {"updated": 0, "skipped": 0, "missing": 0}

    for path in templates:
        result = process_template(path)
        rel = path.relative_to(REPO_ROOT)
        if result == "updated":
            counts["updated"] += 1
            print(f"  updated  {rel}")
        elif result == "skipped":
            counts["skipped"] += 1
        else:
            counts["missing"] += 1
            print(f"  SKIPPED  {rel} ({result})", file=sys.stderr)

    print(
        f"\nDone: {counts['updated']} updated, "
        f"{counts['skipped']} already had extension, "
        f"{counts['missing']} skipped (missing msft fields)"
    )


if __name__ == "__main__":
    main()
