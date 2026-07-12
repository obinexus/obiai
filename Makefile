.PHONY: install test lint demo api serve doctor web
install:
	python -m pip install -e ".[dev]"
test:
	pytest -q
lint:
	ruff check src tests
demo:
	uai demo
api:
	uvicorn obiai.api:app --reload
serve:
	uai serve
doctor:
	uai doctor
web:
	npm --prefix web run dev
