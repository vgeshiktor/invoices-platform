.PHONY: setup dev up down test lint fmt

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

lint:
	$(MAKE) -C apps/api-go lint
	$(MAKE) -C apps/workers-py lint

fmt:
	$(MAKE) -C apps/api-go fmt
	$(MAKE) -C apps/workers-py fmt
