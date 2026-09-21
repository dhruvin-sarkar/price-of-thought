"""Check the site's committed data against a fresh assembly of it from the results."""

import json

import pandas as pd

from export.build_static_json import site_data
from pipeline.common import RESULTS, WEB_DATA
from verify.common import close, read_json, result_json, run

# What the scene header carries for each neuropil, with the value it falls back to for one the atlas omits.
ATLAS_FIELDS = {"compartment": "brain", "types": 0, "wire_um": 0.0, "wire_share": 0.0, "cost_ratio": None}
SHOWN = 5


def differences(committed, rebuilt, path: str = "") -> list[str]:
    """Paths at which two payloads disagree, descending only into the parts that match in shape."""
    if isinstance(committed, dict) and isinstance(rebuilt, dict):
        only = sorted(set(committed) ^ set(rebuilt))
        return [f"{path}.{key} on one side only" for key in only] + [
            d for key in sorted(set(committed) & set(rebuilt))
            for d in differences(committed[key], rebuilt[key], f"{path}.{key}")]
    if isinstance(committed, list) and isinstance(rebuilt, list):
        if len(committed) != len(rebuilt):
            return [f"{path} holds {len(committed)} entries, the results give {len(rebuilt)}"]
        return [d for i, (c, r) in enumerate(zip(committed, rebuilt)) for d in differences(c, r, f"{path}[{i}]")]
    return [] if close(committed, rebuilt) else [f"{path}: {committed!r} against {rebuilt!r}"]


def check() -> str:
    site = WEB_DATA / "site.json"
    assert site.exists(), "web/public/data/site.json is missing; run make export"
    committed = read_json(site)
    rebuilt = site_data(pd.read_csv(RESULTS / "connective_price.csv"))
    drift = differences(committed, rebuilt)
    more = f" and {len(drift) - SHOWN} more" if len(drift) > SHOWN else ""
    assert not drift, f"site.json does not match the results; run make export: {'; '.join(drift[:SHOWN])}{more}"

    # scene.json's geometry needs the neuPrint cache and the meshes; its neuropil table is the part holding results.
    scene = read_json(WEB_DATA / "scene.json")
    atlas = {row["neuropil"]: row for row in result_json("wire_atlas.json")["neuropils"]}
    stale = [row["name"] for row in scene["neuropils"]
             if not close({k: row[k] for k in ATLAS_FIELDS},
                          {k: atlas.get(row["name"], {}).get(k, d) for k, d in ATLAS_FIELDS.items()})]
    assert not stale, f"scene.json differs from wire_atlas.json at: {', '.join(stale)}"

    sections = len(committed)
    values = len(json.dumps(committed, separators=(",", ":")))
    return (f"site.json rebuilds from the results value for value ({sections} sections, {values / 1e3:.0f} kB); "
            f"{len(scene['neuropils'])} neuropils in scene.json match the atlas")


if __name__ == "__main__":
    run(check)
