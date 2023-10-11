import argparse
import json
from pathlib import Path
from uuid import UUID

from datalad.api import (
    catalog_add,
    catalog_translate,
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
parser.add_argument("outdir", type=Path, help="Metadata output directory")
parser.add_argument("-c", "--catalog", type=Path, help="Catalog to add metadata to")
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
translated_name = f"{extracted_path.stem}.cat.jsonl"
translated_path = extracted_path.parent.joinpath(translated_name)

with translated_path.open("w") as json_file:
    for res in catalog_translate(metadata=extracted_path, catalog=None, return_type="generator"):
        assert res["status"] == "ok"  # crude check
        metadata_item = postprocess(res)
        json.dump(metadata_item, json_file)
        json_file.write("\n")

# update catalog if requested
if args.catalog is not None:
    catalog_add(
        catalog=args.catalog,
        metadata=translated_path,
        config_file=args.catalog / "config.json",
    )
