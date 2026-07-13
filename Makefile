.PHONY: run runui screenshot debug-render test test-ui

run:
	uv run --frozen python -m macagentic $(ARGS)

runui:
	uv run --frozen python -m macagentic --ui $(ARGS)

screenshot:
	uv run --frozen python -m macagentic.ui.screenshot_cli --output debug_screenshot.png

QUERY ?= What is 1+1?

debug-render:
	uv run --frozen python -m macagentic --ui "$(QUERY)" --screenshot debug_screenshot.png

test:
	uv run --frozen python -m pytest

test-ui:
	uv run --frozen python -m pytest -m uitest
