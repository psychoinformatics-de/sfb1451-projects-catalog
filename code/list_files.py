from pathlib import Path
import json
import subprocess

from multiprocessing.pool import ThreadPool


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


ds_path = Path("/tmp/my-dataset")


file_required_meta = {
    "type": "file",
    "dataset_id": None,
    "dataset_version": None,
    # "metadata_sources": None,
}


res = subprocess.run(["git", "ls-tree", "HEAD", "-r", "--name-only"],
                     cwd = ds_path,
                     capture_output=True,
                     text=True,
                     )

file_names = res.stdout.split("\n")
files_to_check = [(ds_path, fname) for fname in file_names]

results = ThreadPool(8).starmap(check_filename, files_to_check)

# non-parallel version
# results = [check_filename(f, ds_path) for f in file_names]

for i, result in enumerate(results):
    # todo: json.dump()
    print(file_required_meta | result)
    if i == 10:
        break
