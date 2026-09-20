/**
 * The numbers shared by the hero, the section openings and the captions, read once from the exported results.
 * pipeline/readme_assets.py derives the same set for the README plates and the poster.
 */
export function headline(data) {
  const shares = Object.fromEntries(data.cost_share.rows.map((row) => [row.label, row]));
  const neck = shares["neck-crossing"];
  const value = data.value.families.crossing_cost;
  return {
    neck,
    ratio: data.placement.primary.cost_ratio,
    zScore: data.placement.primary.z_score,
    withinRatio: data.placement.within_compartment.cost_ratio,
    swap: data.swaps.reduction,
    routes: data.richclub.routes.total.ratio,
    routesP: data.richclub.routes.total.p_value,
    enrichment: data.richclub.endpoint_enrichment.ratio,
    odds: data.richclub.membership.odds_ratio,
    flowRatio: value.flow.ratio,
    brainRatio: value.flow_brain_to_vnc.ratio,
    cordRatio: value.flow_vnc_to_brain.ratio,
    intactFlow: data.value.intact.flow,
    partialRho: data.price.tests.descending.partial_rho,
    lengthConstant: data.distance.summary.all.length_constant_um,
    meanHigh: data.cost_share.mean_length_high_um,
    meanOther: data.cost_share.mean_length_other_um,
    reproduced: Object.values(data.generative.comparison.models.G.properties).filter((p) => p.reproduced).length,
    properties: Object.keys(data.generative.comparison.models.G.properties).length,
  };
}
