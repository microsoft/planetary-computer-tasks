import json
from typing import Any, Dict, List, Union

import pystac
from stac_validator.validate import StacValidate


class STACValidationError(Exception):
    def __init__(self, message: str, detail: List[Dict[str, Any]]):
        super().__init__(message)
        detail = detail


def validate_stac(object: Union[Dict[str, Any], pystac.STACObject]) -> None:
    validator = StacValidate(extensions=True)
    validator.stac_content = object if isinstance(object, dict) else object.to_dict()
    validator.run()
    if not validator.valid:
        raise STACValidationError(
            f"Invalid STAC:\n{json.dumps(validator.message, indent=2)}",
            validator.message,
        )
