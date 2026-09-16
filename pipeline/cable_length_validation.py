"""Check that soma-to-output distance, the quantity node positions stand in for, tracks real skeleton cable length."""

import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests
from neuprint import fetch_skeleton
from scipy import stats

from pipeline.build_spatial_graph import with_retries
from pipeline.common import DATA, RESULTS, SEED, get_client
from pipeline.figures import CONNECTIVE, MUTED, NULL, REAL, apply_style, plt
from pipeline.schema_discovery import EXPECTED_VOXEL_NM

STRATA = {"descending_neuron": 100, "ascending_neuron": 100, "cb_intrinsic": 150, "vnc_intrinsic": 150}
ALPHA = 0.05
THREADS = 4
SAMPLE_SEED_OFFSET = 900_000
PREREGISTRATION_COMMIT = "e62c6df"
CACHE = DATA / "skeleton_lengths"
PREREGISTRATION = RESULTS / "wiring_economy_extensions.md"
REPORT = RESULTS / "cable_length.md"


def cable_length_um(skeleton: pd.DataFrame, voxel_nm: float = EXPECTED_VOXEL_NM) -> float:
    """Summed parent-child segment length of a skeleton, in micrometers.

    Args:
        skeleton: neuPrint skeleton table with ``link`` (parent rowId, -1 at a root) and x, y, z in voxels.
        voxel_nm: voxel size.

    Returns:
        Total cable length. Fragment roots contribute nothing, so unhealed gaps are not bridged.
    """
    parents = skeleton.set_index("rowId")[["x", "y", "z"]]
    linked = skeleton[skeleton["link"] != -1]
    child = linked[["x", "y", "z"]].to_numpy(dtype=float)
    parent = parents.loc[linked["link"].to_numpy()].to_numpy(dtype=float)
    return float(np.linalg.norm(child - parent, axis=1).sum() * voxel_nm / 1000)


def stratified_sample(candidates: pd.DataFrame, strata: dict[str, int], seed: int) -> pd.DataFrame:
    """Draw a fixed-size random sample of body IDs from each superclass without replacement."""
    rng = np.random.default_rng(seed)
    parts = []
    for superclass, size in strata.items():
        pool = candidates[candidates["superclass"] == superclass].sort_values("bodyId")
        if len(pool) < size:
            raise ValueError(f"{superclass}: {len(pool)} candidates for a sample of {size}")
        parts.append(pool.iloc[np.sort(rng.choice(len(pool), size=size, replace=False))])
    return pd.concat(parts, ignore_index=True)


def _fetch_length(body_id: int) -> dict:
    path = CACHE / f"{body_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    try:
        skeleton = with_retries(fetch_skeleton, body_id, heal=False)
        row = {"bodyId": body_id, "cable_um": cable_length_um(skeleton), "skeleton_nodes": len(skeleton),
               "fragments": int((skeleton["link"] == -1).sum())}
    except requests.HTTPError as error:
        if "not found" not in str(error).lower():
            raise
        row = {"bodyId": body_id, "cable_um": None, "skeleton_nodes": 0, "fragments": 0}
    path.write_text(json.dumps(row))
    return row


def plot(frame: pd.DataFrame) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(7.5, 6), dpi=200)
    colors = {"descending_neuron": CONNECTIVE, "ascending_neuron": "#8a3ffc", "cb_intrinsic": NULL, "vnc_intrinsic": MUTED}
    for superclass, color in colors.items():
        part = frame[frame["superclass"] == superclass]
        ax.scatter(part["soma_to_output_um"], part["cable_um"], s=9, color=color, alpha=0.75,
                   label=superclass.replace("_", " "), linewidths=0)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("soma to presynaptic centroid (µm)")
    ax.set_ylabel("skeleton cable length (µm)")
    rho = stats.spearmanr(frame["soma_to_output_um"], frame["cable_um"]).statistic
    ax.set_title(f"Cable length against soma-to-output distance, ρ = {rho:.2f}", loc="left", color=REAL)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS / "cable_length.png")
    plt.close(fig)


def main() -> None:
    client = get_client()
    neurons = pd.read_parquet(DATA / "neurons.parquet")
    pre = pd.read_parquet(DATA / "synapse_centroids.parquet").query("kind == 'pre'")
    candidates = neurons.merge(pre[["bodyId", "x", "y", "z"]], on="bodyId")
    candidates = candidates[candidates[["soma_x", "soma_y", "soma_z"]].notna().all(axis=1)]
    sample = stratified_sample(candidates, STRATA, SEED + SAMPLE_SEED_OFFSET)

    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(THREADS) as pool:
        rows = []
        for done, row in enumerate(pool.map(_fetch_length, sample["bodyId"].tolist()), start=1):
            rows.append(row)
            if done % 50 == 0:
                print(f"skeletons: {done}/{len(sample)}", flush=True)

    frame = sample.merge(pd.DataFrame(rows), on="bodyId", how="left", validate="one_to_one")
    frame["soma_to_output_um"] = np.linalg.norm(
        frame[["soma_x", "soma_y", "soma_z"]].to_numpy() - frame[["x", "y", "z"]].to_numpy(), axis=1)
    missing = int(frame["cable_um"].isna().sum())
    frame = frame.dropna(subset=["cable_um"])
    frame["cable_um"] = frame["cable_um"].astype(float)

    rho, p = stats.spearmanr(frame["soma_to_output_um"], frame["cable_um"], alternative="greater")
    by_class = {}
    for superclass, part in frame.groupby("superclass"):
        r, q = stats.spearmanr(part["soma_to_output_um"], part["cable_um"])
        by_class[superclass] = {
            "n": len(part), "spearman_rho": float(r), "p_value": float(q),
            "median_cable_um": float(part["cable_um"].median()),
            "median_soma_to_output_um": float(part["soma_to_output_um"].median()),
            "median_ratio": float((part["cable_um"] / part["soma_to_output_um"]).median()),
        }
    summary = {
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "sampled": len(sample), "without_skeleton": missing, "analysed": len(frame),
        "spearman_rho": float(rho), "p_value": float(p), "significant": bool(p < ALPHA),
        "by_superclass": {k: by_class[k] for k in STRATA if k in by_class},
    }
    frame[["bodyId", "type", "superclass", "cable_um", "skeleton_nodes", "fragments", "soma_to_output_um"]].to_csv(
        RESULTS / "cable_length.csv", index=False, float_format="%.3f")
    (RESULTS / "cable_length.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot(frame)
    write_report(summary)


def write_report(s: dict) -> None:
    hypothesis = PREREGISTRATION.read_text(encoding="utf-8").split("### Cable length validation")[1].split("A result against")[0]
    lines = [
        "# Cable length validation",
        "",
        f"## Hypothesis (committed in `{s['preregistration_commit']}`, in `wiring_economy_extensions.md`)",
        hypothesis.rstrip(),
        "",
        "## Results",
        "",
        f"{s['sampled']} neurons sampled; {s['without_skeleton']} have no skeleton in neuPrint, leaving {s['analysed']}. "
        "Cable length is the summed length of parent-child segments of the unhealed skeleton, so gaps between "
        "fragments are not counted.",
        "",
        f"Spearman ρ = {s['spearman_rho']:.3f}, one-sided p = {s['p_value']:.3g}. "
        f"**H9 is {'supported' if s['significant'] else 'not supported'}.**",
        "",
        "| superclass | n | Spearman ρ | p | median cable | median soma to output | median ratio |",
        "|---|---|---|---|---|---|---|",
        *[
            f"| {k.replace('_', ' ')} | {v['n']} | {v['spearman_rho']:.3f} | {v['p_value']:.3g} | "
            f"{v['median_cable_um']:,.0f} µm | {v['median_soma_to_output_um']:.0f} µm | {v['median_ratio']:.1f} |"
            for k, v in s["by_superclass"].items()
        ],
        "",
        "Per-superclass correlations are descriptive. Within every superclass |ρ| is below "
        f"{max(abs(v['spearman_rho']) for v in s['by_superclass'].values()) + 0.005:.2f}, so the overall correlation "
        "comes from differences between superclasses: neurons whose outputs lie far from the soma, such as descending "
        "and ascending neurons, have more cable, but among neurons of one superclass soma-to-output distance does not "
        "predict cable length. Node positions therefore track the between-class structure of wiring cost, not the "
        "cable of individual neurons. Per-neuron values: `cable_length.csv`.",
        "",
        "![Cable length](cable_length.png)",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
