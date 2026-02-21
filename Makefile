PYTHON ?= python3.12
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: install install-browser init run rerun-failed test lint report-open

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
