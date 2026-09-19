"""Check the headline numbers in the paper and the README are the ones in the result files."""

from pipeline.common import ROOT
from verify.common import result_json, run

PAPER = ROOT / "paper" / "report.md"
README = ROOT / "README.md"


def minus(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace("-", "−")


def claims() -> list[tuple[str, str, tuple[str, ...]]]:
    """(what, the number as written, documents that must contain it) for every headline figure."""
    graph = result_json("spatial_graph_summary.json")["spatial_graph"]
    placement = result_json("spatial_optimality.json")["analyses"]
    economy = result_json("wiring_economy_extensions.json")
    richclub = result_json("connective_richclub.json")
    value = result_json("connective_value.json")["families"]
    price = result_json("connective_price.json")["tests"]
    fits = result_json("generative_model.json")["models"]
    comparison = result_json("generative_comparison.json")["models"]
    robustness = {r["fraction"]: r for r in result_json("threshold_robustness.json")["thresholds"]}
    cable = result_json("cable_length.json")
    shares = {row["label"]: row for row in economy["cost_share"]["rows"]}
    both, paper = ("paper", "readme"), ("paper",)
    reproduced = round(comparison["G"]["fraction_reproduced"] * 13)
    return [
        ("nodes", f"{graph['nodes']:,}", both),
        ("edges", f"{graph['edges']:,}", both),
        ("placement ratio", f"{placement['primary']['cost_ratio']:.3f}", both),
        ("placement z", minus(placement["primary"]["z_score"], 1), both),
        ("within-compartment ratio", f"{placement['within_compartment']['cost_ratio']:.3f}", both),
        ("brain-only ratio", f"{economy['compartment_optimality']['brain']['cost_ratio']:.3f}", paper),
        ("nerve-cord-only ratio", f"{economy['compartment_optimality']['vnc']['cost_ratio']:.3f}", paper),
        ("swap saving", f"{100 * economy['local_optimum']['reduction']:.2f}%", paper),
        ("swap saving, rounded", f"{100 * economy['local_optimum']['reduction']:.1f}%", ("readme",)),
        ("length constant", f"{economy['distance_dependence']['all']['length_constant_um']:.0f} µm", both),
        ("neck edge share", f"{100 * shares['neck-crossing']['edge_share']:.1f}%", both),
        ("neck cost share", f"{100 * shares['neck-crossing']['cost_share']:.1f}%", paper),
        ("high-degree edge length", f"{economy['cost_share']['mean_length_high_um']:.0f} against "
                                    f"{economy['cost_share']['mean_length_other_um']:.0f} µm", both),
        ("rich-to-rich ratio", f"{richclub['routes_top10']['total']['ratio']:.3f}", both),
        ("partner enrichment", f"{richclub['endpoint_enrichment']['ratio']:.2f}", both),
        ("hub odds ratio", f"{richclub['whole_cns_membership']['odds_ratio']:.2f}", both),
        ("value ratio", f"{value['crossing_cost']['flow']['ratio']:.2f}", both),
        ("brain-to-cord ratio", f"{value['crossing_cost']['flow_brain_to_vnc']['ratio']:.2f}", both),
        ("flow lost by the cut", f"{value['crossing_cost']['flow']['real']:,.0f}", both),
        ("flow lost at random", f"{value['crossing_cost']['flow']['null_mean']:,.0f}", both),
        ("count-matched ratio", f"{value['crossing_count']['flow']['ratio']:.2f}", paper),
        ("descending partial rho", f"{price['descending']['partial_rho']:.3f}", both),
        ("descending zero-value nodes", f"{price['descending']['zero_value']} of {price['descending']['n']}", paper),
        ("ascending zero-value nodes", f"{price['ascending']['zero_value']} of {price['ascending']['n']:,}", paper),
        ("model G pseudo-R2", f"{fits['G']['pseudo_r2_mcfadden']:.3f}", paper),
        ("model G AUC", f"{fits['G']['cv_auc_mean']:.3f}", paper),
        ("properties reproduced", f"{reproduced} of the 13", paper),
        ("properties reproduced, README", f"{reproduced} of 13", ("readme",)),
        ("route ratio at 0.5%", f"{robustness[0.005]['routes']['total']['ratio']:.3f}", paper),
        ("cable rho", f"{cable['spearman_rho']:.3f}", paper),
    ]


def check() -> str:
    texts = {"paper": PAPER.read_text(encoding="utf-8"), "readme": README.read_text(encoding="utf-8")}
    missing = [f"{what} ({number}) not in {doc}" for what, number, docs in claims() for doc in docs
               if number not in texts[doc]]
    assert not missing, f"{len(missing)} headline numbers differ from the results: {'; '.join(missing)}"
    return f"{len(claims())} headline numbers in the paper and README match the result files"


if __name__ == "__main__":
    run(check)
