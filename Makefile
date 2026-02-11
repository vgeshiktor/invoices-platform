.PHONY: setup dev up down test lint fmt run-gmail run-graph run-report run-monthly run-n8n quarantine

setup: ## התקנות ראשוניות
	pre-commit install

dev: ## הרצה מקומית של כל הסרוויסים (דוקר קומפוז)
	docker compose -f deploy/compose/docker-compose.dev.yml up --build

up:
	docker compose -f deploy/compose/docker-compose.dev.yml up -d

down:
	docker compose -f deploy/compose/docker-compose.dev.yml down

test:
	@if $(PYTHON) -c "import coverage" > /dev/null 2>&1; then \
		echo "Running pytest with coverage..."; \
		PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m coverage run -m pytest tests && \
		$(PYTHON) -m coverage report --show-missing; \
	else \
		echo "coverage module not found for $(PYTHON); attempting installation..."; \
		if $(PYTHON) -m pip install --quiet coverage; then \
			PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m coverage run -m pytest tests && \
			$(PYTHON) -m coverage report --show-missing; \
		else \
			echo "Failed to install coverage, running pytest without coverage."; \
			PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m pytest tests; \
		fi \
	fi

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
GMAIL_EXTRA_ARGS ?= --save-candidates candidates_gmail.json --save-nonmatches rejected_gmail.json

GRAPH_CLIENT_ID ?=
GRAPH_AUTHORITY ?= consumers
GRAPH_INVOICES_DIR ?= invoices_outlook
GRAPH_EXTRA_ARGS ?= --save-json invoices.json \
	--save-csv invoices.csv \
    --download-report download_report.json \
	--explain --verify \
	--save-candidates candidates_outlook.json --save-nonmatches rejected_outlook.json

MONTHLY_BASE_DIR ?= invoices
MONTHLY_PROVIDERS ?= gmail,outlook
MONTHLY_GMAIL_ARGS ?= --exclude-sent --verify
MONTHLY_GRAPH_ARGS ?= --exclude-sent --verify --explain
MONTHLY_SEQUENTIAL ?=

REPORT_INPUT_DIR ?= invoices_outlook
REPORT_JSON_OUTPUT ?= invoice_report.json
REPORT_CSV_OUTPUT ?= invoice_report.csv
REPORT_EXTRA_ARGS ?=

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

run-report: ## Generate invoice report JSON/CSV from downloaded PDFs
	PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m invplatform.cli.invoices_report \
		--input-dir $(REPORT_INPUT_DIR) \
		--json-output $(REPORT_JSON_OUTPUT) \
		--csv-output $(REPORT_CSV_OUTPUT) \
		$(REPORT_EXTRA_ARGS)

run-monthly: ## Download current-month invoices (Gmail+Outlook) and consolidate under invoices/
	PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m invplatform.cli.monthly_invoices \
		--providers "$(MONTHLY_PROVIDERS)" \
		--base-dir $(MONTHLY_BASE_DIR) \
		$(if $(MONTH),--month $(MONTH),) \
		$(if $(YEAR),--year $(YEAR),) \
		$(if $(MONTHLY_GMAIL_ARGS),--gmail-extra-args "$(MONTHLY_GMAIL_ARGS)",) \
		$(if $(MONTHLY_GRAPH_ARGS),--graph-extra-args "$(MONTHLY_GRAPH_ARGS)",) \
		$(if $(GRAPH_CLIENT_ID),--graph-client-id "$(GRAPH_CLIENT_ID)",) \
		$(if $(MONTHLY_SEQUENTIAL),--sequential,)

run-n8n: ## Start n8n (dev compose only)
	docker compose -f deploy/compose/docker-compose.dev.yml up -d --build n8n

quarantine: ## Move non-invoice PDFs into quarantine/
	PYTHONPATH=$(PYTHONPATH_EXTRA):$$PYTHONPATH $(PYTHON) -m invplatform.cli.quarantine_invoices
