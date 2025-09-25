PYTHON ?= python

.PHONY: install run api ui ingest demo test test-unit test-integration lint typecheck fmt schema launcher desktop desktop-package compose

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

test-unit:
	pytest -m "not integration"

test-integration:
	pytest -m integration

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src

typecheck:
	$(PYTHON) -m mypy src

fmt:
	$(PYTHON) -m ruff format .

schema:
	$(PYTHON) scripts/init_db.py --demo

launcher:
	$(PYTHON) -m option_flow.launcher.cli

desktop:
	$(PYTHON) -m option_flow.desktop.app

desktop-package:
	pyinstaller --clean --noconfirm desktop/option_flow_desktop.spec

compose:
	docker compose up --build
