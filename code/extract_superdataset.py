import argparse
import json
from pathlib import Path

import tomli

from datalad.api import (
    catalog_add,
    catalog_set,
    catalog_translate,
    meta_extract,
)
from datalad_catalog.schema_utils import get_metadata_item
from datalad_next.datasets import Dataset

from utils import MyEncoder


parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Superdataset to extract from")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
parser.add_argument("-c", "--catalog", type=Path, help="Catalog to add metadata to")
args = parser.parse_args()

extracted_path = args.outdir.joinpath(f"{args.dataset.name}.jsonl")
translated_path = extracted_path.with_suffix(".cat.jsonl")

# extract
with extracted_path.open("w") as json_file:
    for extractor_name in ("metalad_core", "we_cff"):
        res = meta_extract(
            extractorname=extractor_name,
            dataset=args.dataset,
            result_renderer="disabled",
            return_type="item-or-list",
        )
        assert res["status"] == "ok"
        json.dump(res["metadata_record"], json_file, cls=MyEncoder)
        json_file.write("\n")


# translate + postprocess
with translated_path.open("w") as json_file:
    for res in catalog_translate(
        metadata=extracted_path,
        catalog=None,
        return_type="generator",
        result_renderer="disabled",
    ):
        assert res["status"] == "ok"  # crude check
        metadata_item = res["translated_metadata"]

        # actually let's ignore all funding and add manually later
        _ = metadata_item.pop("funding", None)

        json.dump(metadata_item, json_file)
        json_file.write("\n")


# inject (make manual additions)
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
handcrafted_item["license"] = manually_entered["license"]["superdataset"]
handcrafted_item["funding"] = [manually_entered["funding"]["sfb1451"]]

with translated_path.open("a") as json_file:
    json.dump(handcrafted_item, json_file)
    json_file.write("\n")


# update catalog if requested
if args.catalog is not None:
    catalog_add(
        catalog=args.catalog,
        metadata=translated_path,
        config_file=Path(__file__).with_name("superds-config.json"),
    )

    catalog_set(
        catalog=args.catalog,
        property="home",
        dataset_id=metadata_item["dataset_id"],
        dataset_version=metadata_item["dataset_version"],
        reckless="overwrite",
    )
