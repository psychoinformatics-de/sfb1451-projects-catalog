import argparse
import json
from pathlib import Path, PurePath

from datalad_next.datasets import Dataset
from datalad_catalog.schema_utils import (
    get_metadata_item,
)


def transform_result(res):
    """Transform status result to catalog schema

    Keeps only type, path, and contentbytesize; ensures that the path
    is relative to dataset root.

    """
    return {
        "type": res["type"],
        "path": PurePath(res["path"]).relative_to(res["parentds"]).as_posix(),
        "contentbytesize": res["bytesize"],
    }


def is_file(res):
    """Check if result type is file"""
    return res["type"] == "file"


def list_files(ds_path):
    """Return generator of catalog-compliant file metadata"""
    ds = Dataset(ds_path)

    file_required_meta = get_metadata_item(
        item_type="file",
        dataset_id=ds.id,
        dataset_version=ds.repo.get_hexsha(),
        source_name="manual_addition",
        source_version="0.1.0",
        exclude_keys=["path"],
    )

    results = ds.status(
        annex="basic",
        result_renderer="disabled",
        result_filter=is_file,
        result_xfm=transform_result,
    )

    return (file_required_meta | result for result in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dataset", type=Path, help="Dataset for which files will be listed"
    )
    parser.add_argument(
        "outfile", type=Path, help="Json lines file for storing metadata"
    )
    args = parser.parse_args()

    with args.outfile.open("w") as json_file:
        for result in list_files(args.dataset):
            json.dump(result, json_file)
            json_file.write("\n")
