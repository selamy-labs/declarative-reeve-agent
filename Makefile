.PHONY: verify test sim image-layout container-structure image-structure

PYTHON ?= python3
IMAGE_TAG ?= career-steward-agent:structure-test
export PYTHONPATH := src

verify:
	$(PYTHON) scripts/verify.py
	$(MAKE) container-structure
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m career_steward.sim --manifest agent.manifest.yaml --input examples/sim/inbound-message.json --out generated/sim-run.json

test:
	$(PYTHON) -m unittest discover -s tests -v

sim:
	$(PYTHON) -m career_steward.sim --manifest agent.manifest.yaml --input examples/sim/inbound-message.json --out generated/sim-run.json

image-layout:
	$(PYTHON) scripts/build_image_layout.py --layout image/image-layout.yaml --out generated/image-layout

container-structure: image-layout
	$(PYTHON) scripts/container_structure_test.py --layout generated/image-layout --spec image/container-structure-test.yaml

image-structure:
	docker build -f image/Containerfile -t $(IMAGE_TAG) .
	$(PYTHON) scripts/container_structure_test.py --image $(IMAGE_TAG) --spec image/container-structure-test.yaml
