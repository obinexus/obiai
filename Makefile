.PHONY: install test lint demo api
install:
	python -m pip install -e ".[dev]"
test:
	pytest -q
lint:
	ruff check src tests
demo:
	obiai demo
api:
	uvicorn obiai.api:app --reload
