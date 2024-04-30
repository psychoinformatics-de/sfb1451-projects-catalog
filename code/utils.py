import json
from uuid import UUID

from bs4 import BeautifulSoup
import requests


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is UUID:
            return str(obj)
        return super.default(obj)


def find_gin_url(ds):
    """Find a GIN URL in dataset siblings, return https"""
    for sibling in ds.siblings(result_renderer="disabled"):
        if sibling["name"] == "origin" and "gin.g-node.org" in sibling["url"]:
            if sibling["url"].startswith("https"):
                return (
                    sibling["url"]
                    if not sibling["url"].endswith(".git")
                    else sibling["url"][:-4]
                )
            elif sibling["url"].startswith("git@"):
                gin_url = sibling["url"].replace("git@", "https://")
                return gin_url if not gin_url.endswith(".git") else gin_url[:-4]
    return None


def find_gin_doi(ds):
    """Find GIN DOI on GIN's dataset page

    Gets html response and parses it.

    """
    ginurl = find_gin_url(ds)
    if ginurl is None:
        return None

    r = requests.get(ginurl)
    if not r.ok:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    tag = soup.find("div", class_="gin doinr")

    doi = f"https://doi.org/{tag.get_text()}" if tag is not None else None

    return doi
