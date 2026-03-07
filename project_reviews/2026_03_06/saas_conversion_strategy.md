# 🚀 SaaS Conversion Strategy: Invoices-Platform

As **Atlas**, here is the architectural blueprint to transform the current local ETL scripts into a **Top 1% Enterprise SaaS Platform**. We are moving from single-user desktop execution to a massively multi-tenant, cloud-native architecture.

## 1. Multi-Tenancy & Data Isolation (The "Pool" Model)
To support thousands of companies without immense infrastructure overhead, we will use a **Logical Pool Model** for the database.
- **Database (PostgreSQL):** All tenant data lives in the same schema, but *every* table must have a `tenant_id` column.
- **Data Protection:** We will implement **Row-Level Security (RLS)** in PostgreSQL. The Go API and Python workers will set the Postgres session variable `tenant_id` at the start of every transaction. This guarantees that a bug in our application code cannot leak Invoice A to Tenant B.

## 2. Core System Architecture (Event-Driven)
We must decouple the data ingest (fetching emails) from the heavy processing (parsing PDFs).

- **Control Plane (Go API):**
  - Handles user authentication, API keys, dashboard requests, and billing events.
  - Exposes REST/GraphQL endpoints for frontends to query invoices.
  - Manages tenant settings (e.g., "Connect my Gmail", "Connect my Outlook").
- **Ingestion Workers (Go or Python):**
  - Fast, lightweight cron-jobs or webhooks that monitor tenant inboxes via MS Graph API / Gmail PubSub.
  - When an email with a PDF arrives, they download the PDF to an S3 bucket (with paths like `s3://invoices-data/{tenant_id}/{year}/{month}/{uuid}.pdf`) and push a message to RabbitMQ: `{"event": "invoice_ingested", "s3_uri": "...", "tenant_id": "..."}`.
- **Data Plane / Processing Workers (Python):**
  - Listen to RabbitMQ.
  - Pull the PDF from S3.
  - Run the heavy extraction logic (shifting from massive Regex to LLM-structured JSON extraction + Regex fallbacks).
  - Write the parsed [InvoiceRecord](file:///Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/apps/workers-py/src/invplatform/cli/invoices_report.py#103-147) to PostgreSQL.

## 3. Identity, Auth & RBAC
- **Authentication:** Integrate **Auth0**, **Clerk**, or **WorkOS** for robust identity management. Do not roll your own auth. This gives us SAML/SSO for enterprise clients immediately.
- **OAuth for Mail Providers:** The Go API must manage the OAuth handshakes for Gmail and Outlook on behalf of the tenants, securely storing refresh tokens in a KMS-encrypted Vault or encrypted Postgres columns.

## 4. Metering & Billing
- **Strategy:** Usage-based billing (e.g., "$0.10 per parsed invoice").
- **Implementation:** Stripe integration. When the Python worker successfully writes an invoice to the DB, it emits an `InvoiceParsed` event. A dedicated Go microservice listens for this and increments the customer's usage counter in Stripe.

## 5. Missing Components for Production Readiness
Currently, the repo is a raw data extraction tool. To be a SaaS, you are missing:
1. **The Web Dashboard (Frontend):** A Next.js, React, or Vue application where users can log in, view their parsed invoices, run reports, and fix OCR/Parsing errors manually.
2. **Human-in-the-Loop (HITL) Queue:** If the parser confidence is low, the invoice should be flagged as "Needs Review" in the dashboard, rather than silently failing or outputting bad data to a CSV.
3. **Webhooks / API Out:** Enterprise SaaS lives and dies by integrations. Tenants will want us to POST parsed invoices directly to their ERPs (Netsuite, Priority, SAP) via outgoing webhooks.
4. **Audit Logging:** Every action (who connected an email, who manually edited an automated invoice amount) must be logged immutably for compliance.
5. **Infrastructure as Code (IaC):** Unify the deployment using Terraform to provision Kubernetes (EKS/GKE), managed RDS (Postgres), managed queuing, and S3.

## Summary of the North Star Architecture
1. **User** logs into Next.js App $\rightarrow$ Authenticated via Clerk.
2. **User** authorizes Gmail $\rightarrow$ Go API stores OAuth refresh token securely.
3. **Go Worker** polls Gmail $\rightarrow$ finds PDF $\rightarrow$ saves to S3 $\rightarrow$ publishes to RabbitMQ.
4. **Python Worker** consumes message $\rightarrow$ runs LLM/Regex extraction $\rightarrow$ saves to Postgres.
5. **Billing Service** logs usage to Stripe.
6. **User** sees the invoice appear in their Dashboard in real-time.
