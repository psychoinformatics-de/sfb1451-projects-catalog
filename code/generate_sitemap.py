import argparse
from pathlib import Path

from datalad.api import (
    catalog_get,
)

base_url = "https://data.sfb1451.de/"
base_dataset_url = "https://data.sfb1451.de/#/dataset/"

def get_subdataset_urls(metadata, catalog_path):
    """"""
    urls = []
    for s in metadata.get("subdatasets",[]):
        s_id = s.get("dataset_id")
        s_v = s.get("dataset_version")
        if not s_id or not s_v:
            continue        
        res = catalog_get(
            catalog=catalog_path,
            property="metadata",
            dataset_id=s_id,
            dataset_version=s_v,
            result_renderer="disabled",
            return_type="item-or-list",
            on_failure="ignore",
        )
        sub_meta = res["output"]
        # only add subdataset to sitemap if it is in the catalog
        if sub_meta is not None:
            urls.append(get_dataset_url(s_id, s_v))
            if sub_meta.get("subdatasets",[]):
                urls += get_subdataset_urls(sub_meta, catalog_path)
    return urls


def get_dataset_url(dataset_id, dataset_version):
    """"""
    return base_dataset_url + dataset_id + "/" + dataset_version


def gen_sitemap(catalog_path):
    """"""
    res = catalog_get(
        catalog=catalog_path,
        property="home",
        result_renderer="disabled",
        return_type="item-or-list",
    )
    assert res["status"] == "ok"
    super_id = res["output"]["dataset_id"]
    super_version = res["output"]["dataset_version"]
    res = catalog_get(
        catalog=args.catalog,
        property="metadata",
        dataset_id=super_id,
        dataset_version=super_version,
        result_renderer="disabled",
        return_type="item-or-list",
    )
    assert res["status"] == "ok"
    supderds_meta = res["output"]

    urls = []
    urls.append(get_dataset_url(super_id, super_version))
    urls += get_subdataset_urls(supderds_meta, catalog_path)
    site_urls = list(set(urls))

    # Create sitemap file
    with open(Path(catalog_path) / 'sitemap.txt', 'w') as f:
        for u in site_urls:
            f.write(f"{u}\n")
    # Create robots file
    with open(Path(catalog_path) / 'robots.txt', 'w') as f:
        txt = f"Sitemap: {base_url}sitemap.txt"
        f.write(f"{txt}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path, help="Catalog for which to generate a sitemap")
    args = parser.parse_args()
    urls = gen_sitemap(args.catalog)
