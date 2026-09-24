.PHONY: dev api web test test-pg lint up down

api:        ## Run the FastAPI backend (SQLite + offline fallbacks)
	cd backend && uvicorn app.main:app --reload --port 8000

web:        ## Run the Next.js frontend
	cd frontend && npm run dev

test:       ## Backend unit + integration + AI evaluation tests
	cd backend && python -m pytest

lint:
	cd frontend && npm run lint && npm run typecheck

up:         ## Full stack: Postgres, Redis, Qdrant, Neo4j, API, worker, web
	docker compose up --build

down:
	docker compose down
