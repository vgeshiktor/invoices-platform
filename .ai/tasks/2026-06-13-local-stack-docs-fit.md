# Local Stack Docs Fit

Issue:
Execute the `local-stack-docs-fit` benchmark task against the current Compose stack, local lifecycle commands, and API-status docs.

Desired outcome:
Local stack docs match current `make dev`, `make up`, `make down`, `make run-n8n`, Compose services, and the implemented Go API surface.

Explicit non-goals:
- New infrastructure or service additions
- Expanding API docs beyond the currently implemented `/healthz`
- Changes outside local stack, n8n, or current API-status wording

Relevant docs/files:
- `README.md`
- `docs/USAGE.md`
- `Makefile`
- `deploy/compose/docker-compose.dev.yml`
- `apps/api-go/cmd/invoicer/main.go`
- `.env.example`

Required validation:
- Confirm documented stack commands match current Makefile targets.
- Confirm service names and ports match Compose.
- Confirm no unsupported Go API endpoints are described as implemented.
- Run `docker compose --env-file .env.example -f deploy/compose/docker-compose.dev.yml config --services` if Docker is available.

Known decisions:
- Root `.env.example` should reflect the current Graph env name used by Make, Compose, and monthly orchestration.
- Reasoning level is `ai:standard`.

Missing decisions:
None after comparing docs, Compose, and the Go API entrypoint.

Reasoning level: `ai:standard`

Maximum initial files: `6`
