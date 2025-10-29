# Invoices Platform

invoices-platform/
├─ apps/
│  ├─ api-go/
│  │  ├─ cmd/invoicer/main.go
│  │  ├─ internal/{domain,usecase,adapters}
│  │  ├─ go.mod
│  │  └─ Makefile
│  └─ workers-py/
│     ├─ src/{workers,pipelines,adapters,models}
│     ├─ tests/
│     ├─ pyproject.toml
│     ├─ uv.lock              # יווצר ע״י uv
│     ├─ Makefile
│     └─ README.md
├─ integrations/
│  ├─ n8n/{docker-compose.yml,n8n.env.example,workflows/}
│  └─ openapi/invoices.yaml
├─ deploy/
│  ├─ compose/docker-compose.dev.yml
│  ├─ docker/{Dockerfile.api-go,Dockerfile.workers-py}
│  └─ k8s/ (later)
├─ storage/                  # volume לקבצי PDF (dev)
├─ docs/{ADR,ONBOARDING.md,ARCHITECTURE.md,CONTRIBUTING.md}
├─ .devcontainer/{devcontainer.json,Dockerfile}
├─ .pre-commit-config.yaml
├─ .github/workflows/ci.yml
├─ .env.example
├─ Makefile
└─ README.md


## Email Discovery Toolkit

Utility scripts for ad-hoc invoice hunting live under `archive/` and evolve across versions. Older scripts are kept for comparison/debugging, while `archive/graph_invoice_finder.v3.5.2.py` is the recommended entry point.

### Graph Invoice Finder (v3.5.2)

- Uses Microsoft Graph `$search` queries (Hebrew + English keywords) with client-side scoring to surface invoices, receipts, and payment confirmations.
- Supports sender/domain boosting, negative keywords, subject regex boosts, and trusted provider lists so you can tune relevance without patching code.
- Provides validation helpers (`--explain`, `--threshold-sweep`, `--save-candidates`, `--save-nonmatches`) plus optional attachment download for final matches.
- Emits JSON/CSV exports and per-strategy summaries to help validate coverage before wiring results back into the pipeline.

Quick start (requires `msal`, `pandas`, `requests`):

```bash
python archive/graph_invoice_finder.v3.5.2.py \
  --client-id "<entra_public_client_id>" \
  --lookback-days 90 \
  --out-json outputs/invoices.json \
  --out-csv outputs/invoices.csv \
  --threshold-sweep 0.30,0.45,0.55
```

### Outlook Search Filters

The files `search_filter_outlook.v1.json` and `search_filter_outlook.v2.json` capture Outlook portal saved searches that mirror the script heuristics (keyword mix, date windows). Importing them is useful when you want to eyeball results inside Outlook before running the automation end-to-end.
