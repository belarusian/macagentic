.PHONY: run

run:
	uv run --frozen python main.py $(ARGS)
