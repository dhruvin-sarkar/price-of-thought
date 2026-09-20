# Wire concentration

The 490,884 connections of the cell-type graph hold 93.09 m of wire between them. Sorted longest first, the top 1% hold 4.6% of it and the top 10% hold 30.7%; the Gini coefficient of the length distribution is 0.404.

## Length by where a connection runs

| group | edges | wire_um | mean_um | median_um | p90_um | p99_um | max_um |
|---|---|---|---|---|---|---|---|
| all | 490884 | 93094951.3 | 189.65 | 154.33 | 360.56 | 808.8 | 1003.9 |
| within the brain | 319431 | 49540297.9 | 155.09 | 146.26 | 263.25 | 544.69 | 993.74 |
| within the nerve cord | 133277 | 21855139.8 | 163.98 | 145.25 | 293.58 | 570.46 | 931.93 |
| across the neck | 36943 | 22371156.5 | 605.56 | 597.65 | 826.5 | 941.35 | 1003.9 |

## Concentration

| group | gini | top 0.1% | top 1% | top 5% | top 10% | top 25% | top 50% |
|---|---|---|---|---|---|---|---|
| all | 0.4039 | 0.005 | 0.0459 | 0.1879 | 0.3072 | 0.5225 | 0.7675 |
| within the brain | 0.3428 | 0.0059 | 0.0429 | 0.1438 | 0.2363 | 0.4588 | 0.7384 |
| within the nerve cord | 0.3343 | 0.0053 | 0.0433 | 0.1429 | 0.2397 | 0.4641 | 0.7301 |
| across the neck | 0.1513 | 0.0016 | 0.0159 | 0.0756 | 0.1459 | 0.337 | 0.6085 |

## Upper tail

A power law fitted above 161 µm, covering 231,054 connections, has exponent 2.99. Weighed against alternatives, a positive ratio favors the power law:

| against | loglikelihood_ratio | p_value |
|---|---|---|
| lognormal | -45.52 | 0.0 |
| exponential | 46.808 | 0.0 |
| truncated_power_law | -62.523 | 0.0 |

## Wire by superclass

A connection is counted for the class of each of its two ends, so the shares sum to more than one.

| superclass | types | edges | wire_um | wire_share | mean_length_um | median_length_um |
|---|---|---|---|---|---|---|
| cb_intrinsic | 13027 | 300466 | 51887020.6 | 0.55736 | 172.69 | 152.01 |
| vnc_intrinsic | 5393 | 141088 | 29828642.9 | 0.32041 | 211.42 | 158.08 |
| ascending_neuron | 1089 | 57516 | 20905944.5 | 0.22457 | 363.48 | 306.7 |
| descending_neuron | 951 | 49647 | 19012805.3 | 0.20423 | 382.96 | 332.86 |
| visual_projection | 681 | 31050 | 4866317.4 | 0.05227 | 156.73 | 149.8 |
| vnc_sensory | 328 | 18765 | 2730484.5 | 0.02933 | 145.51 | 123.86 |
| ol_intrinsic | 529 | 17415 | 2337623.4 | 0.02511 | 134.23 | 127.02 |
| cb_sensory | 342 | 13299 | 1574333.4 | 0.01691 | 118.38 | 97.14 |
| visual_centrifugal | 213 | 6563 | 1360086.3 | 0.01461 | 207.24 | 194.41 |
| sensory_ascending | 52 | 4276 | 1173959.3 | 0.01261 | 274.55 | 266.11 |
| vnc_motor | 281 | 6685 | 1163297.7 | 0.0125 | 174.02 | 123.65 |
| cb_motor | 86 | 2438 | 394412.6 | 0.00424 | 161.78 | 128.15 |
| vnc_efferent | 32 | 710 | 167408.6 | 0.0018 | 235.79 | 118.59 |
| sensory_descending | 8 | 400 | 110691.7 | 0.00119 | 276.73 | 257.97 |
| cb_endocrine | 20 | 379 | 102756.1 | 0.0011 | 271.12 | 266.16 |
| efferent_ascending | 8 | 235 | 81781.2 | 0.00088 | 348.01 | 236.39 |
| vnc_endocrine | 8 | 142 | 44943.6 | 0.00048 | 316.5 | 165.39 |
| ol_sensory | 21 | 279 | 17624.3 | 0.00019 | 63.17 | 49.2 |
| efferent_descending | 2 | 51 | 13134.4 | 0.00014 | 257.54 | 176.7 |
| cb_efferent | 2 | 46 | 12841.0 | 0.00014 | 279.15 | 228.73 |
