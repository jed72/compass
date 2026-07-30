# Compass - top-level targets.
#
# The canonical command for each thing. The reviewer's v1 concern was that
# `pytest -q` must run reliably from a clean checkout - so `make test`
# disables pytest plugin autoload, which is the most common source of
# environment-specific hangs.

.PHONY: help test lint validate ci release clean

help:  ## list targets
	@grep -E '^[a-z-]+:.*?##' Makefile | awk -F':.*?##' '{printf "  %-12s %s\n", $$1, $$2}'

test:  ## run the CLI test suite (autoload disabled - reliable in clean envs)
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -q

lint:  ## validate governance YAML
	python3 cli/compass policy lint

validate:  ## self-check the framework repo structure
	bash scripts/validate.sh

ci:  ## the full mechanical gate suite (policy lint + task lint + check across all tasks)
	python3 cli/compass ci

release:  ## build a clean release tarball into dist/
	bash scripts/release.sh

clean:  ## remove build / pytest / cache noise (leaves `.compass/work/` alone)
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	find . -name '*.bak' -delete 2>/dev/null || true
	find . -name '.DS_Store' -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage dist build 2>/dev/null || true
	@echo "cleaned."
