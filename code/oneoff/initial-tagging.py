"""Create project-tags to be added to the catalog

We need to attribute projects to datasets using tags. We store this
information in a toml file. To avoid re-extracting all datasets
already added to the catalog, we shall add all tags separately, at
first. This script outputs catalog-compliant metadata, ready to be
added.

"""

from argparse import ArgumentParser
import json
from pathlib import Path

import tomli

from datalad_next.datasets import Dataset
from datalad_catalog.schema_utils import get_metadata_item

parser = ArgumentParser()
parser.add_argument("superds", type=Path, help="Superdataset location")
args = parser.parse_args()

ds = Dataset(args.superds)
infile = Path.cwd() / "inputs" / "project_tags.toml"
outfile = Path.cwd() / "metadata" / "initial_tags.jsonl"

with infile.open("rb") as f:
    info = tomli.load(f)

metadata_items = []

for sub in ds.subdatasets(result_renderer="disabled"):
    try:
        sub_info = info[sub["gitmodule_datalad-id"]]
    except KeyError:
        print("Could not find entry for", sub)
        continue

    project = sub_info["project"]
    tags = [project] if isinstance(project, str) else project

    metadata_items.append(
        get_metadata_item(
            item_type="dataset",
            dataset_id=sub["gitmodule_datalad-id"],
            dataset_version=sub["gitshasum"],
            source_name="manual_addition",
            source_version="0.1.0",
        )
        | {"keywords": tags}
    )

with outfile.open("w") as json_file:
    for item in metadata_items:
        json.dump(item, json_file)
        json_file.write("\n")
