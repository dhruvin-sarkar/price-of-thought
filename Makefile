PYTHON ?= python
export PYTHONUTF8 = 1
CHECKS := schema spatial_graph preregistration spatial_optimality richclub value wiring_economy cable_length price \
	generative threshold_robustness hero readme_assets references citations document_numbers

.PHONY: reproduce data analyze hero readme export paper test verify

reproduce: data analyze hero readme export paper test verify

data:
	$(PYTHON) -m pipeline.schema_discovery
	$(PYTHON) -m pipeline.build_spatial_graph

analyze:
	$(PYTHON) -m pipeline.spatial_permutation_test
	$(PYTHON) -m pipeline.connective_richclub
	$(PYTHON) -m pipeline.connective_value --workers 8
	$(PYTHON) -m pipeline.wiring_economy_extensions
	$(PYTHON) -m pipeline.cable_length_validation
	$(PYTHON) -m pipeline.connective_price --workers 6
	$(PYTHON) -m pipeline.threshold_robustness --workers 8
	$(PYTHON) -m pipeline.generative_model
	$(PYTHON) -m pipeline.generative_comparison --workers 6

hero:
	$(PYTHON) -m pipeline.hero_render
	$(PYTHON) -m pipeline.front_view

# README plates, figures and methods diagram, drawn from results/ into assets/readme/.
readme:
	$(PYTHON) -m pipeline.readme_assets

export:
	$(PYTHON) -m export.build_static_json

# Figures are read from ../results, so typst's root is the repository.
paper:
	cd paper && pandoc report.md -o report.pdf --pdf-engine=typst --pdf-engine-opt=--root=..

test:
	$(PYTHON) -m pytest -q

# Checks the committed results against their invariants and each other; fails if any check fails.
# Checks whose inputs are not on disk report SKIP and do not fail.
verify:
	@status=0; for c in $(CHECKS); do printf "%-22s" "$$c"; $(PYTHON) -m verify.check_$$c || status=1; done; exit $$status
