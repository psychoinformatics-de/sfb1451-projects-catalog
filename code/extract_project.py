"""Extract metadata from a project's superdataset

Conducts project_extract_pipeline.json and translates the
result. Extracted and translated metadata are written to the specified
directory as two separate files (project.jsonl, project.cat.jsonl).

"""

import argparse
import json
from pathlib import Path
from uuid import UUID

from datalad.api import(
    catalog,
    meta_conduct,
)

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is UUID:
            return str(obj)
        return super.default(obj)


# allow manual specification
parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset to extract from")
parser.add_argument("outdir", type=Path, help="Metadata output directory")
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
    for res in catalog("translate", metadata=extracted_path, return_type="generator"):
        assert res["status"] == "ok"  # crude check
        json.dump(res["translated_metadata"], json_file)
        json_file.write("\n")

