"""
Additional checks on dataset collections.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pystac

DATETIME_RFC339 = "%Y-%m-%dT%H:%M:%SZ"


def validate_collection(collection: Dict) -> Tuple[str, List[str]]:
    """
    Planetary Computer specific validation for STAC collections.
    """
    pystac_collection = pystac.Collection.from_dict(collection)
    # why is this sometimes None and sometimes valid?
    pystac_collection.remove_links(rel=pystac.RelType.ROOT)
    pystac_collection.validate()
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

    return cid, errors

    # if errors:
    #     msg = f"Errors in collection {cid} at {path}\n\n".join(errors)
    #     raise ValueError(msg)
