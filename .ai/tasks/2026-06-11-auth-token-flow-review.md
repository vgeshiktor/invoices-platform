# Auth Token Flow Review

Issue:
First real governance task packet for Graph and Gmail auth-token guidance.

Desired outcome:
Verified, repo-backed auth and runbook guidance across Graph bootstrap, unattended cache reuse, `AUTH_REQUIRED` recovery, and Gmail OAuth file expectations.

Explicit non-goals:
- Product or auth code changes
- Parser, report, or CLI behavior changes outside auth documentation
- Expanding `docs/CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, or `docs/ONBOARDING.md`

Relevant docs/files:
- `README.md`
- `docs/USAGE.md`
- `Makefile`
- `apps/workers-py/src/invplatform/cli/graph_invoice_finder.py`
- `tests/test_graph_invoice_auth.py`
- `pytest.ini`

Required validation:
- `pytest -q tests/test_graph_invoice_auth.py`
- Manual doc-to-code and doc-to-Makefile consistency check for `GRAPH_INTERACTIVE_AUTH`, `GRAPH_TOKEN_CACHE_PATH`, `--interactive-auth`, `--token-cache-path`, `AUTH_REQUIRED`, `credentials.json`, and `token.json`

Known decisions:
- Reasoning level is `ai:deep`
- Maximum initial files is `6`
- This is a docs-and-workflow review first; code changes are out of scope unless repo-backed auth guidance is impossible without them

Missing decisions:
None after comparing docs, code, tests, and Makefile.

Reasoning level: `ai:deep`

Maximum initial files: `6`
