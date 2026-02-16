# Invoices Platform

Monorepo for invoice discovery, PDF collection, and invoice reporting across Gmail and Microsoft Graph.

## What Is Implemented

- Gmail invoice discovery and PDF download (`invplatform.cli.gmail_invoice_finder`)
- Microsoft Graph invoice discovery and PDF download (`invplatform.cli.graph_invoice_finder`)
- Monthly orchestration across providers with merge + dedup (`invplatform.cli.monthly_invoices`)
- PDF quarantine utility for non-invoice files (`invplatform.cli.quarantine_invoices`)
- Invoice parsing/report generation to JSON/CSV/Summary CSV/PDF (`invplatform.cli.invoices_report`)
- PDF report enhancements:
  - bilingual-safe rendering (Hebrew + English)
  - vendor grouping and optional vendor subtotal rows
  - configurable subtotal behavior (on/off, skip single-invoice vendors)
- Duplicate removal utility script (`scripts/remove_duplicate_invoices.py`)
- Minimal Go API service (`/healthz`) in `apps/api-go`
- Local dev stack via Docker Compose including `api-go`, `workers-py`, `db`, `mq`, and `n8n`

## Documentation Map

- `README.md` (this file): project overview + quick start + workflow map.
- `docs/USAGE.md`: full command reference and how-to usage for all current functionality.
- `docs/META_BILLING_GRAPH_API_EXPLORER.md`: ready-to-paste Graph API Explorer URLs for Meta billing diagnostics.
- `integrations/openapi/invoices.yaml`: API contract draft (broader than currently implemented Go handlers).

## Documentation Approach

The docs structure in this repo follows these principles:

- Quick orientation in `README.md`, detailed how-to/reference in `docs/USAGE.md`.
- Task-first command examples (copy/paste ready).
- Explicitly separate current behavior from future/planned API scope.

References used for this structure:

- Diataxis framework: <https://diataxis.fr/>
- Google developer documentation style guide: <https://developers.google.com/style>
- Write the Docs style/principles:
  - <https://www.writethedocs.org/guide/writing/style-guides.html>
  - <https://www.writethedocs.org/guide/writing/docs-principles.html>

## Quick Start

### Prerequisites

- Python 3.11+
- Go 1.22+ (for `api-go`)
- Docker + Docker Compose (optional, for full local stack)

### Install dependencies (local Python workflow)

```bash
pip install -r requirements.txt
```

### Run tests

```bash
make test
```

### Run main workflows

```bash
# Gmail finder
make run-gmail START_DATE=2026-01-01 END_DATE=2026-02-01

# Graph finder
make run-graph START_DATE=2026-01-01 END_DATE=2026-02-01 GRAPH_CLIENT_ID=<your-client-id>

# Monthly orchestration (current month by default)
make run-monthly GRAPH_CLIENT_ID=<your-client-id>

# Parse invoices + build reports (JSON/CSV/summary/PDF)
make run-report REPORT_INPUT_DIR=invoices/invoices_01_2026

# Quarantine likely non-invoice PDFs
make quarantine
```

For complete options and examples, use `docs/USAGE.md`.

## Key Outputs

- Provider fetch outputs:
  - `invoices/invoices_gmail_MM_YYYY`
  - `invoices/invoices_outlook_MM_YYYY`
- Consolidated monthly outputs:
  - `invoices/invoices_MM_YYYY`
  - `invoices/invoices_MM_YYYY/run_summary.json`
- Report outputs:
  - `report-*.json`, `report-*.csv`, `report-*.summary.csv`, `report-*.pdf` (or custom output paths)

## API Status (Current)

- Implemented in Go:
  - `GET /healthz` -> `200 ok`
- Not yet implemented in current Go handler:
  - the full invoice CRUD suggested by `integrations/openapi/invoices.yaml`

## Repo Layout

```text
invoices-platform/
├─ apps/
│  ├─ api-go/
│  └─ workers-py/
├─ docs/
│  └─ USAGE.md
├─ deploy/
├─ integrations/
├─ scripts/
├─ invoices/
└─ README.md
```

## Notes

- `archive/` contains historical finder scripts kept for comparison/debugging. Current supported entry points are under `apps/workers-py/src/invplatform/cli`.
- `docs/ONBOARDING.md`, `docs/ARCHITECTURE.md`, and `docs/CONTRIBUTING.md` are currently placeholders.
