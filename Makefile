.PHONY: install run test lint docs
install:
	python -m pip install -r requirements-dev.txt
run:
	python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
test:
	python -m pytest --cov=app --cov-report=term-missing
lint:
	python -m ruff check app tests scripts
	python -m ruff format --check app tests scripts
docs:
	python scripts/export_docs.py
