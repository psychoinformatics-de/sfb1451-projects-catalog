"""
datalad -f json meta-conduct conduct_pipelines/extract_files.json \
  traverser.top_level_dir=datasets/rdm-workshop \
  | jq -c '.["pipeline_data"]["result"]["metadata"][0]["metadata_record"]' >> output.json
"""

import argparse
import json
from pathlib import Path
from uuid import UUID

from datalad.api import(
    catalog,
    meta_conduct,
)

from dataladmetadatamodel.metadatapath import MetadataPath

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is UUID:
            return str(obj)
        if type(obj) is MetadataPath:
            return str(obj)
        return super().default(obj)

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset to extract from")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
args = parser.parse_args()

# extraction
results = meta_conduct(
    configuration=str(Path(__file__).parent.joinpath("file_level_pipeline.json")),
    arguments=[
        f"traverser.top_level_dir={args.dataset}",
    ],
    return_type="list",
)

# we assume it's a project's subdataset
ds_name = args.dataset.name
project_name = args.dataset.parent.name
extracted_path = args.outdir.joinpath(f"{project_name}_{ds_name}_files.jsonl")

# writing extracted data
with extracted_path.open("w") as json_file:

    for res in results:
        metadata = res["pipeline_data"]["result"]["metadata"]
        for md in metadata:
            # we expect just 1 metadata item per file, but we loop anyway
            assert md["state"] == "SUCCESS"  # crude check
            json.dump(md["metadata_record"], json_file, cls=MyEncoder)
            json_file.write("\n")

# TODO: translation
translated_name = f"{extracted_path.stem}.cat.jsonl"
translated_path = args.outdir.joinpath(translated_name)

with translated_path.open("w") as json_file:
    for res in catalog("translate", metadata=extracted_path, return_type="generator"):
        assert res["status"] == "ok"  # crude check
        json.dump(res["translated_metadata"], json_file)
        json_file.write("\n")

