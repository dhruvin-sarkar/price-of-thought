"""Record the live neuPrint schema for the spatial analysis and derive the descending/ascending connective set."""

import json

import numpy as np
import pandas as pd
from neuprint import fetch_roi_hierarchy

from pipeline.common import DATASET, RESULTS, get_client, markdown_table

# Properties the pipeline depends on, keyed by the role they play downstream.
REQUIRED_FIELDS = {
    "cell type": "type",
    "superclass (descending / ascending / sensory / motor)": "superclass",
    "soma position (voxels)": "somaLocation",
    "soma hemisphere": "somaSide",
    "nerve-root hemisphere (neurons without a CNS soma)": "rootSide",
    "per-ROI synapse counts": "roiInfo",
}
EXPECTED_VOXEL_NM = 8.0
DESCENDING_SUPERCLASS = "descending_neuron"
ASCENDING_SUPERCLASS = "ascending_neuron"
NECK_ROI = "CV"
COMPARTMENT_ROIS = {"brain": ("CentralBrain", "Optic(L)", "Optic(R)"), "vnc": ("VNC",)}
# Loose physical bounds for a Drosophila CNS; a unit error of 10x or 1000x falls far outside them.
MIN_AXIS_EXTENT_UM, MAX_AXIS_EXTENT_UM = 100.0, 2000.0
MIN_LONG_AXIS_UM = 700.0
CONNECTIVE_JSON = RESULTS / "connective_set.json"

TYPE_SUPERCLASS_QUERY = """\
MATCH (n:Neuron)
WHERE n.type IS NOT NULL
RETURN n.type AS type, n.superclass AS superclass, count(*) AS neurons
ORDER BY type, neurons DESC"""


def assign_type_superclass(rows: pd.DataFrame) -> pd.DataFrame:
    """Give each type the superclass held by most of its neurons (ties broken alphabetically).

    Args:
        rows: columns ``type``, ``superclass`` (may be null), ``neurons``.

    Returns:
        One row per type: ``type``, ``superclass``, ``neurons`` (all neurons of the type),
        ``majority_share`` (fraction of neurons carrying the assigned superclass).
    """
    rows = rows.assign(superclass=rows["superclass"].fillna("unannotated"))
    ranked = rows.sort_values(["type", "neurons", "superclass"], ascending=[True, False, True])
    top = ranked.drop_duplicates("type").set_index("type")
    total = rows.groupby("type")["neurons"].sum()
    return pd.DataFrame(
        {"superclass": top["superclass"], "neurons": total, "majority_share": top["neurons"] / total}
    ).reset_index()


def derive_connective_sets(types: pd.DataFrame) -> dict[str, list[str]]:
    """Sorted descending and ascending type names from per-type majority superclasses."""
    sets = {
        "descending": sorted(types.loc[types["superclass"] == DESCENDING_SUPERCLASS, "type"]),
        "ascending": sorted(types.loc[types["superclass"] == ASCENDING_SUPERCLASS, "type"]),
    }
    for name, members in sets.items():
        if not members:
            raise RuntimeError(f"The {name} connective set is empty")
    return sets


def load_connective_sets() -> dict[str, list[str]]:
    """Descending and ascending type names written by :func:`main`."""
    sets = json.loads(CONNECTIVE_JSON.read_text(encoding="utf-8"))
    return {"descending": sets["descending"], "ascending": sets["ascending"]}


def voxels_to_micrometers(values, voxel_nm: float = EXPECTED_VOXEL_NM) -> np.ndarray:
    """Convert voxel coordinates to micrometers."""
    return np.asarray(values, dtype=float) * voxel_nm / 1000.0


def check_physical_extent(extent_um: dict[str, float]) -> None:
    """Fail if the per-axis spatial extent is not plausible for a fly CNS in micrometers."""
    for axis, span in extent_um.items():
        if not MIN_AXIS_EXTENT_UM <= span <= MAX_AXIS_EXTENT_UM:
            raise RuntimeError(f"Soma extent along {axis} is {span:.0f} um, outside [{MIN_AXIS_EXTENT_UM}, {MAX_AXIS_EXTENT_UM}]")
    if max(extent_um.values()) < MIN_LONG_AXIS_UM:
        raise RuntimeError(f"Longest soma extent {max(extent_um.values()):.0f} um is too short to span brain and nerve cord")


def main() -> None:
    client = get_client()
    q = client.fetch_custom

    meta = q("MATCH (m:Meta) RETURN m.voxelSize AS voxelSize, m.voxelUnits AS voxelUnits").iloc[0]
    voxel_size = [float(v) for v in meta["voxelSize"]]
    if meta["voxelUnits"] != "nanometers" or voxel_size != [EXPECTED_VOXEL_NM] * 3:
        raise RuntimeError(f"Unexpected voxel size {voxel_size} {meta['voxelUnits']}")

    roi_names = set(client.fetch_datasets()[DATASET]["ROIs"])
    counts = q(
        "MATCH (n:Neuron) UNWIND keys(n) AS k WITH k WHERE NOT k CONTAINS '(' "
        "RETURN k AS property, count(*) AS non_null ORDER BY non_null DESC"
    )
    counts = counts[~counts["property"].isin(roi_names)]
    missing = set(REQUIRED_FIELDS.values()) - set(counts["property"])
    if missing:
        raise RuntimeError(f"Required neuron properties absent from {DATASET}: {sorted(missing)}")

    hierarchy = fetch_roi_hierarchy(include_subprimary=False, format="dict")["CNS"]
    top_level = sorted(hierarchy)
    expected_rois = {NECK_ROI, *COMPARTMENT_ROIS["brain"], *COMPARTMENT_ROIS["vnc"]}
    if not expected_rois <= set(top_level):
        raise RuntimeError(f"Expected top-level ROIs {sorted(expected_rois)} under CNS, found {top_level}")

    box = q(
        "MATCH (n:Neuron) WHERE n.type IS NOT NULL AND n.somaLocation IS NOT NULL RETURN "
        "min(n.somaLocation.x) AS xmin, max(n.somaLocation.x) AS xmax, min(n.somaLocation.y) AS ymin, "
        "max(n.somaLocation.y) AS ymax, min(n.somaLocation.z) AS zmin, max(n.somaLocation.z) AS zmax"
    ).iloc[0]
    extent_um = {a: float(voxels_to_micrometers(box[f"{a}max"] - box[f"{a}min"])) for a in "xyz"}
    check_physical_extent(extent_um)

    compartment_z = q(
        "MATCH (n:Neuron) WHERE n.type IS NOT NULL AND n.somaLocation IS NOT NULL "
        "AND n.superclass IN ['cb_intrinsic', 'vnc_intrinsic'] "
        "RETURN n.superclass AS superclass, count(*) AS neurons, avg(n.somaLocation.z) AS mean_z, "
        "min(n.somaLocation.z) AS min_z, max(n.somaLocation.z) AS max_z"
    )
    soma_coverage = q(
        "MATCH (n:Neuron) WHERE n.type IS NOT NULL "
        "RETURN n.superclass AS superclass, count(*) AS neurons, "
        "sum(CASE WHEN n.somaLocation IS NULL THEN 0 ELSE 1 END) AS with_soma ORDER BY neurons DESC"
    )
    soma_coverage["share_with_soma"] = (soma_coverage["with_soma"] / soma_coverage["neurons"]).round(3)

    types = assign_type_superclass(q(TYPE_SUPERCLASS_QUERY))
    sets = derive_connective_sets(types)
    members = sets["descending"] + sets["ascending"]
    confirmed = set(q(f"MATCH (n:Neuron) WHERE n.type IN {json.dumps(members)} RETURN DISTINCT n.type AS type")["type"])
    unconfirmed = set(members) - confirmed
    if unconfirmed:
        raise RuntimeError(f"{len(unconfirmed)} connective types not found in a live query: {sorted(unconfirmed)[:10]}")
    overlap = set(sets["descending"]) & set(sets["ascending"])
    if overlap:
        raise RuntimeError(f"Types assigned to both connective sets: {sorted(overlap)}")

    neck = q(
        "MATCH (n:Neuron) WHERE n.type IS NOT NULL "
        f"WITH n, n.roiInfo CONTAINS '\"{NECK_ROI}\"' AS in_neck "
        "RETURN n.superclass AS superclass, count(*) AS neurons, sum(CASE WHEN in_neck THEN 1 ELSE 0 END) AS neck_neurons, "
        "count(DISTINCT CASE WHEN in_neck THEN n.type END) AS neck_types ORDER BY neck_neurons DESC"
    )
    neck = neck[neck["neck_neurons"] > 0].reset_index(drop=True)
    neck_total = int(neck["neck_neurons"].sum())
    neck_connective = int(neck.loc[neck["superclass"].isin([DESCENDING_SUPERCLASS, ASCENDING_SUPERCLASS]), "neck_neurons"].sum())
    n_types = len(types)
    mixed = types[types["type"].isin(members) & (types["majority_share"] < 1)]

    RESULTS.mkdir(exist_ok=True)
    CONNECTIVE_JSON.write_text(
        json.dumps(
            {
                "dataset": DATASET,
                "descending_superclass": DESCENDING_SUPERCLASS,
                "ascending_superclass": ASCENDING_SUPERCLASS,
                "query": TYPE_SUPERCLASS_QUERY,
                **sets,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        f"# neuPrint schema: {DATASET}",
        "",
        "## Coordinates",
        "",
        f"The dataset `Meta` node gives voxel size {voxel_size} in `{meta['voxelUnits']}`. Soma positions "
        "(`somaLocation`) and synapse positions (`Synapse.location`) are stored in voxels, so every coordinate is "
        f"multiplied by {EXPECTED_VOXEL_NM:g} nm / 1000 = {EXPECTED_VOXEL_NM / 1000:g} µm per voxel.",
        "",
        "Sanity check: the somata of all typed neurons span "
        + ", ".join(f"{extent_um[a]:.0f} µm along {a}" for a in "xyz")
        + f". The long axis ({max(extent_um, key=extent_um.get)}) runs from the brain to the posterior end of the "
        "ventral nerve cord, about a millimetre, which is the expected scale for an adult fly CNS; a factor-of-1000 "
        "unit error would put these spans near 1 µm or 1 m.",
        "",
        "Brain and nerve-cord somata separate along z (voxels):",
        "",
        *markdown_table(compartment_z.round(0)),
        "",
        "## Fields used downstream",
        "",
        *[f"- {role}: `{prop}`" for role, prop in REQUIRED_FIELDS.items()],
        "",
        "## Soma positions by superclass (typed neurons)",
        "",
        "Sensory neurons have their cell bodies in the periphery, outside the imaged CNS, and so carry no "
        "`somaLocation`; their positions downstream come from synapse locations instead.",
        "",
        *markdown_table(soma_coverage),
        "",
        "## Connective set",
        "",
        f"Each type takes the `superclass` held by the majority of its neurons. Of {n_types} types:",
        "",
        f"- **Descending** (`{DESCENDING_SUPERCLASS}`, brain to nerve cord): {len(sets['descending'])} types.",
        f"- **Ascending** (`{ASCENDING_SUPERCLASS}`, nerve cord to brain): {len(sets['ascending'])} types.",
        "",
        "Every type name was confirmed in a second live query. "
        + (f"{len(mixed)} of these types contain some neurons with another superclass; the lowest majority share is "
           f"{mixed['majority_share'].min():.2f}." if len(mixed) else "Every connective type has a single superclass."),
        "",
        f"Cross-check against anatomy: of the {neck_total} typed neurons with synapses inside the neck connective ROI "
        f"(`{NECK_ROI}`), {neck_connective} ({neck_connective / neck_total:.1%}) are descending or ascending neurons. "
        "The remainder are listed below; sensory ascending neurons (peripheral somata, axons ascending through the "
        "neck) are the largest group and are kept out of the connective set because they have no CNS soma to place.",
        "",
        *markdown_table(neck),
        "",
        "## Top-level ROIs under CNS",
        "",
        *[f"- `{name}`" for name in top_level],
        "",
        "Compartments: "
        + "; ".join(f"{k} = {', '.join(f'`{r}`' for r in v)}" for k, v in COMPARTMENT_ROIS.items())
        + f". `{NECK_ROI}` belongs to neither.",
        "",
        "## Neuron properties",
        "",
        *markdown_table(counts.rename(columns={"non_null": "non-null neurons"})),
        "",
    ]
    (RESULTS / "schema.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        f"voxel {voxel_size} {meta['voxelUnits']}; extent (um) "
        + ", ".join(f"{a}={extent_um[a]:.0f}" for a in "xyz")
        + f"; descending {len(sets['descending'])}, ascending {len(sets['ascending'])} of {n_types} types; "
        f"neck neurons that are DN/AN: {neck_connective}/{neck_total}"
    )


if __name__ == "__main__":
    main()
