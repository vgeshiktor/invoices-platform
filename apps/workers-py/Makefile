.PHONY: venv run test lint fmt
venv:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip uv && uv pip install -r requirements.txt --system
run:
	python -c "print('workers ready')"
test:
	pytest -q
lint:
	ruff check --fix .
fmt:
	ruff format .
