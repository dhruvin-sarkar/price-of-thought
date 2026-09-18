PYTHON ?= python
export PYTHONUTF8 = 1

.PHONY: reproduce data analyze hero export test

reproduce: data analyze hero export

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

export:
	$(PYTHON) -m export.build_static_json

test:
	$(PYTHON) -m pytest -q
