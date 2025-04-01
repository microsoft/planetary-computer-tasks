import logging
from math import isinf, isnan
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def reduce_coordinate_precision(coords: List[Any], precision: int = 7) -> List[Any]:
    return [
        (
            round(x, precision)
            if type(x) is float or type(x) is int
            else reduce_coordinate_precision(x, precision=precision)
        )
        for x in coords
    ]


def reduce_geom_precision(geom: Dict[str, Any], precision: int = 7) -> Dict[str, Any]:
    """Reduces the precision of geom. Mutates the geom."""

    return {
        "coordinates": reduce_coordinate_precision(geom["coordinates"]),
        **{k: v for k, v in geom.items() if k != "coordinates"},
    }


def clean_item_dict(item_dict: Dict[str, Any], log_id: Optional[str] = None) -> None:
    """For the given dict that represents a STAC Item, remove
    any values that are NaN or Inf.
    """
    log_id_str = "" if log_id is None else f" in {log_id}"

    def _clean_dict(d: Dict[str, Any], key_chain: List[str]) -> None:
        keys = list(d.keys())
        for k in keys:
            v = d[k]
            if type(v) is dict:
                _clean_dict(v, key_chain + [k])
            if type(v) is list:
                for i, x in enumerate(v):
                    if type(x) is dict:
                        _clean_dict(x, key_chain + [f"{k}[{i}]]"])
            else:

                if type(v) is float:
                    if isnan(v):
                        logger.warning(
                            f"NaN value for {'.'.join(key_chain)}.{k}{log_id_str}"
                        )
                        del d[k]
                    elif isinf(v):
                        logger.warning(
                            f"Inf value for {'.'.join(key_chain)}.{k}{log_id_str}"
                        )
                        del d[k]

    _clean_dict(item_dict, [])
