ifeq ($(OS),Windows_NT)
PYTHON ?= python
PY := backend/.venv/Scripts/python
else
PYTHON ?= python3
PY := backend/.venv/bin/python
endif

.PHONY: install dev back worker front test migrate

install:
	$(PYTHON) -m venv backend/.venv
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install
	$(PY) backend/manage.py migrate

migrate:
	$(PY) backend/manage.py migrate

back:
	$(PY) backend/manage.py runserver 127.0.0.1:8040

worker:
	$(PY) backend/manage.py run_huey -w 1 -k thread

front:
	cd frontend && npm run dev

dev:
	$(MAKE) -j3 back worker front

test:
	cd backend && $(abspath $(PY)) -m pytest -q
	cd frontend && npm run typecheck
