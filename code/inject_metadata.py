import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import tempfile

from datalad.api import Dataset, catalog


def get_gitconfig(conf_name):
    result = (
        subprocess.run(["git", "config", conf_name], capture_output=True)
        .stdout.decode()
        .rstrip()
    )
    return result


def get_ds_info(ds_path):
    ds = Dataset(ds_path)
    return (ds.id, ds.repo.get_hexsha())


def get_metadata_source():
    source = {
        "key_source_map": {},
        "sources": [
            {
                "source_name": "manual_addition",
                "source_version": "0.1.0",
                "source_time": datetime.now().timestamp(),
                "agent_email": get_gitconfig("user.name"),
                "agent_name": get_gitconfig("user.email"),
            }
        ],
    }
    return source


def new_meta_item(ds_path):
    ds = Dataset(ds_path)
    meta_item = {
        "type": "dataset",
        "dataset_id": ds.id,
        "dataset_version": ds.repo.get_hexsha(),
        "name": "",
        "metadata_sources": get_metadata_source(),
    }
    return meta_item


parser = argparse.ArgumentParser()
parser.add_argument(
    "dataset",
    help="Dataset for which metadata will be injected into the catalog",
    type=Path,
)
parser.add_argument("--funding", help="Add funding info", action="store_true")
args = parser.parse_args()

if not any((args.funding,)):
    # can be more
    parser.error("No options specified, nothing to do")

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

with tempfile.NamedTemporaryFile(mode="w+t") as f:
    json.dump(meta_item, f)
    f.seek(0)
    res = catalog("add", catalog_dir=catalog_dir, metadata=f.name)
