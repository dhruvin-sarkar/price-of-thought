# Design direction for the project site

Written before any frontend code.

## Purpose

Show, in one sitting, the results of this study of how the *Drosophila* male CNS pays for its wiring. Cell types are placed so that their connections are short. The neck connective holds a quarter of the wire in a small share of the connections. That wire is enriched for connections between well-connected partners, but, length for length, it is not where sensory-to-motor flow is concentrated. The site also has to show the negative and null results at the same size as the positive ones, and let a reader check every number against the repository.

## Audience

1. Connectomics and systems neuroscience researchers who know wiring-economy work (Cherniak, Chklovskii, Kaiser & Hilgetag, van den Heuvel & Sporns) and will look for overclaiming first.
2. Technically literate readers arriving from the launch posts who know neither the fly nor the network statistics, and need each result stated in a sentence before the chart.

The first group decides whether the work is taken seriously, so the methods and validation section is not hidden or shrunk.

## Tone

Plain, measured, specific. Sentences carry numbers, not adjectives. Every result states its hypothesis, its null model and its outcome, including "not supported". No claims about cognition, consciousness or development. The title is the only playful thing on the page.

## The one memorable detail

The connective itself, in 3D. The page opens on the whole-CNS neuropil shell with the 36,943 neck-crossing connections drawn through it as lines coloured by length. The visitor can rotate it, and can switch the overlay between length (wiring cost), connections to rich partners, and each cell type's price against its value. Picking a cell type shows its wiring alone and its line in the price-and-value table. Everything else on the page is quiet so that this is what people remember and share.

## Structure

Separate sections, each reachable by its own anchor:

1. **Hero**: the interactive 3D connective view and the headline statistic (wiring 54% shorter than random placement; the neck is 7.5% of connections and 24% of the wire).
2. **Placement**: the permutation test and its three variants, distance dependence, the within-compartment tests, and distance from a swap optimum.
3. **The connective**: rich-to-rich routing, connective hubs, the value test against cost-matched wiring, and the price-and-value table per cell type.
4. **Generative model**: what distance, compartment and cell class reproduce, and what they miss.
5. **Methods and validation**: pre-registration commits, null models, the cable-length check, threshold robustness, limitations, and links to every `results/` file. This section has the same weight as the ones above it.
6. A short footer placing the project as the third part with ConnectomeLens and Fault Lines.

## Visual system

- **Colour.** A cool paper background (`#f4f5f3`) and near-black ink (`#0b0b0b`), shared with the two earlier projects' hero images. One data ramp, pale peach to deep brown, encodes wire length and is used for nothing else. One secondary hue, blue, marks null distributions, as in the figures in `results/`. Colour is only ever an encoding, never decoration.
- **Type.** Archivo for text and headings, and Spline Sans Mono for numbers and statistics, as in the other two projects' images. Sentence case everywhere.
- **Layout.** A single reading column around 68 characters wide for prose. Charts break out wider than the column, and the 3D view is full width. There are no cards, shadows or panels around content. Sections are divided by space and a hairline rule.
- **Charts.** Rendered from static JSON in the page, following the same conventions as the committed figures: titles as sentences, direct labels over legends where possible, and every axis in units.
- **Motion.** Only what explains: the 3D view rotates slowly until the visitor touches it, and overlay changes cross-fade. Nothing animates on scroll. `prefers-reduced-motion` stops the rotation.

## Anti-patterns to avoid

Cream-and-terracotta or near-black-and-neon defaults. A SaaS card kit. ALL-CAPS eyebrow labels above headings. Middle-dot metadata strings. Buttons with arrow suffixes. Numbered markers on content that is not a sequence. Entrance animations on every element. Gradient text. Stat tiles that strip numbers of their context.

## Constraints

- A static site with no backend. Every value is precomputed by `export/build_static_json.py` from files in `results/` and `data/`.
- GitHub Pages, deployed by Actions on push to `main`, the same single path as the other two projects.
- The 3D view must stay interactive on a mid-range laptop. Meshes are decimated and connections drawn as one line batch, with the payload aimed below 15 MB compressed.
- Usable at phone width: the 3D view becomes a static render with the overlay switch, and tables scroll within their own box.
- Accessible: keyboard-operable controls, text alternatives for every chart, contrast of at least 4.5:1 for text, and no information carried by colour alone in tables.
