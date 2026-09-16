# Spatially embedded cell-type graph

Dataset `male-cns:v1.0`: 164,506 neurons with a cell type.

## Nodes

Each node is a cell type on one side of the body, `type|side`. The side is the soma hemisphere (`somaSide`), or for neurons without a CNS soma the hemisphere of their nerve root (`rootSide`). Pooling both sides of a bilateral type would place its centroid on the midline, away from every one of its neurons.

- 23,073 nodes; sides: L 11,449, R 11,422, M 161, unknown 41.
- Position: the centroid of the node's soma positions when at least 50% of its neurons have one (22,139 nodes), otherwise the synapse-count-weighted centroid of its neurons' synapses (934 nodes, 751 of them sensory, whose somata lie outside the CNS). For the 10,865 soma-placed nodes with more than one soma, the mean distance of a soma from its node centroid has median 9.9 µm, 90th percentile 103.4 µm and 99th percentile 171.2 µm.
- Compartment: brain-dominant if more than half of the node's synapses (pre + post) that lie in `CentralBrain`, `Optic(L)`, `Optic(R)` or `VNC` lie in the first three, VNC-dominant if fewer than half. Synapses in the neck connective (`CV`) are not counted. Every node received a label.
- Connective: nodes whose cell type is descending or ascending (`results/connective_set.json`), 2,047 of 23,073 nodes (8.9%).

| connective role | brain-dominant | VNC-dominant |
|---|---|---|
| descending | 897 | 54 |
| ascending | 205 | 891 |
| none | 14,950 | 6,076 |

## Edges

A directed edge joins two nodes when the connection supplies at least 1% of the target node's input synapses from typed neurons; self-connections are excluded. 490,884 edges.

The same rule applied to cell types pooled across sides gives 11,751 types and 243,439 edges from 122,318,556 synapses between typed neurons, the graph used in Fault Lines and ConnectomeLens, rebuilt here from a fresh neuPrint pull.

Mean out-degree 21.3.
