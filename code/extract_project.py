"""Extract metadata from a project's superdataset

Conducts project_extract_pipeline.json and translates the
result. Extracted and translated metadata are written to the specified
directory as two separate files (project.jsonl, project.cat.jsonl).

"""

import argparse
import json
from pathlib import Path

import tomli

from datalad.api import (
    catalog_add,
    catalog_translate,
    meta_conduct,
)
from datalad_catalog.schema_utils import get_metadata_item
from datalad_next.datasets import Dataset

from utils import MyEncoder

# allow manual specification
parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset to extract from")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
parser.add_argument("-c", "--catalog", type=Path, help="Catalog to add metadata to")
args = parser.parse_args()

# extraction
res = meta_conduct(
    configuration=str(Path(__file__).parent.joinpath("project_extract_pipeline.json")),
    arguments=[
        f"traverser.top_level_dir={args.dataset}",
    ],
    return_type="item-or-list",
)

metadata = res["pipeline_data"]["result"]["metadata"]

extracted_path = args.outdir.joinpath(f"{args.dataset.name}.jsonl")

with extracted_path.open("w") as json_file:
    for md in metadata:
        assert md["state"] == "SUCCESS"  # crude check
        json.dump(md["metadata_record"], json_file, cls=MyEncoder)
        json_file.write("\n")

# translation
translated_name = f"{extracted_path.stem}.cat.jsonl"
translated_path = args.outdir.joinpath(translated_name)

with translated_path.open("w") as json_file:
    for res in catalog_translate(
        metadata=extracted_path, catalog=None, return_type="generator"
    ):
        print(res)
        assert res["status"] == "ok"  # crude check
        json.dump(res["translated_metadata"], json_file)
        json_file.write("\n")

# injection
with open(Path(__file__).parent / "manually_entered.toml", "rb") as f:
    manually_entered = tomli.load(f)

ds = Dataset(args.dataset)
handcrafted_item = get_metadata_item(
    item_type="dataset",
    dataset_id=ds.id,
    dataset_version=ds.repo.get_hexsha(),
    source_name="manual_addition",
    source_version="0.1.0",
)

project_name = args.dataset.name  # asume dataset.tld = project name
if (keywords := manually_entered["keywords"].get(project_name)) is not None:
    handcrafted_item["keywords"] = keywords

sfb_grant = manually_entered["funding"]["sfb1451"]
project_grant = manually_entered["funding"].get(project_name)

handcrafted_item["funding"] = (
    [sfb_grant, project_grant] if project_grant is not None else [sfb_grant]
)

with translated_path.open("a") as json_file:
    json.dump(handcrafted_item, json_file)
    json_file.write("\n")

# optional addition
if args.catalog is not None:
    catalog_add(
        catalog=args.catalog,
        metadata=translated_path,
        config_file=Path(__file__).with_name("superds-config.json"),
    )
