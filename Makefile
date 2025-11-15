# https://sebastian.lauwe.rs/blog/parallelising-makefile-uv/
.PHONY: testall
.PRECIOUS: .venv-%/pyvenv.cfg

PYTHON_VERSIONS := 3.10 3.11 3.12 3.13 3.14
TEST_TARGETS := $(addprefix .tests-,$(PYTHON_VERSIONS))

testall: $(TEST_TARGETS)

.venv-%/pyvenv.cfg:
	uv venv --python $(patsubst .venv-%,%,$(@D)) $(@D)

.tests-%: .venv-%/pyvenv.cfg
	venv=$(patsubst .tests-%,.venv-%,$@) && \
	source $$venv/bin/activate && \
	uv run --active --python $$venv pytest
