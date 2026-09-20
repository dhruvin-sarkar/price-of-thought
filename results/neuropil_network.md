# Neuropil network

Collapsing the cell-type graph onto the neuropils gives a network of 89 regions joined by 2,698 weighted edges, 68.9% of the 3,916 pairs that could be joined. Every cell type takes the nearest of 105 published neuropil surfaces and each connection lends half its length to the neuropil at each of its ends, the rule `wire_atlas.py` uses; the whole pair matrix is recomputed here because the atlas saves only its 40 largest pairs. The recomputation reproduces the atlas total of 93.09 m and every pair it saves. 93.4% of the wire runs between two regions and the rest stays inside one.

## Regions

`strength_um` is the wire running between a region and every other region; `internal_um` is the wire that stays inside it. A micrometre between two regions belongs to both, so `atlas_wire_um`, which halves it, is the figure `wire_atlas.md` reports and the strengths sum to twice the between-region wire.

| neuropil | compartment | side | community | types | degree | strength_um | strength_share | internal_um | atlas_wire_um |
|---|---|---|---|---|---|---|---|---|---|
| GNG | brain |  | 2 | 1918 | 85 | 16057522.7 | 0.09235 | 1416344.5 | 9445105.9 |
| ANm | vnc |  | 2 | 1108 | 74 | 9007051.2 | 0.0518 | 916918.6 | 5420444.2 |
| LegNp(T3)(R) | vnc | R | 2 | 759 | 68 | 6890519.6 | 0.03963 | 227269.4 | 3672529.2 |
| LegNp(T2)(R) | vnc | R | 2 | 803 | 68 | 6790036.8 | 0.03905 | 286508.6 | 3681527.0 |
| AVLP(R) | brain | R | 1 | 1135 | 85 | 6771275.2 | 0.03894 | 386477.5 | 3772115.1 |
| LegNp(T2)(L) | vnc | L | 2 | 799 | 71 | 6720744.6 | 0.03865 | 294000.3 | 3654372.6 |
| AVLP(L) | brain | L | 1 | 1075 | 82 | 6455500.3 | 0.03713 | 344029.0 | 3571779.1 |
| LegNp(T1)(L) | vnc | L | 2 | 667 | 74 | 6079420.0 | 0.03496 | 152258.1 | 3191968.1 |
| LegNp(T3)(L) | vnc | L | 2 | 636 | 71 | 5855035.4 | 0.03367 | 154752.1 | 3082269.8 |
| SAD | brain |  | 2 | 677 | 82 | 5740695.7 | 0.03301 | 159696.7 | 3030044.6 |
| LegNp(T1)(R) | vnc | R | 2 | 590 | 74 | 5443329.6 | 0.0313 | 123728.7 | 2845393.5 |
| PB | brain |  | 1 | 820 | 82 | 5241388.8 | 0.03014 | 97945.1 | 2718639.5 |
| AL(L) | brain | L | 1 | 551 | 85 | 4025109.4 | 0.02315 | 206213.0 | 2218767.7 |
| AL(R) | brain | R | 1 | 570 | 87 | 3929411.9 | 0.0226 | 200605.5 | 2165311.5 |
| LH(L) | brain | L | 1 | 668 | 74 | 3690796.8 | 0.02123 | 125915.0 | 1971313.5 |
| SMP(L) | brain | L | 1 | 549 | 81 | 3688870.1 | 0.02121 | 50418.6 | 1894853.7 |
| LH(R) | brain | R | 1 | 620 | 70 | 3475295.1 | 0.01999 | 97205.8 | 1834853.3 |
| PLP(R) | brain | R | 1 | 485 | 78 | 3265478.1 | 0.01878 | 34980.4 | 1667719.5 |
| SMP(R) | brain | R | 1 | 500 | 80 | 3166910.1 | 0.01821 | 42026.6 | 1625481.6 |
| Ov(R) | vnc | R | 2 | 341 | 69 | 3152897.4 | 0.01813 | 20781.9 | 1597230.6 |
| PLP(L) | brain | L | 1 | 438 | 77 | 2964571.6 | 0.01705 | 31879.5 | 1514165.3 |
| Ov(L) | vnc | L | 2 | 301 | 70 | 2777116.9 | 0.01597 | 20555.9 | 1409114.3 |
| WTct(UTct-T2)(L) | vnc | L | 2 | 305 | 70 | 2701314.6 | 0.01554 | 39750.5 | 1390407.8 |
| SPS(L) | brain | L | 1 | 299 | 79 | 2616070.0 | 0.01505 | 6119.7 | 1314154.7 |
| SLP(L) | brain | L | 1 | 533 | 73 | 2600940.8 | 0.01496 | 89736.5 | 1390206.8 |
| SPS(R) | brain | R | 1 | 311 | 80 | 2551541.8 | 0.01467 | 7647.1 | 1283418.0 |
| SLP(R) | brain | R | 1 | 455 | 70 | 2352365.0 | 0.01353 | 53662.0 | 1229844.5 |
| ME(R) | brain | R | 1 | 448 | 70 | 2290905.1 | 0.01318 | 223619.1 | 1369071.7 |
| WTct(UTct-T2)(R) | vnc | R | 2 | 257 | 65 | 2219594.5 | 0.01276 | 27867.5 | 1137664.7 |
| AOTU(L) | brain | L | 1 | 360 | 76 | 2135083.3 | 0.01228 | 10742.8 | 1078284.5 |
| LO(L) | brain | L | 1 | 248 | 77 | 1987003.4 | 0.01143 | 31470.5 | 1024972.2 |
| IB | brain |  | 2 | 195 | 81 | 1804747.3 | 0.01038 | 2301.8 | 904675.5 |
| CA(R) | brain | R | 1 | 227 | 78 | 1764116.8 | 0.01015 | 8608.2 | 890666.7 |
| gL(L) | brain | L | 1 | 219 | 78 | 1738048.9 | 0.01 | 4566.7 | 873591.1 |
| LO(R) | brain | R | 1 | 228 | 75 | 1711810.2 | 0.00984 | 31696.7 | 887601.8 |
| gL(R) | brain | R | 1 | 214 | 76 | 1687838.0 | 0.00971 | 4333.9 | 848253.0 |
| CA(L) | brain | L | 1 | 200 | 78 | 1647943.3 | 0.00948 | 5826.0 | 829797.7 |
| AOTU(R) | brain | R | 1 | 247 | 76 | 1561288.6 | 0.00898 | 6449.5 | 787093.8 |
| ME(L) | brain | L | 1 | 278 | 54 | 1352427.3 | 0.00778 | 153371.9 | 829585.5 |
| HTct(UTct-T3)(R) | vnc | R | 2 | 126 | 62 | 1027117.7 | 0.00591 | 2756.6 | 516315.4 |
| WED(L) | brain | L | 1 | 120 | 70 | 941007.4 | 0.00541 | 4345.3 | 474849.0 |
| WED(R) | brain | R | 1 | 106 | 76 | 921502.1 | 0.0053 | 1868.3 | 462619.4 |
| CRE(R) | brain | R | 1 | 90 | 70 | 898325.9 | 0.00517 | 384.1 | 449547.0 |
| PRW | brain |  | 1 | 106 | 77 | 859705.8 | 0.00494 | 2722.7 | 432575.6 |
| HTct(UTct-T3)(L) | vnc | L | 2 | 90 | 60 | 768510.2 | 0.00442 | 1552.3 | 385807.3 |
| IntTct | vnc |  | 2 | 86 | 66 | 742566.5 | 0.00427 | 2392.6 | 373675.9 |
| IPS(L) | brain | L | 1 | 94 | 68 | 698405.5 | 0.00402 | 1124.5 | 350327.3 |
| IPS(R) | brain | R | 1 | 85 | 71 | 696349.6 | 0.004 | 916.8 | 349091.6 |
| mVAC(T3)(L) | vnc | L | 2 | 47 | 58 | 642060.4 | 0.00369 | 236.0 | 321266.2 |
| CRE(L) | brain | L | 1 | 68 | 66 | 634431.7 | 0.00365 | 482.5 | 317698.4 |
| NTct(UTct-T1)(R) | vnc | R | 2 | 32 | 64 | 615322.0 | 0.00354 | 414.8 | 308075.8 |
| LTct | vnc |  | 2 | 49 | 58 | 593412.5 | 0.00341 | 1195.0 | 297901.3 |
| SIP(L) | brain | L | 1 | 71 | 71 | 559795.3 | 0.00322 | 243.6 | 280141.3 |
| mVAC(T2)(L) | vnc | L | 2 | 44 | 48 | 552495.0 | 0.00318 | 1000.3 | 277247.8 |
| SIP(R) | brain | R | 1 | 79 | 65 | 513567.7 | 0.00295 | 499.8 | 257283.6 |
| ICL(R) | brain | R | 2 | 47 | 72 | 512493.0 | 0.00295 | 87.7 | 256334.2 |
| mVAC(T2)(R) | vnc | R | 2 | 34 | 52 | 503731.3 | 0.0029 | 282.7 | 252148.3 |
| ATL(L) | brain | L | 1 | 52 | 75 | 459726.2 | 0.00264 | 132.3 | 229995.4 |
| NTct(UTct-T1)(L) | vnc | L | 2 | 20 | 56 | 455860.4 | 0.00262 | 122.9 | 228053.1 |
| ATL(R) | brain | R | 1 | 51 | 71 | 442075.6 | 0.00254 | 104.1 | 221141.9 |
| mVAC(T3)(R) | vnc | R | 2 | 39 | 53 | 393648.8 | 0.00226 | 154.1 | 196978.5 |
| ICL(L) | brain | L | 1 | 47 | 69 | 392188.8 | 0.00226 | 121.7 | 196216.1 |
| AME(R) | brain | R | 1 | 56 | 49 | 321024.6 | 0.00185 | 2237.0 | 162749.3 |
| CV-anterior | brain |  | 2 | 28 | 63 | 306198.6 | 0.00176 | 315.7 | 153415.0 |
| LOP(R) | brain | R | 1 | 51 | 39 | 295974.2 | 0.0017 | 14607.8 | 162594.9 |
| PVLP(L) | brain | L | 1 | 51 | 52 | 294591.7 | 0.00169 | 994.9 | 148290.7 |
| LOP(L) | brain | L | 1 | 47 | 43 | 268799.0 | 0.00155 | 12454.3 | 146853.8 |
| LAL(R) | brain | R | 1 | 33 | 65 | 242256.6 | 0.00139 | 92.3 | 121220.6 |
| PVLP(R) | brain | R | 1 | 38 | 49 | 226592.6 | 0.0013 | 571.3 | 113867.6 |
| LAL(L) | brain | L | 1 | 26 | 65 | 223224.3 | 0.00128 | 15.4 | 111627.5 |
| CRN | brain |  | 2 | 10 | 52 | 176554.6 | 0.00102 | 93.4 | 88370.7 |
| mVAC(T1)(L) | vnc | L | 2 | 15 | 37 | 167284.1 | 0.00096 | 164.7 | 83806.7 |
| AME(L) | brain | L | 1 | 30 | 43 | 156684.8 | 0.0009 | 946.7 | 79289.1 |
| mVAC(T1)(R) | vnc | R | 2 | 15 | 40 | 138629.5 | 0.0008 | 100.1 | 69414.9 |
| aL(L) | brain | L | 1 | 9 | 35 | 49478.1 | 0.00028 | 8.1 | 24747.1 |
| aL(R) | brain | R | 1 | 10 | 33 | 47083.7 | 0.00027 | 49.2 | 23591.1 |
| a'L(R) | brain | R | 1 | 3 | 38 | 44519.0 | 0.00026 | 0.0 | 22259.5 |
| FB | brain |  | 1 | 5 | 48 | 35920.4 | 0.00021 | 0.0 | 17960.2 |
| a'L(L) | brain | L | 1 | 6 | 29 | 31068.5 | 0.00018 | 0.0 | 15534.3 |
| FLA(R) | brain | R | 2 | 6 | 22 | 27055.9 | 0.00016 | 48.5 | 13576.5 |
| bL(R) | brain | R | 1 | 2 | 23 | 18802.7 | 0.00011 | 0.0 | 9401.4 |
| AB(L) | brain | L | 1 | 1 | 22 | 18700.6 | 0.00011 | 0.0 | 9350.3 |
| LA(R) | brain | R | 1 | 4 | 15 | 13571.3 | 8e-05 | 12.9 | 6798.6 |
| FLA(L) | brain | L | 2 | 3 | 15 | 12044.1 | 7e-05 | 0.0 | 6022.1 |
| SCL(R) | brain | R | 1 | 2 | 21 | 10342.9 | 6e-05 | 0.0 | 5171.4 |
| EB | brain |  | 1 | 2 | 15 | 7344.6 | 4e-05 | 0.0 | 3672.3 |
| VES(R) | brain | R | 2 | 1 | 21 | 5911.9 | 3e-05 | 0.0 | 2956.0 |
| b'L(L) | brain | L | 1 | 1 | 19 | 4653.7 | 3e-05 | 0.0 | 2326.8 |
| LA(L) | brain | L | 1 | 1 | 2 | 1006.9 | 1e-05 | 0.0 | 503.4 |

## Hubs

GNG is the largest hub by wire, holding 16.06 m to 85 of the other 88 regions, 9.2% of all between-region wire. The 15 largest regions by wire hold 56.8% of it between them. Degree separates the regions much less than wire does: the median region has 69 partners and the least connected has 2.

## Small-world comparison

Two nulls, 1000 draws each, both of which preserve every region's number of partners exactly:

- **Rewired.** Degree-preserving edge swaps randomize which pairs of regions are joined, and the multiset of per-pair wire values is then dealt out over the rewired edges at random. Region strength is not preserved.
- **Weights shuffled.** The real topology is left alone and only the wire values are permuted over its edges, so the unweighted clustering and path length are the real ones by construction and the comparison isolates the arrangement of wire.

Clustering is the mean local clustering coefficient and path length the mean shortest path over all pairs; the weighted versions weigh a pair by its wire, a step along the heaviest pair of regions costing one and a thinner pair proportionally more.

### Against the rewired null

| metric | real | null mean | null sd | null central 95% | real / null | p |
|---|---|---|---|---|---|---|
| clustering | 0.872 | 0.8622 | 0.0017 | 0.8605 to 0.8634 | 1.0114 | 0.002 |
| path length | 1.3189 | 1.3121 | 0.0008 | 1.311 to 1.3138 | 1.0053 | 0.002 |
| weighted clustering | 0.9473 | 0.8622 | 0.0048 | 0.8521 to 0.8712 | 1.0986 | 0.002 |
| weighted path length | 292.416 | 28.9525 | 13.9444 | 22.3195 to 67.5948 | 10.0999 | 0.002 |

### Against the weight-shuffled null

| metric | real | null mean | null sd | null central 95% | real / null | p |
|---|---|---|---|---|---|---|
| clustering | 0.872 | 0.872 | 0.0 | 0.872 to 0.872 | 1.0 | 1.0 |
| path length | 1.3189 | 1.3189 | 0.0 | 1.3189 to 1.3189 | 1.0 | 1.0 |
| weighted clustering | 0.9473 | 0.8721 | 0.0046 | 0.8631 to 0.8812 | 1.0863 | 0.002 |
| weighted path length | 292.416 | 29.5737 | 14.4459 | 22.3554 to 76.0962 | 9.8877 | 0.002 |

The region network is more clustered than the rewired null by wire (1.099 times the null mean) but its weighted paths are 10.1 times longer, not shorter, which puts the wire-weighted small-world ratio at 0.109 — far below the one a small-world network would give. The network is not small-world by wire. The unweighted structure cannot answer the question either way: at 69% density almost every pair of regions is already joined, so the unweighted clustering is 0.872 against a null mean of 0.862 and the mean path is 1.32 steps against 1.31. The long weighted paths are the expected consequence of heavy pairs sitting together rather than bridging the network: the weight-shuffled null, which keeps the topology and moves only the wire, reproduces the same direction at 9.9 times the null mean.

## Communities

Louvain on the wire-weighted region graph returns 2 communities with modularity 0.229. All 100 random seeds return the same partition.

| community | regions | brain_regions | vnc_regions | strength_um |
|---|---|---|---|---|
| 1 | 57 | 57 | 0 | 85000711.7 |
| 2 | 32 | 9 | 23 | 88880922.8 |

**Community 1** (57 regions, largest by wire first): AVLP(R), AVLP(L), PB, AL(L), AL(R), LH(L), SMP(L), LH(R), PLP(R), SMP(R), PLP(L), SPS(L), SLP(L), SPS(R), SLP(R), ME(R), AOTU(L), LO(L), CA(R), gL(L), LO(R), gL(R), CA(L), AOTU(R), ME(L), WED(L), WED(R), CRE(R), PRW, IPS(L), IPS(R), CRE(L), SIP(L), SIP(R), ATL(L), ATL(R), ICL(L), AME(R), LOP(R), PVLP(L), LOP(L), LAL(R), PVLP(R), LAL(L), AME(L), aL(L), aL(R), a'L(R), FB, a'L(L), bL(R), AB(L), LA(R), SCL(R), EB, b'L(L), LA(L).

**Community 2** (32 regions, largest by wire first): GNG, ANm, LegNp(T3)(R), LegNp(T2)(R), LegNp(T2)(L), LegNp(T1)(L), LegNp(T3)(L), SAD, LegNp(T1)(R), Ov(R), Ov(L), WTct(UTct-T2)(L), WTct(UTct-T2)(R), IB, HTct(UTct-T3)(R), HTct(UTct-T3)(L), IntTct, mVAC(T3)(L), NTct(UTct-T1)(R), LTct, mVAC(T2)(L), ICL(R), mVAC(T2)(R), NTct(UTct-T1)(L), mVAC(T3)(R), CV-anterior, CRN, mVAC(T1)(L), mVAC(T1)(R), FLA(R), FLA(L), VES(R).

## Do the communities follow anatomy

| anatomical split | regions labelled | groups | adjusted Rand | normalized mutual information |
|---|---|---|---|---|
| compartment | 89 | 2 | 0.6265 | 0.5843 |
| side | 77 | 2 | -0.0099 | 0.0017 |
| segment | 18 | 3 | 0.0 | 0.0 |

The partition follows the brain and nerve cord split and nothing else. Against the compartment label it reaches an adjusted Rand index of 0.626 over all 89 regions. Against hemisphere it reaches -0.010 over the 77 regions carrying an `(L)` or `(R)` suffix, and against thoracic segment 0.000 over the 18 regions naming a segment — both indices sit at chance. Of the 36 neuropils present on both sides, only ICL has its two copies in different communities, and the leg neuropils of all three thoracic segments sit together; the wire that joins a region to its mirror image or to its neighbouring segment does not separate either from the rest of its compartment.

The correspondence with the compartment is strong but not exact. Community 2 holds every one of the 23 nerve-cord neuropils together with 9 brain neuropils — GNG, SAD, IB, ICL(R), CV-anterior, CRN, FLA(R), FLA(L), VES(R) — which are the gnathal and ventral-posterior regions that sit against the neck. On wire alone they group with the nerve cord rather than with the rest of the brain.
