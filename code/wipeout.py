"""Wipe out metadata

This code will remove metadata for all current version of 1st level
subdatasets of a given dataset.

"""

from argparse import ArgumentParser
from pathlib import Path

from datalad_next.datasets import Dataset
from datalad.api import catalog_remove

parser = ArgumentParser()
parser.add_argument("dataset", type=Path)
parser.add_argument("catalog", type=Path)
args = parser.parse_args()

ds = Dataset(args.dataset)

for subds in ds.subdatasets(result_renderer="disabled"):
    catalog_remove(
        catalog=args.catalog,
        dataset_id=subds["gitmodule_datalad-id"],
        dataset_version=subds["gitshasum"],
        reckless=True,
    )
