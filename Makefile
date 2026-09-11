SHELL := /bin/bash
export PATH := $(HOME)/.local/bin:$(PATH)

BACKEND := backend
FRONTEND := frontend

.PHONY: help install install-backend install-frontend up down logs ps \
        dev-api dev-web test demo optimize benchmark lint fmt migrate seed ingest clean

help:
	@echo "SIH26105 CRQ Platform"
	@echo ""
	@echo "  make install          install backend + frontend deps"
	@echo "  make up               start db + api + web (docker compose)"
	@echo "  make down             stop the stack"
	@echo "  make logs             follow stack logs"
	@echo "  make dev-api          run FastAPI locally (reload)"
	@echo "  make dev-web          run Next.js locally"
	@echo "  make test             run backend tests"
	@echo "  make demo             run the example risk scenario end to end"
	@echo "  make optimize         optimize the security budget (₹25L demo org)"
	@echo "  make benchmark        regenerate docs/benchmark.md (proof artifact)"
	@echo "  make lint             ruff check + format --check"
	@echo "  make fmt              ruff format + fix"
	@echo "  make migrate          alembic upgrade head"
	@echo "  make seed             load the demo organization"
	@echo "  make ingest           run one ingestion cycle"
	@echo "  make clean            remove caches and build artifacts"

# --- setup ---
install: install-backend install-frontend

install-backend:
	cd $(BACKEND) && uv sync

install-frontend:
	cd $(FRONTEND) && npm install --include=dev

# --- docker stack ---
up:
	docker compose up --build -d
	@echo "api:  http://localhost:8000/health"
	@echo "web:  http://localhost:3000"

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

# --- local dev ---
dev-api:
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd $(FRONTEND) && npm run dev

# --- quality ---
test:
	cd $(BACKEND) && uv run pytest

demo:
	cd $(BACKEND) && uv run python -m app.risk.demo

optimize:
	cd $(BACKEND) && uv run python -m app.optimization.demo --budget 2500000 --trials 20000

benchmark:
	cd $(BACKEND) && uv run python -m app.optimization.benchmark_cli --trials 20000

lint:
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .

fmt:
	cd $(BACKEND) && uv run ruff check --fix . && uv run ruff format .

# --- data ---
migrate:
	cd $(BACKEND) && uv run alembic upgrade head

seed:
	cd $(BACKEND) && uv run python -m app.seed.org_demo

ingest:
	cd $(BACKEND) && uv run python -m app.jobs.ingest

# --- cleanup ---
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(FRONTEND)/.next
