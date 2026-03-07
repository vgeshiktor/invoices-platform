# 🏗 Architectural & Code Review: invoices-platform

As **Atlas**, I have completed Phase 1: Deep Codebase Review of `invoices-platform`. Here is my unvarnished, staff-level engineering assessment of the current state, and the technical debt we must clear to reach a scalable SaaS architecture.

## 1. Current State Assessment
The system is currently built as a **Script-based ETL Pipeline** meant for local or cron-based single-user execution.
- **Data Flow:** Mails are fetched (Gmail/Graph) $\rightarrow$ PDFs downloaded locally $\rightarrow$ `fitz`/[pdfminer](file:///Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/apps/workers-py/src/invplatform/cli/invoices_report.py#541-551) parses text via massive Regex rulesets $\rightarrow$ outputs dumped to JSON/CSV on the local filesystem.
- **Persistence:** There is no actual operational database utilized by the Python workers. `postgres` and `rabbitmq` exist in [docker-compose.dev.yml](file:///Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/deploy/compose/docker-compose.dev.yml), but [monthly_invoices.py](file:///Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/apps/workers-py/src/invplatform/cli/monthly_invoices.py) and the CLI tools only read/write to the local [invoices/](file:///Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/apps/workers-py/src/invplatform/cli/invoices_report.py#2088-2091) directory.
- **Go API:** The `apps/api-go/` service is a hollow shell containing only a `/healthz` endpoint.
- **Coupling:** The orchestration logic (`monthly_invoices.py`) invokes other Python modules as `subprocess.run(...)` rather than calling them as imported library functions.

## 2. Technical Debt & Bottlenecks
1. **The PDF Parsing Monolith (`invoices_report.py` - 2,600+ lines):**
   - **Fragility:** Parsing relies entirely on hundreds of hardcoded Hebrew/English regexes, substring coordinates, and vendor-specific edge cases (e.g., `extract_partner_totals_from_text`, `find_municipal_invoice_id`). This will break instantly as vendors change HTML/PDF layouts.
   - **Maintenance Nightmare:** Adding a new vendor requires writing brittle regex. This is not scalable for a multi-tenant SaaS.
2. **Subprocess Orchestration:**
   - Using `subprocess.run` inside Python to call other Python scripts breaks application state, complicates error handling, creates zombie processes, and makes testing incredibly difficult.
3. **Lack of Persistence Layer:**
   - Filesystem-based state (`invoices/`) prevents horizontal scaling or API integrations.
4. **State Management & Idempotency:**
   - Relying on local SHA-256 deduplication works for one user on one machine, but fails miserably in a distributed/cloud environment.

## 3. Code-Level Improvements (Short-Term Refactoring)
Before we can convert this to a SaaS, we need to clean the foundation:
- **Refactor `monthly_invoices.py`**: Replace `subprocess.run` with direct module imports and function calls (e.g., `gmail_finder.run(...)`).
- **Decompose `invoices_report.py`**: Break the 2600-line monolith into a plugin-based architecture or Strategy Pattern. Create an `IInvoiceParser` interface, with separate classes like `PartnerInvoiceParser`, `MunicipalInvoiceParser`, etc.
- **Database Integration**: Actually connect the Python workers to PostgreSQL via SQLAlchemy or asyncpg to store `InvoiceRecord` entities rather than CSVs.

## 4. Architectural Improvements (Long-Term SaaS Vision)
To build a top 1% SaaS, we must transition to an **Event-Driven Architecture**:
1. **Ingestion Layer (Edge):** Webhooks (via SendGrid/Mailgun) or scheduled background workers (Celery/Temporal) ingest emails asynchronously.
2. **Event Bus (RabbitMQ/Kafka):** Emits an `InvoiceReceived` event.
3. **Parsing Workers (Data Plane - Python):** Consume the event. Instead of brittle Regex, we should utilize **LLM-based structured extraction** (e.g., passing the PDF text to an LLM to reliably extract JSON matching our `InvoiceRecord` schema), falling back to Regex only for strict legacy vendors.
4. **API Layer (Control Plane - Go):** The Go service becomes the user-facing GraphQL/REST API to query invoices, manage tenant settings, and serve the UI dashboard, reading from PostgreSQL.

---
_Next Step: I will draft the SaaS Conversion Strategy (Phase 3), focusing on Multi-Tenancy, Auth, and Cloud-Native scalable deployment._
