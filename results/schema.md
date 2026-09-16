# neuPrint schema: male-cns:v1.0

## Coordinates

The dataset `Meta` node gives voxel size [8.0, 8.0, 8.0] in `nanometers`. Soma positions (`somaLocation`) and synapse positions (`Synapse.location`) are stored in voxels, so every coordinate is multiplied by 8 nm / 1000 = 0.008 µm per voxel.

Sanity check: the somata of all typed neurons span 730 µm along x, 514 µm along y, 995 µm along z. The long axis (z) runs from the brain to the posterior end of the ventral nerve cord, about a millimetre, which is the expected scale for an adult fly CNS; a factor-of-1000 unit error would put these spans near 1 µm or 1 m.

Brain and nerve-cord somata separate along z (voxels):

| superclass | neurons | mean_z | min_z | max_z |
|---|---|---|---|---|
| cb_intrinsic | 31122 | 26620.0 | 10154 | 43610 |
| vnc_intrinsic | 12563 | 101107.0 | 60697 | 134531 |

## Fields used downstream

- cell type: `type`
- superclass (descending / ascending / sensory / motor): `superclass`
- soma position (voxels): `somaLocation`
- soma hemisphere: `somaSide`
- nerve-root hemisphere (neurons without a CNS soma): `rootSide`
- per-ROI synapse counts: `roiInfo`

## Soma positions by superclass (typed neurons)

Sensory neurons have their cell bodies in the periphery, outside the imaged CNS, and so carry no `somaLocation`; their positions downstream come from synapse locations instead.

| superclass | neurons | with_soma | share_with_soma |
|---|---|---|---|
| ol_intrinsic | 89357 | 81031 | 0.907 |
| cb_intrinsic | 31280 | 31122 | 0.995 |
| vnc_intrinsic | 12967 | 12563 | 0.969 |
| visual_projection | 9201 | 9162 | 0.996 |
| ol_sensory | 6098 | 28 | 0.005 |
| vnc_sensory | 5605 | 2 | 0.0 |
| cb_sensory | 4756 | 0 | 0.0 |
| ascending_neuron | 1841 | 1807 | 0.982 |
| descending_neuron | 1310 | 1304 | 0.995 |
| vnc_motor | 699 | 695 | 0.994 |
| visual_centrifugal | 562 | 562 | 1.0 |
| sensory_ascending | 528 | 0 | 0.0 |
| cb_motor | 106 | 102 | 0.962 |
| vnc_efferent | 78 | 77 | 0.987 |
| cb_endocrine | 65 | 61 | 0.938 |
| vnc_endocrine | 22 | 22 | 1.0 |
| sensory_descending | 12 | 0 | 0.0 |
| efferent_ascending | 8 | 8 | 1.0 |
| efferent_descending | 4 | 4 | 1.0 |
| cb_efferent | 4 | 4 | 1.0 |
| visual_projection_tbc | 2 | 2 | 1.0 |
| sensory_ascending_tbc | 1 | 0 | 0.0 |

## Connective set

Each type takes the `superclass` held by the majority of its neurons. Of 11751 types:

- **Descending** (`descending_neuron`, brain to nerve cord): 480 types.
- **Ascending** (`ascending_neuron`, nerve cord to brain): 563 types.

Every type name was confirmed in a second live query. 22 of these types contain some neurons with another superclass; the lowest majority share is 0.50.

Cross-check against anatomy: of the 3265 typed neurons with synapses inside the neck connective ROI (`CV`), 2789 (85.4%) are descending or ascending neurons. The remainder are listed below; sensory ascending neurons (peripheral somata, axons ascending through the neck) are the largest group and are kept out of the connective set because they have no CNS soma to place.

| superclass | neurons | neck_neurons | neck_types |
|---|---|---|---|
| ascending_neuron | 1841 | 1631 | 562 |
| descending_neuron | 1310 | 1158 | 474 |
| sensory_ascending | 528 | 424 | 28 |
| cb_motor | 106 | 20 | 10 |
| sensory_descending | 12 | 12 | 4 |
| efferent_ascending | 8 | 8 | 5 |
| cb_intrinsic | 31280 | 5 | 4 |
| vnc_motor | 699 | 4 | 2 |
| vnc_intrinsic | 12967 | 1 | 1 |
| cb_endocrine | 65 | 1 | 1 |
| vnc_efferent | 78 | 1 | 1 |

## Top-level ROIs under CNS

- `CV`
- `CentralBrain`
- `Optic(L)`
- `Optic(R)`
- `VNC`

Compartments: brain = `CentralBrain`, `Optic(L)`, `Optic(R)`; vnc = `VNC`. `CV` belongs to neither.

## Neuron properties

| property | non-null neurons |
|---|---|
| post | 176422 |
| pre | 176422 |
| downstream | 176422 |
| upstream | 176422 |
| synweight | 176422 |
| bodyId | 176422 |
| roiInfo | 176422 |
| statusLabel | 176243 |
| size | 175313 |
| totalNtPredictions | 174165 |
| predictedNt | 174165 |
| celltypeTotalNtPredictions | 174165 |
| celltypePredictedNt | 174165 |
| consensusNt | 174165 |
| predictedNtConfidence | 173308 |
| status | 172208 |
| superclass | 166700 |
| vfbId | 166686 |
| type | 164506 |
| celltypePredictedNtConfidence | 164445 |
| instance | 161506 |
| somaSide | 150726 |
| group | 147514 |
| flywireType | 143156 |
| somaLocation | 141781 |
| itoleeHl | 37754 |
| supertype | 34096 |
| hemibrainType | 32919 |
| class | 26513 |
| assignedOlHex1 | 23720 |
| assignedOlHex2 | 23720 |
| mancType | 22744 |
| subclass | 21930 |
| somaNeuromere | 21820 |
| trumanHl | 19753 |
| mancBodyid | 18708 |
| rootSide | 17939 |
| mancGroup | 14554 |
| entryNerve | 11835 |
| birthtime | 7904 |
| mancSerial | 5422 |
| fruDsx | 5012 |
| synonyms | 3958 |
| mcnsSerial | 3945 |
| matchingNotes | 3425 |
| dimorphism | 2368 |
| exitNerve | 1005 |
| tosomaLocation | 995 |
| serialMotif | 902 |
| receptorType | 752 |
