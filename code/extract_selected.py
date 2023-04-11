import argparse
import json
from pathlib import Path
from uuid import UUID

from datalad.api import (
    catalog,
    meta_extract,
)


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is UUID:
            return str(obj)
        return super.default(obj)


parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset to extract from")
parser.add_argument("output", type=Path, help="Extracted metadata file")
parser.add_argument("extractors", metavar="name", nargs="+", help="Extractors to use")
parser.add_argument(
    "--add-super",
    type=Path,
    metavar="cat",
    help="Add translated metadata to catalog and update super",
)

args = parser.parse_args()

# extract
with args.output.open("w") as json_file:
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

# translate
translated_name = f"{args.output.stem}.cat.jsonl"
translated_path = args.output.parent.joinpath(translated_name)

with translated_path.open("w") as json_file:
    for res in catalog("translate", metadata=args.output, return_type="generator"):
        assert res["status"] == "ok"  # crude check
        json.dump(res["translated_metadata"], json_file)
        json_file.write("\n")

# update catalog if requested
if args.add_super is not None:
    with translated_path.open() as json_file:
        first = json.loads(json_file.readline())
    catalog("add", catalog_dir=args.add_super, metadata=translated_path)
    catalog(
        "set-super",
        catalog_dir=args.add_super,
        dataset_id=first["dataset_id"],
        dataset_version=first["dataset_version"],
    )
