"""Check the region network's wire accounting, its null comparisons, its partition and the report."""

import pipeline.neuropil_network as neuropil_network
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("neuropil_network.json")
    totals, rows, net = s["totals"], s["regions"], s["network"]
    names = net["regions"]
    n = len(names)

    assert totals["n_nulls"] == neuropil_network.N_NULLS
    assert totals["regions"] == len(rows) == n, "the totals, the region rows and the network disagree on the count"
    assert totals["possible_region_edges"] == n * (n - 1) // 2, "the pairs that could be joined are miscounted"
    assert totals["region_edges"] == len(net["pairs"]), "the network holds a different number of edges"
    assert close(totals["density"], totals["region_edges"] / totals["possible_region_edges"], rel=1e-3), "density"
    assert [r["strength_um"] for r in rows] == sorted((r["strength_um"] for r in rows), reverse=True), \
        "the regions are not ordered by the wire they hold to other regions"

    seen = set()
    for i, j, wire, connections in net["pairs"]:
        assert 0 <= i < j < n, f"pair ({i}, {j}) is not an ordered pair of regions"
        assert (i, j) not in seen, f"{names[i]}-{names[j]} appears twice"
        assert wire > 0 and connections > 0, f"{names[i]}-{names[j]} is joined by nothing"
        seen.add((i, j))
    assert [p[2] for p in net["pairs"]] == sorted((p[2] for p in net["pairs"]), reverse=True), \
        "the pairs are not ordered by the wire between them"

    # Every micrometre either stays inside one region or runs between exactly two of them.
    between = sum(p[2] for p in net["pairs"])
    within = sum(net["internal_um"])
    assert close(between, totals["between_region_wire_um"], rel=1e-6), \
        "the pairs do not add up to the between-region wire"
    assert close(within, totals["within_region_wire_um"], rel=1e-6), \
        "the diagonal does not add up to the within-region wire"
    assert close(between + within, totals["total_wire_um"], rel=1e-6), "the network does not hold all the wire"
    assert close(totals["share_between_regions"], between / totals["total_wire_um"], rel=1e-3), "the share disagrees"

    atlas = result_json("wire_atlas.json")
    assert close(totals["total_wire_um"], atlas["totals"]["total_wire_um"], rel=1e-6), \
        "the network and the wire atlas disagree on the total wire"
    assert s["atlas_agreement"]["pairs_reproduced"] == len(atlas["pairs"]), "not every atlas pair was reproduced"
    assert totals["meshes"] == atlas["totals"]["meshes"], "the two disagree on how many meshes there are"
    assert totals["regions"] == atlas["totals"]["neuropils_with_types"], "the two disagree on how many hold types"
    atlas_wire = {r["neuropil"]: r["wire_um"] for r in atlas["neuropils"]}

    strength = dict.fromkeys(names, 0.0)
    degree = dict.fromkeys(names, 0)
    for i, j, wire, _ in net["pairs"]:
        strength[names[i]] += wire
        strength[names[j]] += wire
        degree[names[i]] += 1
        degree[names[j]] += 1
    internal = dict(zip(names, net["internal_um"]))
    for row in rows:
        name = row["neuropil"]
        assert close(row["strength_um"], strength[name], rel=1e-4), f"{name} strength does not match its pairs"
        assert row["degree"] == degree[name], f"{name} degree does not match its pairs"
        assert close(row["strength_share"], strength[name] / (2 * between), rel=1e-3, abs_tol=1e-5), \
            f"{name} strength share"
        # Half of the wire between two regions belongs to each, which is the figure the atlas reports.
        assert close(row["atlas_wire_um"], internal[name] + strength[name] / 2, rel=1e-4), f"{name} atlas wire"
        assert close(row["atlas_wire_um"], atlas_wire[name], rel=1e-4), f"{name} disagrees with the wire atlas"
        assert row["types"] > 0, f"{name} is listed with no cell types"

    world = s["small_world"]
    for label, comparisons in world["nulls"].items():
        for metric in ("clustering", "path_length", "weighted_clustering", "weighted_path_length"):
            c = comparisons[metric]
            assert close(c["real"], world["real"][metric], rel=1e-6), \
                f"{label} {metric} restates a different real value"
            assert close(c["ratio"], c["real"] / c["null_mean"], rel=1e-3), f"{label} {metric} ratio arithmetic"
            assert c["null_lo"] <= c["null_hi"], f"{label} {metric} null interval is inverted"
            assert 0 <= c["n_at_or_above_real"] <= totals["n_nulls"], f"{label} {metric} rank out of range"
            assert 0 < c["p_value"] <= 1, f"{label} {metric} p-value out of range"
        for prefix in ("", "weighted_"):
            assert close(comparisons[f"{prefix}sigma"],
                         comparisons[f"{prefix}clustering"]["ratio"] / comparisons[f"{prefix}path_length"]["ratio"],
                         rel=1e-3), f"{label} {prefix}sigma arithmetic"
    # Shuffling wire over the real topology cannot move an unweighted statistic.
    for metric in ("clustering", "path_length"):
        assert close(world["nulls"]["weights shuffled"][metric]["ratio"], 1.0, rel=1e-6), \
            f"the weight-shuffled null moved the unweighted {metric}"

    part, communities = s["partition"], s["communities"]
    assert part["communities"] == len(communities), "the partition and the community list disagree"
    assert 1 <= part["distinct_partitions"] <= part["seeds"] and 0 < part["seeds_agreeing"] <= part["seeds"]
    members = [name for community in communities for name in community["members"]]
    assert sorted(members) == sorted(names), "the communities are not a partition of the regions"
    labelled = {r["neuropil"]: r["community"] for r in rows}
    for community in communities:
        assert community["regions"] == len(community["members"]), f"community {community['community']} size"
        assert community["brain_regions"] + community["vnc_regions"] == community["regions"], \
            f"community {community['community']} compartment counts"
        assert all(labelled[name] == community["community"] for name in community["members"]), \
            f"community {community['community']} disagrees with the region rows"

    # A label fewer than two regions carry is left uncompared; the compartment split is the one the report quotes.
    compared = [split for split, agreement in s["anatomy"].items() if agreement is not None]
    assert "compartment" in compared, "the communities were never compared with brain against nerve cord"
    for split in compared:
        agreement = s["anatomy"][split]
        assert 2 <= agreement["regions"] <= totals["regions"], f"{split} labels an impossible number of regions"
        assert -1 <= agreement["adjusted_rand"] <= 1 and 0 <= agreement["nmi"] <= 1, f"{split} index out of range"
    mirror = s["mirrored"]
    assert mirror["split_across_communities"] == len(mirror["split"]) <= mirror["neuropils_on_both_sides"], \
        "the mirrored-pair counts disagree"

    assert same_text(result_text("neuropil_network.md"), neuropil_network.report(s)), \
        "neuropil_network.md is out of date"
    rewired = world["nulls"]["rewired"]
    return (f"{totals['regions']} regions and {totals['region_edges']:,} weighted edges reproduce the atlas total of "
            f"{totals['total_wire_um'] / 1e6:.1f} m; weighted clustering {rewired['weighted_clustering']['ratio']:.3f} "
            f"and weighted path length {rewired['weighted_path_length']['ratio']:.1f} times the rewired null; "
            f"{part['communities']} communities, adjusted Rand {s['anatomy']['compartment']['adjusted_rand']:.3f} "
            "against brain versus nerve cord; report current")


if __name__ == "__main__":
    run(check)
