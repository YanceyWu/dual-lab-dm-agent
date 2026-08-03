SHELL := /bin/sh

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
LOCAL_PYTHON := $(REPO_ROOT)/src/.venv/bin/python
ifneq ($(origin PYTHON),command line)
PYTHON := $(shell if [ -x "$(LOCAL_PYTHON)" ]; then printf '%s' "$(LOCAL_PYTHON)"; else command -v python3; fi)
endif

.PHONY: validate rehearse-release build-usage-bundles

validate:
	@cd "$(REPO_ROOT)" && "$(PYTHON)" tools/validate_release.py

rehearse-release:
	@cd "$(REPO_ROOT)" && "$(PYTHON)" tools/rehearse_release.py

build-usage-bundles:
	@cd "$(REPO_ROOT)" && "$(PYTHON)" tools/build_usage_bundle.py
