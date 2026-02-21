PYTHON ?= python3.12
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: install install-browser init run rerun-failed test lint report-open api-run db-migrate acceptance-smoke acceptance-backend

install: $(VENV)/bin/python

$(VENV)/bin/python: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-browser: install
	$(PY) -m playwright install chromium

init: install-browser
	$(PY) -m tos_radar.cli init

run: install-browser
	$(PY) -m tos_radar.cli run

rerun-failed: install-browser
	$(PY) -m tos_radar.cli rerun-failed

test: install
	$(PY) -m unittest discover -s tests -p "test_*.py" -v

lint: install
	$(PY) -m ruff check tos_radar tests

report-open: install
	$(PY) -m tos_radar.cli report-open

api-run: install
	$(PY) -m tos_radar.cli api-run

db-migrate: install
	$(PY) -m tos_radar.cli db-migrate

acceptance-smoke: install
	$(PY) -m unittest tests.test_acceptance_smoke_backend -v

acceptance-backend: install
	$(PY) -m unittest \
		tests.test_cabinet_service \
		tests.test_cabinet_telegram_service \
		tests.test_cabinet_telegram_test_service \
		tests.test_cabinet_security_service \
		tests.test_cabinet_account_lifecycle_service \
		tests.test_cabinet_store \
		tests.test_cabinet_api \
		tests.test_cabinet_api_degradation \
		tests.test_acceptance_smoke_backend \
		-v
