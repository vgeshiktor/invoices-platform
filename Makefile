.PHONY: setup dev up down test lint fmt run-gmail run-graph

setup: ## התקנות ראשוניות
	pre-commit install

dev: ## הרצה מקומית של כל הסרוויסים (דוקר קומפוז)
	docker compose -f deploy/compose/docker-compose.dev.yml up --build

up:
	docker compose -f deploy/compose/docker-compose.dev.yml up -d

down:
	docker compose -f deploy/compose/docker-compose.dev.yml down

test:
	$(MAKE) -C apps/api-go test
	$(MAKE) -C apps/workers-py test
	PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m pytest tests

lint:
	$(MAKE) -C apps/api-go lint
	$(MAKE) -C apps/workers-py lint

fmt:
	$(MAKE) -C apps/api-go fmt
	$(MAKE) -C apps/workers-py fmt

PYTHON ?= python
PYTHONPATH_EXTRA := apps/workers-py/src

START_DATE ?=
END_DATE ?=

GMAIL_INVOICES_DIR ?= invoices_gmail
GMAIL_EXTRA_ARGS ?=

GRAPH_CLIENT_ID ?=
GRAPH_AUTHORITY ?= consumers
GRAPH_INVOICES_DIR ?= invoices_outlook
GRAPH_EXTRA_ARGS ?= --save-json invoices.json \
	--save-csv invoices.csv \
    --download-report download_report.json \
	--explain --verify

run-gmail: ## הרצת Gmail invoice finder (נדרש START_DATE ו-END_DATE)
	@test -n "$(START_DATE)" || (echo "START_DATE is required. Example: make run-gmail START_DATE=2025-06-01 END_DATE=2025-07-01"; exit 1)
	@test -n "$(END_DATE)" || (echo "END_DATE is required. Example: make run-gmail START_DATE=2025-06-01 END_DATE=2025-07-01"; exit 1)
	PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m invplatform.cli.gmail_invoice_finder \
		--start-date $(START_DATE) \
		--end-date $(END_DATE) \
		--invoices-dir $(GMAIL_INVOICES_DIR) \
		$(GMAIL_EXTRA_ARGS)

run-graph: ## הרצת Outlook/Graph invoice finder (נדרש START_DATE, END_DATE, GRAPH_CLIENT_ID)
	@test -n "$(START_DATE)" || (echo "START_DATE is required. Example: make run-graph START_DATE=2025-06-01 END_DATE=2025-07-01 GRAPH_CLIENT_ID=..."; exit 1)
	@test -n "$(END_DATE)" || (echo "END_DATE is required. Example: make run-graph START_DATE=2025-06-01 END_DATE=2025-07-01 GRAPH_CLIENT_ID=..."; exit 1)
	@test -n "$(GRAPH_CLIENT_ID)" || (echo "GRAPH_CLIENT_ID is required. Pass via make run-graph GRAPH_CLIENT_ID=..."; exit 1)
	PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m invplatform.cli.graph_invoice_finder \
		--client-id "$(GRAPH_CLIENT_ID)" \
		--authority "$(GRAPH_AUTHORITY)" \
		--start-date $(START_DATE) \
		--end-date $(END_DATE) \
		--invoices-dir $(GRAPH_INVOICES_DIR) \
		$(GRAPH_EXTRA_ARGS)
