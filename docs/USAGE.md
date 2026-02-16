# Usage Guide

This guide documents all currently implemented user-facing functionality in this repository.

## 1. Setup

### 1.1 Python dependencies

```bash
pip install -r requirements.txt
```

### 1.2 Optional: run full local stack

```bash
make dev
```

Services in `deploy/compose/docker-compose.dev.yml`:
- `api-go` on `:8080`
- `workers-py`
- `db` (Postgres) on `:5432`
- `mq` (RabbitMQ) on `:5672` and management UI on `:15672`
- `n8n` on `:5678`

### 1.3 Authentication files

- Gmail finder expects OAuth files:
  - `credentials.json`
  - `token.json` (created after first auth flow)
- Graph finder requires `--client-id` (or `GRAPH_CLIENT_ID` for monthly orchestration).

## 2. Command Matrix

| Goal | Make target | Direct CLI |
|---|---|---|
| Find/download Gmail invoices | `make run-gmail ...` | `python -m invplatform.cli.gmail_invoice_finder ...` |
| Find/download Outlook/Graph invoices | `make run-graph ...` | `python -m invplatform.cli.graph_invoice_finder ...` |
| Run both providers for one month + consolidate | `make run-monthly ...` | `python -m invplatform.cli.monthly_invoices ...` |
| Parse PDFs and generate report files | `make run-report ...` | `python -m invplatform.cli.invoices_report ...` |
| Move likely non-invoice PDFs to quarantine | `make quarantine` | `python -m invplatform.cli.quarantine_invoices ...` |
| Remove duplicate invoice files by hash | none | `python scripts/remove_duplicate_invoices.py ...` |
| Start local n8n | `make run-n8n` | docker compose directly |

## 3. Gmail Invoice Finder

Entry point:

```bash
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.gmail_invoice_finder --help
```

Typical run:

```bash
make run-gmail START_DATE=2026-01-01 END_DATE=2026-02-01
```

Key functionality:
- Builds Gmail search query from date range (unless `--gmail-query` is provided).
- Finds invoice-like messages using keyword + sender heuristics.
- Downloads attachment PDFs and link-based PDFs (including provider-specific flows such as Bezeq).
- Optional candidate/non-match dumps and debug explainability.
- Optional verification against PDF text heuristics.

Useful flags:
- `--gmail-query`, `--start-date`, `--end-date`, `--exclude-sent`
- `--invoices-dir`, `--keep-quarantine`
- `--save-json`, `--save-csv`, `--save-candidates`, `--save-nonmatches`
- `--verify`, `--explain`, `--debug`

## 4. Microsoft Graph Invoice Finder

Entry point:

```bash
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.graph_invoice_finder --help
```

Typical run:

```bash
make run-graph START_DATE=2026-01-01 END_DATE=2026-02-01 GRAPH_CLIENT_ID=<client-id>
```

Key functionality:
- Reads messages from Graph over date range.
- Filters and scores messages using invoice heuristics and context checks.
- Downloads attachments and link-based PDFs.
- Optional threshold sweep and explainability output for tuning.
- Optional exclusion of Sent Items.

Useful flags:
- `--client-id`, `--authority`, `--start-date`, `--end-date`
- `--interactive-auth`, `--token-cache-path`
- `--invoices-dir`, `--keep-quarantine`
- `--save-json`, `--save-csv`, `--save-candidates`, `--save-nonmatches`, `--download-report`
- `--exclude-sent`, `--threshold-sweep`, `--verify`, `--explain`, `--debug`

Unattended scheduling tip (n8n/cron):
- first bootstrap run once with `--interactive-auth` and a persistent `--token-cache-path`
- scheduled runs should omit `--interactive-auth` and reuse the same cache path
- if cache is missing/expired, CLI exits fast with `AUTH_REQUIRED` instead of waiting for input

## 5. Monthly Orchestration

Entry point:

```bash
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.monthly_invoices --help
```

Typical runs:

```bash
# current month, both providers
make run-monthly GRAPH_CLIENT_ID=<client-id>

# specific month
MONTH=1 YEAR=2026 make run-monthly GRAPH_CLIENT_ID=<client-id>

# only Gmail
MONTHLY_PROVIDERS=gmail make run-monthly

# Outlook/Gmail with persisted Graph token cache (seamless after bootstrap)
make run-monthly GRAPH_CLIENT_ID=<client-id> GRAPH_TOKEN_CACHE_PATH=./.msal_token_cache.bin

# one-time Graph bootstrap auth for monthly flow (interactive device code)
make run-monthly GRAPH_CLIENT_ID=<client-id> GRAPH_INTERACTIVE_AUTH=1 GRAPH_TOKEN_CACHE_PATH=./.msal_token_cache.bin
```

Behavior:
- Computes monthly range `[start_date, end_date)`.
- Runs Gmail/Graph fetchers (parallel by default).
- Deduplicates PDFs inside provider folders.
- Consolidates all provider PDFs into `invoices/invoices_MM_YYYY`.
- Writes run metadata to `run_summary.json`.

Important flags:
- `--providers`, `--month`, `--year`, `--base-dir`
- `--gmail-extra-args`, `--graph-extra-args`
- `--graph-client-id`
- `--sequential`

## 6. Invoice Report Generator

Entry point:

```bash
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.invoices_report --help
```

Typical run:

```bash
make run-report REPORT_INPUT_DIR=invoices/invoices_01_2026
```

Outputs:
- JSON report
- CSV report
- Summary CSV totals
- PDF report

Parsing/report functionality:
- Extracts invoice fields from PDFs (id, date, vendor, purpose, totals, VAT, period, refs, etc.).
- Includes vendor/category heuristics and vendor-specific parsing logic.
- PDF report supports Hebrew/English text and vendor sorting.
- PDF report can include vendor subtotal rows and a grand total row.

Main flags:
- `--input-dir`, `--files`
- `--json-output`, `--csv-output`, `--summary-csv-output`, `--pdf-output`
- `--pdf-vendor-subtotals` / `--no-pdf-vendor-subtotals`
- `--pdf-skip-single-vendor-subtotals`
- `--debug`

Examples:

```bash
# disable vendor subtotals in PDF
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.invoices_report \
  --input-dir invoices/invoices_01_2026 \
  --json-output report-01-2026.json \
  --csv-output report-01-2026.csv \
  --no-pdf-vendor-subtotals

# keep subtotals but skip vendors that appear once
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.invoices_report \
  --input-dir invoices/invoices_01_2026 \
  --json-output report-01-2026.json \
  --csv-output report-01-2026.csv \
  --pdf-skip-single-vendor-subtotals
```

## 7. Quarantine Non-Invoice PDFs

Entry point:

```bash
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.quarantine_invoices --help
```

Typical usage:

```bash
make quarantine
```

Direct examples:

```bash
PYTHONPATH=apps/workers-py/src python -m invplatform.cli.quarantine_invoices \
  --input-dir invoices/invoices_01_2026 --dry-run
```

Behavior:
- Scans PDFs recursively (skips `_tmp`, `quarantine`, `duplicates`).
- Moves files failing invoice heuristics into quarantine.

## 8. Remove Duplicate Invoices Script

Entry point:

```bash
python scripts/remove_duplicate_invoices.py --help
```

Examples:

```bash
# dry-run by default
python scripts/remove_duplicate_invoices.py invoices

# apply deletion
python scripts/remove_duplicate_invoices.py invoices --apply

# move duplicates instead of deleting
python scripts/remove_duplicate_invoices.py invoices --apply --move-to invoices/duplicates_review
```

Behavior:
- SHA-256 hash-based duplicate detection.
- Can operate on `.pdf` (default) or custom extensions via repeated `--ext`.

## 9. n8n Local Scheduler

Start n8n:

```bash
make run-n8n
```

Suggested workflow:
- Trigger: Cron
- Action: Execute Command
- Daily command: `make -C /workspace run-monthly MONTHLY_PROVIDERS=gmail,outlook GRAPH_TOKEN_CACHE_PATH=/home/node/.n8n/msal_graph_invoice_cache.bin`
- One-time/bootstrap command (manual): `make -C /workspace run-monthly MONTHLY_PROVIDERS=outlook GRAPH_INTERACTIVE_AUTH=1 GRAPH_TOKEN_CACHE_PATH=/home/node/.n8n/msal_graph_invoice_cache.bin`

Notes:
- Repo is mounted in container at `/workspace`.
- Ensure Gmail OAuth files exist in repo root if using Gmail flow.
- Import ready-to-use n8n workflow JSON files:
  - `integrations/n8n/workflows/monthly_invoices_daily.json`
  - `integrations/n8n/workflows/monthly_invoices_graph_bootstrap.json`

### 9.1 Bootstrap + Daily Runbook

```bash
# 1) Ensure Graph client id exists in repo root .env
# GRAPH_CLIENT_ID=<your-client-id>

# 2) Start/recreate n8n with .env loaded
make run-n8n

# 3) One-time Graph auth bootstrap (interactive, seeds token cache)
docker compose --env-file .env -f deploy/compose/docker-compose.dev.yml exec n8n \
  make -C /workspace run-monthly \
  MONTHLY_PROVIDERS=outlook \
  GRAPH_INTERACTIVE_AUTH=1 \
  GRAPH_TOKEN_CACHE_PATH=/home/node/.n8n/msal_graph_invoice_cache.bin

# 4) Verify env inside n8n and let daily workflow run silently
docker compose --env-file .env -f deploy/compose/docker-compose.dev.yml exec n8n printenv GRAPH_CLIENT_ID
```

Recovery when daily run reports `AUTH_REQUIRED`:

```bash
docker compose --env-file .env -f deploy/compose/docker-compose.dev.yml exec n8n \
  make -C /workspace run-monthly \
  MONTHLY_PROVIDERS=outlook \
  GRAPH_INTERACTIVE_AUTH=1 \
  GRAPH_TOKEN_CACHE_PATH=/home/node/.n8n/msal_graph_invoice_cache.bin
```

## 10. Go API

Run:

```bash
make -C apps/api-go run
```

Current endpoint:
- `GET /healthz` -> `200 ok`

`integrations/openapi/invoices.yaml` describes broader future invoice endpoints that are not fully implemented in current Go handler.

## 11. Testing and Quality

Run all root tests:

```bash
make test
```

Targeted test suites:

```bash
pytest -q tests/test_invoices_report.py tests/test_invoices_report_utils.py
pytest -q tests/test_invoice_finders.py
```

Lint/format:

```bash
make lint
make fmt
```

## 12. Historical Scripts

- `archive/` contains historical scripts and experiments retained for reference/debugging.
- Supported day-to-day entry points are the CLIs under `apps/workers-py/src/invplatform/cli`.

## 13. Meta Billing Graph API Explorer URLs

For ready-to-paste Graph API Explorer URLs (business sanity, invoices edge, ad account activities, `me/businesses`, `me/adaccounts`), see:

- `docs/META_BILLING_GRAPH_API_EXPLORER.md`
