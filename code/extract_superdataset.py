import argparse
import json
from pathlib import Path

from datalad.api import (
    catalog_add,
    catalog_set,
    catalog_translate,
    meta_extract,
)

from utils import MyEncoder, postprocess


parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Superdataset to extract from")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
parser.add_argument("-c", "--catalog", type=Path, help="Catalog to add metadata to")
args = parser.parse_args()

extracted_path = args.outdir.joinpath(f"{args.dataset.name}.jsonl")
translated_path = extracted_path.with_suffix(".cat.jsonl")

# extract
with extracted_path.open("w") as json_file:
    for extractor_name in ("metalad_core", "metalad_studyminimeta"):
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
        metadata_item = postprocess(res)
        json.dump(metadata_item, json_file)
        json_file.write("\n")

# update catalog if requested
if args.catalog is not None:
    catalog_add(
        catalog=args.catalog,
        metadata=translated_path,
        config_file=args.add_catalog / "config.json",
    )

    catalog_set(
        catalog=args.catalog,
        property="home",
        dataset_id=metadata_item["dataset_id"],
        dataset_version=metadata_item["dataset_version"],
        reckless="overwrite",
    )
