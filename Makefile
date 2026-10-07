# Makefile

.PHONY: test dep-update

test:
	uv sync --frozen --dev
	uv run pytest tests -o "addopts="

dep-update:
	uv sync --upgrade
	uv lock
	uv run python3 scripts/update-pyproject-versions.py
	uv lock --check
	$(MAKE) test
