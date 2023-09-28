import argparse
import json
from multiprocessing.pool import ThreadPool
from pathlib import Path
import subprocess

from datalad_next.datasets import Dataset


def check_filename(ds_path, fname):
    """Report file size and relative path

    First checks the size with stat(). If that fails (presumably
    meaning a broken symlink, i.e. annexed file with content not
    available locally) uses git annex info on that file.

    Returns a dictionary with "path" and "contentbytesize" keys
    matching catalog schema.

    """
    if fname == "":
        return None

    fp = ds_path / Path(fname)
    try:
        stat = fp.stat()
        return {"path": fname, "contentbytesize": stat.st_size}
    except FileNotFoundError:
        res = subprocess.run(
            ["git", "annex", "--json", "info", "--fast", "--bytes", fname],
            cwd=ds_path,
            capture_output=True,
            text=True,
        )
        out = json.loads(res.stdout)
        if out["success"]:
            return {"path": fname, "contentbytesize": int(out["size"])}


def iter_tree(ds_path, n_threads=8):
    """Run git ls-tree; report file size and relative path"""
    res = subprocess.run(
        ["git", "ls-tree", "HEAD", "-r", "-z", "--name-only"],
        cwd=ds_path,
        capture_output=True,
        text=True,
    )
    file_names = res.stdout.split("\x00")
    files_to_check = [(ds_path, fname) for fname in file_names if fname != ""]

    results = ThreadPool(n_threads).starmap(check_filename, files_to_check)

    return results


parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset for which files will be listed")
parser.add_argument("outfile", type=Path, help="Json lines file for storing metadata")
args = parser.parse_args()

# create basic metadata item with dataset id and version
ds = Dataset(args.dataset)
file_required_meta = {
    "type": "file",
    "dataset_id": ds.id,
    "dataset_version": ds.repo.get_hexsha(),
    # "metadata_sources": None,
}

# list files and save metadata
results = iter_tree(args.dataset)
with args.outfile.open("w") as json_file:
    for result in results:
        if result is not None:
            json.dump(file_required_meta | result, json_file)
            json_file.write("\n")
