PYTHON ?= python

.PHONY: install run api ui ingest demo test lint typecheck fmt schema

install:
	$(PYTHON) -m pip install -e .[dev]

run:
	$(PYTHON) -m option_flow.scripts.run_dev

api:
	$(PYTHON) -m option_flow.api.main

ui:
	$(PYTHON) -m streamlit run src/option_flow/ui/app.py --server.port 8501

ingest:
	$(PYTHON) -m option_flow.ingest.worker

demo:
	$(PYTHON) -m option_flow.scripts.run_demo

test:
	pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src

typecheck:
	$(PYTHON) -m mypy src

fmt:
	$(PYTHON) -m ruff format .

schema:
	$(PYTHON) scripts/init_db.py --demo
