# What the length of a connection buys

The cell-type graph has 23,073 nodes, 490,884 directed connections and 93.09 m of wire. Connections are removed cumulatively under three schedules and the graph that is left is measured each time: longest first, shortest first, and at random. Comparing the two ends against the same amount of wire removed answers the question the project asks — per micrometre of wire, do long connections buy more connectivity than short ones?

## Measures and sampling

- **Efficiency.** The mean of 1/d over ordered pairs of nodes, d the directed shortest path in connections. It is estimated from a fixed sample of 300 source nodes drawn once (seed 20960916) and used at every point of every schedule, so the curves differ only in what was removed. Characteristic path length is the more familiar measure but it is the wrong one here: removal is exactly what makes pairs unreachable, and the mean of a set that includes infinities is undefined, whereas an unreachable pair contributes a well-defined zero to efficiency. The full distance matrix is 23,073 × 23,072 pairs per point, which is why it is sampled rather than computed whole.
- **Largest component.** The number of nodes in the largest weakly connected component.
- **Sampling of the curve.** 18 points, placed at the shares of the total wire 0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6. At each point the longest-first and shortest-first schedules have removed the same amount of wire, by construction, and the random schedule has removed the same *number* of connections as the longest-first one. The random schedule is the mean of 5 draws.

The whole graph has efficiency 0.2152 and a largest weakly connected component of 23,070 of its 23,073 nodes. Every efficiency below is given as a share of that starting value.

## Longest first

| wire_removed_share | edges_removed | edges_removed_share | largest_component_share | efficiency | efficiency_share |
|---|---|---|---|---|---|
| 0.0 | 0 | 0.0 | 0.99987 | 0.215224 | 1.0 |
| 0.01 | 993 | 0.00202 | 0.99987 | 0.21451 | 0.99668 |
| 0.02001 | 2038 | 0.00415 | 0.99987 | 0.21438 | 0.99608 |
| 0.03001 | 3118 | 0.00635 | 0.99987 | 0.214191 | 0.9952 |
| 0.05 | 5383 | 0.01097 | 0.99987 | 0.213766 | 0.99323 |
| 0.075 | 8385 | 0.01708 | 0.99987 | 0.213084 | 0.99006 |
| 0.10001 | 11577 | 0.02358 | 0.99987 | 0.212215 | 0.98602 |
| 0.12501 | 14972 | 0.0305 | 0.99987 | 0.211172 | 0.98117 |
| 0.15 | 18583 | 0.03786 | 0.99987 | 0.20994 | 0.97545 |
| 0.20001 | 26582 | 0.05415 | 0.99987 | 0.206601 | 0.95993 |
| 0.25 | 35849 | 0.07303 | 0.99987 | 0.201265 | 0.93514 |
| 0.3 | 47242 | 0.09624 | 0.99987 | 0.19194 | 0.89182 |
| 0.35 | 60956 | 0.12418 | 0.99974 | 0.184923 | 0.85921 |
| 0.4 | 76729 | 0.15631 | 0.9997 | 0.178325 | 0.82856 |
| 0.45 | 94349 | 0.1922 | 0.99961 | 0.172258 | 0.80037 |
| 0.5 | 113559 | 0.23134 | 0.99957 | 0.164619 | 0.76487 |
| 0.55 | 134364 | 0.27372 | 0.99944 | 0.157384 | 0.73126 |
| 0.6 | 156798 | 0.31942 | 0.999 | 0.149505 | 0.69465 |

## Shortest first, matched on the wire removed

| wire_removed_share | edges_removed | edges_removed_share | largest_component_share | efficiency | efficiency_share |
|---|---|---|---|---|---|
| 0.0 | 0 | 0.0 | 0.99987 | 0.215224 | 1.0 |
| 0.01 | 40861 | 0.08324 | 0.99987 | 0.209993 | 0.9757 |
| 0.02 | 60597 | 0.12344 | 0.99987 | 0.207394 | 0.96362 |
| 0.03 | 76222 | 0.15527 | 0.99987 | 0.205423 | 0.95446 |
| 0.05 | 101753 | 0.20729 | 0.99978 | 0.199668 | 0.92772 |
| 0.075 | 128187 | 0.26114 | 0.99935 | 0.194226 | 0.90244 |
| 0.1 | 151243 | 0.3081 | 0.99848 | 0.188737 | 0.87693 |
| 0.125 | 172010 | 0.35041 | 0.99775 | 0.181831 | 0.84485 |
| 0.15 | 191036 | 0.38917 | 0.99684 | 0.175821 | 0.81692 |
| 0.2 | 225227 | 0.45882 | 0.99315 | 0.164887 | 0.76612 |
| 0.25 | 255849 | 0.5212 | 0.98938 | 0.154352 | 0.71717 |
| 0.3 | 283921 | 0.57839 | 0.98396 | 0.134488 | 0.62487 |
| 0.35 | 309922 | 0.63135 | 0.97768 | 0.118255 | 0.54945 |
| 0.4 | 334087 | 0.68058 | 0.96801 | 0.104503 | 0.48555 |
| 0.45 | 356521 | 0.72628 | 0.94942 | 0.084716 | 0.39362 |
| 0.5 | 377326 | 0.76867 | 0.91657 | 0.063002 | 0.29273 |
| 0.55 | 396536 | 0.8078 | 0.86616 | 0.045572 | 0.21174 |
| 0.6 | 414156 | 0.84369 | 0.79522 | 0.029105 | 0.13523 |

## Random, matched on the number of connections removed

| wire_removed_share | edges_removed | edges_removed_share | largest_component_share | efficiency | efficiency_share | efficiency_share_sd |
|---|---|---|---|---|---|---|
| 0.0 | 0 | 0.0 | 0.99987 | 0.215224 | 1.0 | 0.0 |
| 0.002012 | 993 | 0.00202 | 0.99987 | 0.215116 | 0.999502 | 0.000107 |
| 0.004148 | 2038 | 0.00415 | 0.99987 | 0.214995 | 0.998936 | 0.000291 |
| 0.006366 | 3118 | 0.00635 | 0.99987 | 0.214882 | 0.99841 | 0.000315 |
| 0.010968 | 5383 | 0.01097 | 0.99987 | 0.214642 | 0.997298 | 0.000291 |
| 0.017028 | 8385 | 0.01708 | 0.99987 | 0.214324 | 0.995816 | 0.000472 |
| 0.023548 | 11577 | 0.02358 | 0.99987 | 0.21385 | 0.993616 | 0.001011 |
| 0.030518 | 14972 | 0.0305 | 0.99987 | 0.213457 | 0.99179 | 0.001182 |
| 0.037874 | 18583 | 0.03786 | 0.99987 | 0.212607 | 0.98784 | 0.003008 |
| 0.05425 | 26582 | 0.05415 | 0.99987 | 0.211705 | 0.98365 | 0.002546 |
| 0.073096 | 35849 | 0.07303 | 0.99987 | 0.210517 | 0.978128 | 0.002336 |
| 0.096428 | 47242 | 0.09624 | 0.99987 | 0.209139 | 0.971726 | 0.001953 |
| 0.124462 | 60956 | 0.12418 | 0.99987 | 0.207184 | 0.962644 | 0.001704 |
| 0.156428 | 76729 | 0.15631 | 0.99987 | 0.205061 | 0.952778 | 0.003459 |
| 0.192112 | 94349 | 0.1922 | 0.99987 | 0.2024 | 0.940414 | 0.003328 |
| 0.231302 | 113559 | 0.23134 | 0.99987 | 0.199207 | 0.92558 | 0.004912 |
| 0.273812 | 134364 | 0.27372 | 0.99987 | 0.195552 | 0.908596 | 0.00724 |
| 0.319332 | 156798 | 0.31942 | 0.99987 | 0.191652 | 0.890478 | 0.006424 |

## Per micrometre of wire

At the reference point, 25% of the wire removed (23.27 m): taking it from the long end costs 35,849 connections (7.3% of them) and leaves efficiency at 93.5% of the whole graph's. Taking the same wire from the short end costs 255,849 connections (52.1%) and leaves efficiency at 71.7%. Per metre of wire removed that is 0.28% of the starting efficiency lost from the long end against 1.22% from the short end, a factor of 4.4.

Efficiency falls to half its starting value after 38.9% of it is taken from the short end, and not within the 60% sampled from the long end, where it still stands at 69.5%.

**Short connections buy more connectivity per micrometre than long ones.**

The reason is arithmetic rather than subtle: a micrometre spent on short connections buys many more of them. The median connection is 154 µm long against a mean of 190 µm, so the same wire taken from the short end removes 7.1 times as many connections. The budget spent on the long tail is not buying connectivity efficiently; whatever else it is for, it is not the cheapest way to keep the graph short-pathed.

## Per connection

Matched on the number of connections removed rather than the wire, the picture reverses. At 35,849 connections removed, taking the longest leaves efficiency at 93.5% while taking the same number at random leaves it at 97.8% ± 0.2% over 5 draws. The longest connections are individually worth more to the graph than typical ones — they are simply not worth their length.

## Fragmentation

None of the three schedules breaks the graph apart over the range sampled. The largest weakly connected component holds 23,070 of the 23,073 nodes to begin with and still holds 99.99% of them after 25% of the wire is taken from the long end, 98.94% after the same wire is taken from the short end and 99.99% after the matched number of random removals. At the far end of the sampled range, with 60% of the wire gone, the long-end schedule has cost 31% of the efficiency while leaving 99.90% of the nodes in one component, and the short-end schedule has cost 86% of the efficiency while still leaving 79.5% of them in one. Component size is a blunt instrument at this density: efficiency has collapsed while the graph is still almost entirely one piece. That is a null result for the component measure rather than evidence that the graph is robust in any useful sense.
