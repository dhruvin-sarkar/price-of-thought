"""Compare the wiring budget and the internal placement economy of the left and right copy of each neuropil."""

import json
import re

import numpy as np
import pandas as pd

from pipeline.common import RESULTS, SEED, markdown_table
from pipeline.figures import CONNECTIVE, INK_SECONDARY, MUTED, REAL, apply_style, plt
from pipeline.rewiring import empirical_p_value_lower

PERMUTATIONS = 1000
NULL_SEED_OFFSET = 150_000
EXTREMES = 10
ATLAS = RESULTS / "wire_atlas.json"
REPORT = RESULTS / "wire_symmetry.md"
SIDE = re.compile(r"^(.*)\(([LR])\)$")


def split_side(name: str) -> tuple[str, str | None]:
    """Neuropil name split into its stem and its trailing hemisphere suffix.

    Args:
        name: neuropil name as published, for example ``LegNp(T2)(R)``.

    Returns:
        The stem and ``"L"`` or ``"R"``; the whole name and None for a name without a suffix.
    """
    match = SIDE.match(name)
    return (match.group(1), match.group(2)) if match else (name, None)


def pair_up(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Sort neuropil rows into left-right pairs, midline structures and sides without a partner.

    Args:
        rows: the ``neuropils`` rows of the wire atlas.

    Returns:
        The pairs, each holding the stem and both sides' rows; the rows with no hemisphere suffix; and the
        rows whose opposite side is absent. Pairs are ordered by the wire the two sides hold together.
    """
    sided: dict[str, dict[str, dict]] = {}
    midline = []
    for row in rows:
        stem, side = split_side(row["neuropil"])
        if side is None:
            midline.append(row)
        else:
            sided.setdefault(stem, {})[side] = row
    pairs = [{"neuropil": stem, "left": s["L"], "right": s["R"]} for stem, s in sided.items() if len(s) == 2]
    unpaired = [next(iter(s.values())) for s in sided.values() if len(s) == 1]
    pairs.sort(key=lambda p: -(p["left"]["wire_um"] + p["right"]["wire_um"]))
    return pairs, midline, unpaired


def pair_rows(pairs: list[dict]) -> list[dict]:
    """Both sides' wire, share, cell types and internal cost ratio for every pair, with the log ratio."""
    rows = []
    for pair in pairs:
        left, right = pair["left"], pair["right"]
        row = {
            "neuropil": pair["neuropil"],
            "compartment": left["compartment"],
            "types_left": left["types"],
            "types_right": right["types"],
            "wire_left_um": left["wire_um"],
            "wire_right_um": right["wire_um"],
            "wire_share_left": left["wire_share"],
            "wire_share_right": right["wire_share"],
            "log_ratio": round(float(np.log(left["wire_um"] / right["wire_um"])), 4),
        }
        if "cost_ratio" in left and "cost_ratio" in right:
            row |= {"cost_ratio_left": left["cost_ratio"], "cost_ratio_right": right["cost_ratio"],
                    "cost_ratio_difference": round(left["cost_ratio"] - right["cost_ratio"], 4)}
        rows.append(row)
    return rows


def sign_flip_null(values: np.ndarray, seed: int, permutations: int = PERMUTATIONS) -> np.ndarray:
    """Mean of ``values`` with each entry's sign flipped at random, the null of no systematic side bias."""
    rng = np.random.default_rng(seed)
    return np.array([float((values * rng.choice([-1.0, 1.0], size=len(values))).mean())
                     for _ in range(permutations)])


def repairing_null(left: np.ndarray, right: np.ndarray, seed: int,
                   permutations: int = PERMUTATIONS) -> np.ndarray:
    """Mean absolute log ratio when each left neuropil is matched to a right neuropil chosen at random."""
    rng = np.random.default_rng(seed)
    return np.array([float(np.abs(np.log(left / right[rng.permutation(len(right))])).mean())
                     for _ in range(permutations)])


def two_sided_p(observed: float, null: np.ndarray) -> float:
    """Share of the null at least as far from zero as the observed value, with the +1 correction."""
    return float((1 + np.sum(np.abs(null) >= abs(observed))) / (1 + len(null)))


def bias_test(values: np.ndarray, seed: int, permutations: int = PERMUTATIONS) -> dict:
    """Test the mean of a per-pair left-minus-right quantity against a sign-flip null."""
    null = sign_flip_null(values, seed, permutations)
    observed = float(values.mean())
    # A sign-flip null has no spread only when every pair is exactly in balance, and then the mean is zero too.
    sd = float(null.std(ddof=1))
    return {
        "pairs": int(len(values)),
        "mean": round(observed, 4),
        "mean_absolute": round(float(np.abs(values).mean()), 4),
        "median_absolute": round(float(np.median(np.abs(values))), 4),
        "max_absolute": round(float(np.abs(values).max()), 4),
        "null_sd": round(sd, 4),
        "z_score": round(observed / sd, 2) if sd else 0.0,
        "p_value": round(two_sided_p(observed, null), 6),
        "permutations": permutations,
    }


def symmetry(atlas: dict) -> dict:
    """Hemisphere symmetry of the wiring budget and of internal placement economy, pair by pair."""
    pairs, midline, unpaired = pair_up(atlas["neuropils"])
    rows = pair_rows(pairs)
    total = atlas["totals"]["total_wire_um"]

    log_ratio = np.array([r["log_ratio"] for r in rows])
    left = np.array([r["wire_left_um"] for r in rows])
    right = np.array([r["wire_right_um"] for r in rows])
    seed = SEED + NULL_SEED_OFFSET
    wire = bias_test(log_ratio, seed)
    scrambled = repairing_null(left, right, seed + 1)
    observed_spread = float(np.abs(log_ratio).mean())
    wire |= {
        "repaired_null_mean": round(float(scrambled.mean()), 4),
        "repaired_null_sd": round(float(scrambled.std(ddof=1)), 4),
        "repaired_n_at_or_below_observed": int((scrambled <= observed_spread).sum()),
        "repaired_p_value": round(empirical_p_value_lower(observed_spread, scrambled), 6),
    }

    priced = [r for r in rows if "cost_ratio_difference" in r]
    cost = bias_test(np.array([r["cost_ratio_difference"] for r in priced]), seed + 2) if priced else None

    def budget(group: list[dict]) -> dict:
        return {"neuropils": len(group), "wire_um": round(sum(r["wire_um"] for r in group), 1),
                "wire_share": round(sum(r["wire_um"] for r in group) / total, 4)}

    paired_wire = float(left.sum() + right.sum())
    return {
        "pairs": rows,
        "midline": [{"neuropil": r["neuropil"], "compartment": r["compartment"], "types": r["types"],
                     "wire_um": r["wire_um"], "wire_share": r["wire_share"]} for r in midline],
        "unpaired_sides": [{"neuropil": r["neuropil"], "compartment": r["compartment"], "types": r["types"],
                            "wire_um": r["wire_um"], "wire_share": r["wire_share"]} for r in unpaired],
        "wire_asymmetry": wire,
        "cost_ratio_asymmetry": cost,
        "totals": {
            "neuropils": len(atlas["neuropils"]),
            "paired": {"neuropils": 2 * len(rows), "wire_um": round(paired_wire, 1),
                       "wire_share": round(paired_wire / total, 4)},
            "midline": budget(midline),
            "unpaired_sides": budget(unpaired),
            "total_wire_um": total,
            "permutations": PERMUTATIONS,
            "seed": seed,
        },
    }


def figure(result: dict, path) -> None:
    """Each pair's two sides against each other, and the pairs whose sides differ most."""
    apply_style()
    rows = result["pairs"]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.0))

    left = np.array([r["wire_left_um"] for r in rows])
    right = np.array([r["wire_right_um"] for r in rows])
    span = [min(left.min(), right.min()) * 0.6, max(left.max(), right.max()) * 1.6]
    axes[0].plot(span, span, color=MUTED, linestyle="--", linewidth=1)
    for factor in (2.0, 0.5):
        axes[0].plot(span, [v * factor for v in span], color=MUTED, linestyle=":", linewidth=0.8)
    for compartment, color in (("brain", REAL), ("vnc", CONNECTIVE)):
        keep = [i for i, r in enumerate(rows) if r["compartment"] == compartment]
        axes[0].scatter(left[keep], right[keep], s=22, color=color, alpha=0.85,
                        label="brain" if compartment == "brain" else "nerve cord")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlim(*span)
    axes[0].set_ylim(*span)
    axes[0].set_xlabel("wire held by the left copy (µm)")
    axes[0].set_ylabel("wire held by the right copy (µm)")
    axes[0].legend(loc="upper left")
    axes[0].set_title(f"{len(rows)} neuropil pairs, dotted lines at a factor of two", loc="left", fontsize=10.5)

    extremes = sorted(rows, key=lambda r: -abs(r["log_ratio"]))[:EXTREMES][::-1]
    y = np.arange(len(extremes))
    axes[1].barh(y, [r["log_ratio"] for r in extremes],
                 color=[REAL if r["compartment"] == "brain" else CONNECTIVE for r in extremes], height=0.62)
    axes[1].axvline(0, color=MUTED, linewidth=1)
    axes[1].set_yticks(y, [r["neuropil"] for r in extremes], fontsize=8.5)
    axes[1].set_xlabel("log(left wire / right wire)")
    reach = max(abs(r["log_ratio"]) for r in extremes) * 1.22
    axes[1].set_xlim(-reach, reach)
    for i, r in enumerate(extremes):
        offset = 0.05 * reach * (1 if r["log_ratio"] > 0 else -1)
        axes[1].text(r["log_ratio"] + offset, i, f"{np.exp(abs(r['log_ratio'])):.1f}×", va="center", fontsize=8,
                     ha="left" if r["log_ratio"] > 0 else "right", color=INK_SECONDARY)
    axes[1].set_title("The most lopsided pairs", loc="left", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def report(result: dict) -> str:
    """Markdown report of the paired, midline and unpaired neuropils and the two asymmetry tests."""
    totals, wire = result["totals"], result["wire_asymmetry"]
    cost = result["cost_ratio_asymmetry"]
    rows = result["pairs"]
    worst = max(rows, key=lambda r: abs(r["log_ratio"]))
    heavier = "left" if wire["mean"] > 0 else "right"
    biased = wire["p_value"] < 0.05
    wider = wire["repaired_p_value"] > 0.95
    frame = pd.DataFrame(rows)[
        ["neuropil", "compartment", "types_left", "types_right", "wire_left_um", "wire_right_um",
         "wire_share_left", "wire_share_right", "cost_ratio_left", "cost_ratio_right", "log_ratio"]
    ]
    lines = [
        "# Wire symmetry",
        "",
        f"Of the {totals['neuropils']} neuropils that hold cell types, {totals['paired']['neuropils']} form "
        f"{wire['pairs']} left-right pairs and carry {totals['paired']['wire_share'] * 100:.2f}% of the wire. "
        f"Within a pair the two sides hold wire within a factor of "
        f"{np.exp(wire['median_absolute']):.2f} of each other at the median and "
        f"{np.exp(wire['mean_absolute']):.2f} on average; the widest gap is {worst['neuropil']}, where the "
        f"{'left' if worst['log_ratio'] > 0 else 'right'} copy holds {np.exp(abs(worst['log_ratio'])):.1f} times "
        f"the wire of the other. Across all pairs the {heavier} side holds a geometric mean of "
        f"{np.exp(abs(wire['mean'])):.3f} times the wire of the other, "
        + (f"a bias a sign-flip null separates from chance (p = {wire['p_value']:.3f})." if biased else
           f"which a sign-flip null does not separate from chance (p = {wire['p_value']:.3f})."),
        "",
        "## Pairs",
        "",
        *markdown_table(frame),
        "",
        "`wire_um`, `wire_share`, `types` and `cost_ratio` are read from `results/wire_atlas.json` rather than "
        "recomputed; `cost_ratio` is blank for a side the atlas left untested because it holds too few cell "
        "types or too few internal connections. `log_ratio` is the natural logarithm of the left side's wire "
        "over the right side's, so it is zero for a pair in balance and positive when the left copy holds more.",
        "",
        "## Is the asymmetry larger than expected?",
        "",
        "Two nulls, because the question has two halves.",
        "",
        f"**A systematic side bias.** If the two hemispheres are wired alike, the sign of a pair's `log_ratio` "
        f"is arbitrary, so negating each pair's log ratio at random gives the null distribution of their mean. "
        f"Observed mean {wire['mean']:+.4f} against a null spread of {wire['null_sd']:.4f} "
        f"(z = {wire['z_score']:+.2f}, two-sided p = {wire['p_value']:.4f} over {wire['permutations']} "
        f"sign flips). "
        + (f"The {heavier} hemisphere holds systematically more wire than the other." if biased else
           "There is no side bias in the wiring budget that this test can separate from chance."),
        "",
        f"**The size of the gap within a pair.** Matching each left neuropil to a right neuropil drawn at "
        f"random instead of to its own counterpart gives the asymmetry expected between two unrelated "
        f"structures of this atlas. The observed mean absolute log ratio is {wire['mean_absolute']:.4f} against "
        f"{wire['repaired_null_mean']:.4f} ± {wire['repaired_null_sd']:.4f} for random matching "
        f"({wire['repaired_n_at_or_below_observed']} of {wire['permutations']} random matchings at or below the "
        f"observed value, p = {wire['repaired_p_value']:.4f}). "
        + ("Counterparts are far more alike than arbitrary neuropils, which is what the name pairing asserts "
           "and is worth confirming, but it is a weak null: it sets no scale for how alike two copies of the "
           "same structure ought to be." if not wider else
           "Counterparts differ by more than arbitrary neuropils of this atlas do."),
        "",
        ("On neither test is the observed asymmetry larger than expected. It is smaller than random matching, "
         "and its direction is not consistent enough across pairs to register. The left-right difference in "
         "the wiring budget of this specimen is a null result."
         if not biased and not wider else
         "At least one of the two tests finds the observed asymmetry larger than its null, so the left-right "
         "difference in the wiring budget is not attributable to chance alone."),
        "",
        "## Internal placement economy",
        "",
        (f"{cost['pairs']} pairs have an internal cost ratio on both sides. The mean left-minus-right "
         f"difference is {cost['mean']:+.4f} against a sign-flip null spread of {cost['null_sd']:.4f} "
         f"(z = {cost['z_score']:+.2f}, p = {cost['p_value']:.4f}), and the mean absolute difference is "
         f"{cost['mean_absolute']:.4f} on ratios that all sit below one. "
         + ("Whatever placement economy a neuropil has, its opposite copy has about the same amount of it."
            if cost["p_value"] >= 0.05 else
            "The two sides differ systematically in how economically they are wired internally.")
         if cost else
         "No pair has an internal cost ratio on both sides, so there is nothing to compare here."),
        "",
        "## Neuropils that are not part of a pair",
        "",
        f"{totals['midline']['neuropils']} neuropils carry no hemisphere suffix and together hold "
        f"{totals['midline']['wire_share'] * 100:.2f}% of the wire:",
        "",
        *markdown_table(pd.DataFrame(result["midline"])),
        "",
        f"{totals['unpaired_sides']['neuropils']} are one side of a structure whose other side holds no cell "
        f"type in this specimen, holding {totals['unpaired_sides']['wire_share'] * 100:.2f}% of the wire "
        f"between them. They are excluded from the tests above and listed here rather than dropped:",
        "",
        *markdown_table(pd.DataFrame(result["unpaired_sides"])),
        "",
        "![Wire symmetry](wire_symmetry.png)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    result = symmetry(atlas)
    (RESULTS / "wire_symmetry.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "wire_symmetry.png")
    wire = result["wire_asymmetry"]
    worst = max(result["pairs"], key=lambda r: abs(r["log_ratio"]))
    print(f"{wire['pairs']} neuropil pairs; median wire ratio {np.exp(wire['median_absolute']):.2f}x, "
          f"widest {worst['neuropil']} at {np.exp(abs(worst['log_ratio'])):.1f}x; side bias p "
          f"{wire['p_value']:.4f}, against random matching p {wire['repaired_p_value']:.4f}")


if __name__ == "__main__":
    main()
