.PHONY: setup dev up down test lint fmt

setup: ## התקנות ראשוניות
\tpre-commit install

dev: ## הרצה מקומית של כל הסרוויסים (דוקר קומפוז)
\tdocker compose -f deploy/compose/docker-compose.dev.yml up --build

up:
\tdocker compose -f deploy/compose/docker-compose.dev.yml up -d

down:
\tdocker compose -f deploy/compose/docker-compose.dev.yml down

test:
\t$(MAKE) -C apps/api-go test
\t$(MAKE) -C apps/workers-py test

lint:
\t$(MAKE) -C apps/api-go lint
\t$(MAKE) -C apps/workers-py lint

fmt:
\t$(MAKE) -C apps/api-go fmt
\t$(MAKE) -C apps/workers-py fmt
