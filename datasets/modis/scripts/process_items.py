#!/usr/bin/env python

import os
import sys
from datetime import datetime

COLLECTIONS = [
    "09A1",
    "09Q1",
    "10A1",
    "10A2",
    "11A1",
    "11A2",
    "13A1",
    "13Q1",
    "14A1",
    "14A2",
    "15A2H",
    "15A3H",
    "16A3GF",
    "17A2H",
    "17A2HGF",
    "17A3HGF",
    "21A2",
    "43A4",
    "64A1",
]

datestring = datetime.now().strftime("%Y%m%d")

if len(sys.argv) == 1:
    raise ValueError("'suffix' argument must be provided")
else:
    suffix = sys.argv[1]

if len(sys.argv) == 2:
    submit = ""
else:
    submit = sys.argv[2]

if len(sys.argv) > 3:
    raise ValueError("Too many arguments")


for collection in COLLECTIONS:
    os.system("echo")
    os.system(
        f"echo 'Running command: pctasks dataset process-items -d "
        f"datasets/modis/dataset.yaml -c modis-{collection}-061 "
        f"test-process-items-{datestring}-{suffix} {submit}'"
    )
    os.system(
        f"pctasks dataset process-items -d "
        f"datasets/modis/dataset.yaml -c modis-{collection}-061 "
        f"test-process-items-{datestring}-{suffix} {submit}"
    )
