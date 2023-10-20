import json
from uuid import UUID


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) is UUID:
            return str(obj)
        return super.default(obj)


def postprocess(result):
    """post-translation tweaks"""
    md = result["translated_metadata"]

    # try to split studyminimeta funding into name; identifier; description
    if md["metadata_sources"]["sources"][0]["source_name"] == "metalad_studyminimeta":
        funding = md["funding"]
        new_funding = []
        for fund_source in funding:
            if len(fund_parts := fund_source["name"].split(";")) == 3:
                new_funding.append(
                    {
                        "name": fund_parts[0].strip(),
                        "identifier": fund_parts[1].strip(),
                        "description": fund_parts[2].strip(),
                    }
                )
            else:
                new_funding.append(fund_source)
        md["funding"] = new_funding

    return md
