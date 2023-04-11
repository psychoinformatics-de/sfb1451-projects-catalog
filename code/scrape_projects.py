import argparse
from pathlib import Path
import re

from bs4 import BeautifulSoup
import requests
from ruamel.yaml import YAML

# a naive name regex that splits into first, mid (optional) and last
name_regex = re.compile(
    r"^(?:[Pp]rof\.{0,1} )?(?:[Dd]r\. )*(?P<first>[\w-]+) (?P<mid>[\w.-]+ )?(?P<last>[\w-]+)$"
)
# allow exceptions to override how names are split into parts
x_path = Path(__file__).parent.joinpath("exceptions.yaml")
if x_path.is_file():
    yaml = YAML(typ="safe")
    name_exceptions = yaml.load(x_path)
else:
    name_exceptions = {}

def split_name(person_str):
    """Reverse-engineer cff name components from full name"""
    global name_regex
    global name_exceptions

    if (predefined := name_exceptions.get(person_str)) is not None:
        return predefined
    match = re.match(name_regex, person_str)
    if match is None:
        breakpoint()
    person = {
        "given-names": match.group("first"),
        "family-names": match.group("last"),
    }
    if match.group("mid") is not None:
        mid = match.group("mid").rstrip()
        if mid in ("von", "van"):
            person["name-particle"] = mid
        else:
            person["given-names"] = " ".join([person["given-names"], mid])
    return person

def parse_project(url):
    """Parse project website into CFF dictionary"""
    global name_regex
    
    request = requests.get(url)
    soup = BeautifulSoup(request.text, 'html.parser')

    h3 = soup.find_all('h3')

    if re.match(name_regex, h3[1].text.rstrip()) is not None:
        # typically only the first h3 is the project title
        title = h3[0].text
        people = [tag.text.rstrip() for tag in h3[1:]]
    else:
        # but we've seen exceptions
        title = h3[0].text + " " + h3[1].text
        people = [tag.text.rstrip() for tag in h3[2:]]

    promo_description = soup.find(
        name="div",
        attrs={"class": "et_pb_promo_description"},
    )

    citation = {
        "title": title,
        "authors": [split_name(person) for person in people],
        "abstract": promo_description.text.rstrip(),
        "cff-version": "1.2.0",
        "message": "Generated with data scraped from crc1451.uni-koeln.de",
    }

    return citation

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("base_dir", type=Path)
args = parser.parse_args()

# Get a list of projects and their urls (there are irregularities)
home_url = "https://www.crc1451.uni-koeln.de"
request = requests.get(home_url)
soup = BeautifulSoup(request.text, 'html.parser')

base_dir = args.base_dir

nav = soup.find("div", {"id": "et-top-navigation"})
all_links = nav.find_all("a")
for tag in all_links:
    if re.match("[ABCXZ]0[1-9]|INF|MGK|Dr\. \w+$", tag.text):
        project = tag.text.replace("Dr. ", "JRG_")  # Junior Research Group
        page_url = tag.get("href")

        citation = parse_project(page_url)

        target_path = base_dir / project / "auto-pub-dataset" / "CITATION.cff"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        yaml.dump(citation, target_path)
