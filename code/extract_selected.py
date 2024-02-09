import argparse
import json
from pathlib import Path

import tomli

from datalad.api import (
    catalog_add,
    catalog_translate,
    meta_extract,
)
from datalad_catalog.schema_utils import get_metadata_item
from datalad_next.datasets import Dataset

from list_files import list_files
from utils import MyEncoder, postprocess

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset to extract from")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
parser.add_argument("-c", "--catalog", type=Path, help="Catalog to add metadata to")
parser.add_argument("--files", action="store_true", help="Also list files")
parser.add_argument(
    "--filename",
    help="Use this file name instead of deriving from folder names",
)
parser.add_argument("extractors", metavar="name", nargs="+", help="Extractors to use")

args = parser.parse_args()

# obtain or generate name for metadata file
if args.filename is not None:
    extracted_path = args.outdir.joinpath(args.filename)
else:
    # we assume it's a project's subdataset
    ds_name = args.dataset.name
    project_name = args.dataset.parent.name
    extracted_path = args.outdir.joinpath(f"{project_name}_{ds_name}.jsonl")

# extract
with extracted_path.open("w") as json_file:
    for extractor_name in args.extractors:
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
translated_path = extracted_path.with_suffix(".cat.jsonl")

with translated_path.open("w") as json_file:
    for res in catalog_translate(
        metadata=extracted_path, catalog=None, return_type="generator"
    ):
        assert res["status"] == "ok"  # crude check
        metadata_item = postprocess(res)
        json.dump(metadata_item, json_file)
        json_file.write("\n")

# see if there's some manual additions
ds = Dataset(args.dataset)
with open(Path(__file__).parent / "manually_entered.toml", "rb") as f:
    manually_entered = tomli.load(f)

if (additional := manually_entered["additional"].get(ds.id)) is not None:
    basic_item = get_metadata_item(
        item_type="dataset",
        dataset_id=ds.id,
        dataset_version=ds.repo.get_hexsha(),
        source_name="manual_addition",
        source_version="0.1.0",
    )
    handcrafted_item = basic_item | additional
    with translated_path.open("w") as json_file:
        json.dump(handcrafted_item, json_file)
        json_file.write("\n")


# extract file list if requested
if args.files:
    files_stem = f"{extracted_path.stem}_files"
    files_path = extracted_path.with_stem(files_stem).with_suffix(".cat.jsonl")
    with files_path.open("w") as json_file:
        for metadata_item in list_files(args.dataset):
            json.dump(metadata_item, json_file)
            json_file.write("\n")

# update catalog if requested
if args.catalog is not None:
    catalog_add(
        catalog=args.catalog,
        metadata=translated_path,
        config_file=args.catalog / "config.json",
    )

    if args.files:
        catalog_add(
            catalog=args.catalog,
            metadata=files_path,
            config_file=args.catalog / "config.json",
        )
