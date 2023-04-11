import argparse
import json
from pathlib import Path
from pprint import pprint
import re
import subprocess
import warnings

from bs4 import BeautifulSoup
from habanero import Crossref
import requests
from ruamel.yaml import YAML


def meta_item_to_str(item):
    """Represent crossref metadata as title & doi string"""
    title = item.get("title", [""])[0]
    doi = item.get("DOI")
    return f"{title} (doi: {doi})"


def sanitize_title(item):
    """Create name from sanitized title

    Keeps word characters, " ", "-"

    """
    title = item.get("title")[0]
    s_title = re.sub(r"[^\w \-]", "", title)
    if len(s_title) > 144:
        # nice number to stay well below 255 bytes (ext4 limit)
        s_title = s_title[:144].rstrip()
    return s_title


def check_ratings(items, close=0.75, almost=0.9):
    """Print warning if ratings are close, return one item

    If two ratings are almost the same, but the first item is a
    preprint and the second is not, returns the latter.

    If the first item found is a "peer-review" (happened for an author
    response), it is taken out of consideration.

    Otherwise, returns the first (i.e. higher-rated) item.

    """
    if len(items) < 2:
        return items[0]

    scores = tuple(item["score"] for item in items)
    similarity = scores[1] / scores[0]

    if similarity > close:
        print(
            f"ATTN: Similar scores ({round(similarity, 2)}) for",
            meta_item_to_str(items[0]),
            "and",
            meta_item_to_str(items[1]),
        )
        if items[0]["type"] == "peer-review":
            print("The former is a peer review, discarding")
            return check_ratings(items[1:], close, almost)
    if (
        similarity >= almost
        and items[0].get("subtype") == "preprint"
        and items[1].get("type") == "journal-article"
    ):
        print("The former is a preprint, taking the latter as it is a journal article")
        return items[1]
    return items[0]


parser = argparse.ArgumentParser()
parser.add_argument("base_dir", type=Path)
args = parser.parse_args()

# Scrape the publications page
page_url = "https://www.crc1451.uni-koeln.de/index.php/intern-2/"
request = requests.get(page_url)
soup = BeautifulSoup(request.text, "html.parser")

headings = soup.find_all(re.compile("h[35]"))

papers = {}
project = None

for h in headings:
    if len(h.text) == 0:
        continue
    if h.name == "h3":
        project = h.text
    else:
        paper = h.text.split("|")[0].replace("\xa0", " ").rstrip()
        if project in papers:
            papers[project].append(paper)
        else:
            papers[project] = [paper]

paper_count = sum([len(proj_papers) for proj_papers in papers.values()])
print(f"Found {paper_count} papers")

# Now, feed the papers into CrossRef API
# try to use git config email, so we can get into "polite" pool
email = (
    subprocess.run(["git", "config", "user.email"], capture_output=True)
    .stdout.decode()
    .rstrip()
)
if email != "":
    print(f"Querrying crossref as {email}")
    cr = Crossref(mailto=email)
else:
    cr = Crossref()

base_dir = args.base_dir

for project in papers.keys():

    target_dir = base_dir / project / "auto-pub-dataset" / "publications"
    target_dir.mkdir(parents=True, exist_ok=True)

    for paper in papers[project]:
        print("Querying", paper.split(",")[-1])

        try:

            response = cr.works(
                query_bibliographic=paper,
                limit=3,
            )
            if response["status"] != "ok":
                warnings.warn("Response status was not ok")

            items = response["message"]["items"]
            best_item = check_ratings(items)

            file_path = target_dir / (sanitize_title(best_item) + ".crossref.json")
            with file_path.open("w") as f:
                json.dump(best_item, f)

        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")
            print(f"Query: {paper}")
