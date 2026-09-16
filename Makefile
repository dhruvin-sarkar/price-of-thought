PYTHON ?= python
export PYTHONUTF8 = 1

.PHONY: reproduce data analyze test

reproduce: data analyze

data:
	$(PYTHON) -m pipeline.schema_discovery
	$(PYTHON) -m pipeline.build_spatial_graph

analyze:
	$(PYTHON) -m pipeline.spatial_permutation_test

test:
	$(PYTHON) -m pytest -q
