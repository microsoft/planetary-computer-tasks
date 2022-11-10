"""
Additional checks on dataset collections.
"""
import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

DATETIME_RFC339 = "%Y-%m-%dT%H:%M:%SZ"


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser("check-collection")
    parser.add_argument(
        "collection", nargs="?", type=argparse.FileType("r"), default=sys.stdin
    )
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    args2 = parse_args(args)
    data = json.loads(args2.collection.read())

    try:
        validate_collection(data)
        code = 0
    except Exception as e:
        print(e, file=sys.stderr)
        code = 1
    return code


def validate_collection(collection: Dict) -> None:
    """
    Planetary Computer specific validation for STAC collections.
    """
    required_keys = [
        "msft:short_description",
        "msft:storage_account",
        "msft:container",
        "title",
    ]
    errors = [
        f"Missing required key '{x}'" for x in required_keys if x not in collection
    ]

    if "assets" not in collection or "thumbnail" not in collection["assets"]:
        errors.append("Missing 'thumbnail' in 'collection.assets'.")

    # Ensure temporal extent datetime is formatted correctly
    temporal_extent_intervals: List[List[str]] = collection["extent"]["temporal"][
        "interval"
    ]
    for interval in temporal_extent_intervals:
        if len(interval) != 2:
            errors.append(
                f"Temporal extent interval '{interval}' is not a pair of datetimes."
            )
            continue

        start_datetime_str: str = interval[0]
        end_datetime_str: str = interval[1]

        start_datetime: Optional[datetime] = None
        end_datetime: Optional[datetime] = None

        if start_datetime_str:
            try:
                start_datetime = datetime.strptime(start_datetime_str, DATETIME_RFC339)
            except ValueError as e:
                errors.append(
                    f"Temporal extent start datetime '{start_datetime_str}' "
                    f"is invalid: {e}"
                )

        if end_datetime_str:
            try:
                end_datetime = datetime.strptime(end_datetime_str, DATETIME_RFC339)
            except ValueError as e:
                errors.append(
                    f"Temporal extent end datetime '{start_datetime_str}' "
                    f"is invalid: {e}"
                )

        if start_datetime and end_datetime and start_datetime > end_datetime:
            errors.append(
                f"Temporal extent start datetime '{start_datetime_str}' "
                f"is after end datetime '{end_datetime_str}'."
            )

    cid = collection.get("id", "")
    if "_" in cid:
        errors.append(f"Collection id '{cid}' should use hyphens, not underscores.")

    for provider in collection["providers"]:
        if provider["name"].lower() == "microsoft" and provider["name"] != "Microsoft":
            errors.append(
                f"Provider 'Microsoft' should be titlecase. Got "
                f"{provider['name']} instead."
            )

    has_license_link = False
    for link in collection.get("links", []):
        if link.get("rel") == "license":
            has_license_link = True
            if "title" not in link:
                errors.append("license link must have a title.")

        if link.get("rel") == "self":
            errors.append(f"Collection should not have 'self' links: {link}")

    if not has_license_link:
        errors.append("must have license link")

    if errors:
        msg = "\n\n".join(errors)
        raise ValueError(msg)


if __name__ == "__main__":
    sys.exit(main())
