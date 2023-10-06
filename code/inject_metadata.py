"""Add some predefined metadata to the catalog

Given a dataset, look up dataset's ID and version, and use it to add
predefined metadata to the catalog.

"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import tomli

from datalad.api import Dataset, catalog_add
from datalad_catalog.schema_utils import (
    get_metadata_item,
)


def get_ds_info(ds_path):
    ds = Dataset(ds_path)
    return (ds.id, ds.repo.get_hexsha())


def new_meta_item(ds_path):
    """Create a minimal valid dataset metadata blob in catalog schema"""
    ds = Dataset(ds_path)
    meta_item = get_metadata_item(
        item_type='dataset',
        dataset_id=ds.id,
        dataset_version=ds.repo.get_hexsha(),
        source_name="manual_addition",
        source_version="0.1.0",
    )
    return meta_item


# Command line input
parser = argparse.ArgumentParser()
parser.add_argument(
    "dataset",
    help="Dataset for which metadata will be injected into the catalog",
    type=Path,
)
parser.add_argument("--funding", help="Add funding info", action="store_true")
parser.add_argument("--keywords", help="Add keywords", action="store_true")
args = parser.parse_args()

if not any((args.funding, args.keywords)):
    # can be more
    parser.error("No options specified, nothing to do")

# Load hand-generated values
with open(Path(__file__).parent / "manually_entered.toml", "rb") as f:
    manually_entered = tomli.load(f)

# Use specified dataset path to get id, version
meta_item = new_meta_item(args.dataset)
# Assume we're calling from the catalog superdataset
catalog_dir = Path("docs")

if args.funding:
    meta_item["funding"] = [
        {
            "name": "Deutsche Forschungsgemeinschaft (DFG)",
            "identifier": "Project number 431549029",
            "description": "SFB1451: Key mechanisms of motor control in health and disease",
        }
    ]

if args.keywords:
    project_name = args.dataset.name  # assume dataset tld = project name
    keywords = manually_entered["keywords"].get(project_name)
    if keywords is not None:
        meta_item["keywords"] = keywords

res = catalog_add(
    catalog=catalog_dir,
    metadata=json.dumps(meta_item),
    config_file=catalog_dir / "config.json",
)
