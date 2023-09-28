import argparse
import json
from multiprocessing.pool import ThreadPool
from pathlib import Path
import subprocess

from datalad_next.datasets import Dataset

def check_filename(ds_path, fname):

    if fname == "":
        return None

    fp = ds_path / Path(fname)
    try:
        stat = fp.stat()
        return {"path": fname, "contentbytesize": stat.st_size}
    except FileNotFoundError:
        res = subprocess.run(
            ["git", "annex", "--json", "info", "--fast", "--bytes", fname],
            cwd = ds_path,
            capture_output=True,
            text=True,
        )
        out = json.loads(res.stdout)
        if out["success"]:
            return {"path": fname, "contentbytesize": int(out["size"])}


parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path, help="Dataset for which files will be listed")
parser.add_argument("outfile", type=Path, help="Json lines file for storing metadata")
args = parser.parse_args()


ds = Dataset(args.dataset)

file_required_meta = {
    "type": "file",
    "dataset_id": ds.id,
    "dataset_version": ds.repo.get_hexsha(),
    # "metadata_sources": None,
}

# list files with git ls-tree

res = subprocess.run(["git", "ls-tree", "HEAD", "-r", "--name-only"],
                     cwd = args.dataset,
                     capture_output=True,
                     text=True,
                     )

file_names = res.stdout.split("\n")
print(file_names)
files_to_check = [(args.dataset, fname) for fname in file_names]

# get file sizes

results = ThreadPool(8).starmap(check_filename, files_to_check)

# save outputs

with args.outfile.open("w") as json_file:
    for result in results:
        if result is not None:
            json.dump(file_required_meta | result, json_file)
            json_file.write("\n")
