from itertools import groupby
from typing import List, Optional


def crossing_longitude(
    coord1: List[float], coord2: List[float], center_lat: float, max_delta_lon: float
) -> float:
    # check if we are interpolating across the antimeridian
    delta_lon_1 = abs(coord2[0] - coord1[0])
    if delta_lon_1 > max_delta_lon:
        delta_lon_2 = 360 - delta_lon_1
        if coord1[0] < 0:
            coord2[0] = coord1[0] - delta_lon_2
        else:
            coord2[0] = coord1[0] + delta_lon_2

    # interpolate
    crossing_longitude = ((center_lat - coord1[1]) / (coord2[1] - coord1[1])) * (
        coord2[0] - coord1[0]
    ) + coord1[0]

    # force interpolated longitude to be in the range [-180, 180]
    crossing_longitude = ((crossing_longitude + 180) % 360) - 180

    return crossing_longitude


def ccw_or_cw(lon_crossings: List[List[float]], max_delta_lon: float) -> Optional[str]:
    for cross1, cross2 in zip(lon_crossings, lon_crossings[1:]):
        delta_lon = cross2[0] - cross1[0]
        if delta_lon < max_delta_lon:
            if cross1[1] != -cross2[1]:
                raise ValueError("Crossings should be in opposite directions")
            if cross1[1] == -1:
                return "CCW"
            else:
                return "CW"
    return None


def get_winding(coords: List[List[float]], max_delta_lon: float) -> Optional[str]:
    """Heuristic method for determining the winding for complex Sentinel-3
    'strip' polygons that self-intersect and overlap and for simple Sentinel-3
    'chip' polygons that may cross the antimeridian.

    Args:
        coords (List[List[float]]): List of coordinates in the polygon.
        max_delta_lon (float): This argument serves two purposes:
            1. Longitude crossings (of the center latitude of the polygon) that
            are within this distance of each other are considered to be on either
            side of polygon interior.
            2. When interpolating a longitude crossing, if the difference in
            longitudes between the two points is greater than this value, then
            we assume that we are interpolating across the antimeridian.

            --> Recommended values are 120 degrees for strips and chips, and
            300 degrees for the rectangular synergy-v10 and synergy-vg1 products.
    """
    # force all longitudes to be in the range [-180, 180]
    for i, point in enumerate(coords):
        coords[i] = [((point[0] + 180) % 360) - 180, point[1]]

    # duplicate points will cause a divide by zero problem
    coords = [c for c, _ in groupby(coords)]

    # get center latitude against which we will check for crossings
    lats = [coord[1] for coord in coords]
    center_lat = (max(lats) + min(lats)) / 2

    # find all longitude crossings of the center latitude
    lon_crossings = []
    for coord1, coord2 in zip(coords, coords[1:]):
        if coord1[1] >= center_lat and coord2[1] < center_lat:
            lon_crossings.append(
                [crossing_longitude(coord1, coord2, center_lat, max_delta_lon), -1]
            )
        elif coord1[1] <= center_lat and coord2[1] > center_lat:
            lon_crossings.append(
                [crossing_longitude(coord1, coord2, center_lat, max_delta_lon), 1]
            )
    if len(lon_crossings) == 0:
        raise ValueError("No crossings found")
    if len(lon_crossings) % 2 != 0:
        raise ValueError("Number of crossings should always be a multiple of 2")
    lon_crossings = sorted(lon_crossings, key=lambda x: x[0])

    # get winding
    winding = ccw_or_cw(lon_crossings, max_delta_lon)
    if winding is None:
        # we could have an antimeridian crossing
        for crossing in lon_crossings:
            if crossing[0] < 0:
                crossing[0] += 360
        lon_crossings = sorted(lon_crossings, key=lambda x: x[0])
        winding = ccw_or_cw(lon_crossings, max_delta_lon)

    return winding
