"""Write a template for dataset to project assignment

We need to attribute projects to datasets using tags. For most
datasets, this information needs to come from the outside. This
scripts creates a toml file with project IDs, into which the projects
can be manually entered.

"""

from argparse import ArgumentParser
from pathlib import Path

import tomli_w

from datalad_next.datasets import Dataset

parser = ArgumentParser()
parser.add_argument("superds", type=Path, help="Superdataset location")
args = parser.parse_args()

ds = Dataset(args.superds)
outfile = Path.cwd() / "inputs" / "project_tags.toml"

# quit early if file already exists
if outfile.is_file():
    print("Refusing to overwrite", outfile)
    exit()

info = {}
for sub in ds.subdatasets(result_renderer="disabled"):
    info[sub["gitmodule_datalad-id"]] = {
        "name": sub["gitmodule_name"],  # just for human-readability
        "project": "",
    }

# save
with outfile.open("wb") as f:
    tomli_w.dump(info, f)
