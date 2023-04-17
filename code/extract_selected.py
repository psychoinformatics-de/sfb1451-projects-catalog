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


def postprocess(result):
    """post-translation tweaks"""
    md = result["translated_metadata"]

    # try to split studyminimeta funding into name; identifier; description
    if md["metadata_sources"]["sources"][0]["source_name"] == "metalad_studyminimeta":
        funding = md["funding"]
        new_funding = []
        for fund_source in funding:
            if len(fund_parts := fund_source["name"].split(";")) == 3:
                new_funding.append(
                    {
                        "name": fund_parts[0].strip(),
                        "identifier": fund_parts[1].strip(),
                        "description": fund_parts[2].strip(),
                    }
                )
            else:
                new_funding.append(fund_source)
        md["funding"] = new_funding

    return md


parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset to extract from")
# parser.add_argument("output", type=Path, help="Extracted metadata file")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
parser.add_argument("extractors", metavar="name", nargs="+", help="Extractors to use")
parser.add_argument(
    "--add-super",
    type=Path,
    metavar="cat",
    help="Add translated metadata to catalog and update super",
)

args = parser.parse_args()

if args.add_super is None:
    # we assume it's a project's subdataset
    ds_name = args.dataset.name
    project_name = args.dataset.parent.name
    extracted_path = args.outdir.joinpath(f"{project_name}_{ds_name}.jsonl")
else:
    ds_name = args.dataset.name
    extracted_path = args.outdir.joinpath(f"{ds_name}.jsonl")

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

# translate
translated_name = f"{extracted_path.stem}.cat.jsonl"
translated_path = extracted_path.parent.joinpath(translated_name)

with translated_path.open("w") as json_file:
    for res in catalog("translate", metadata=extracted_path, return_type="generator"):
        assert res["status"] == "ok"  # crude check
        metadata_item = postprocess(res)
        json.dump(metadata_item, json_file)
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
