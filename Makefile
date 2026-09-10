.PHONY: help install up down restart logs backend frontend local-backend local-worker local-frontend local-frontend-build migrate test lint format

help:
	@echo "ThinkTank Monitor commands:"
	@echo "  make install   install backend and frontend dependencies"
	@echo "  make up        start Docker services"
	@echo "  make down      stop Docker services"
	@echo "  make backend   start FastAPI backend"
	@echo "  make frontend  start Next.js frontend"
	@echo "  make local-backend   start local FastAPI on 8001 with isolated queue"
	@echo "  make local-worker    start local Celery worker on isolated queue"
	@echo "  make local-frontend  start local Next.js on 3001"
	@echo "  make local-frontend-build  build frontend after checking local dev port"
	@echo "  make migrate   run Alembic migrations"
	@echo "  make test      run backend tests"
	@echo "  make lint      run frontend lint"

install:
	cd backend && poetry install
	cd frontend && npm install

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

logs:
	docker compose logs -f

backend:
	cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

local-backend:
	powershell -ExecutionPolicy Bypass -File scripts/start-local-backend.ps1

local-worker:
	powershell -ExecutionPolicy Bypass -File scripts/start-local-worker.ps1

local-frontend:
	powershell -ExecutionPolicy Bypass -File scripts/start-local-frontend.ps1

local-frontend-build:
	powershell -ExecutionPolicy Bypass -File scripts/build-local-frontend.ps1

migrate:
	cd backend && poetry run alembic upgrade head

test:
	cd backend && poetry run pytest

lint:
	cd frontend && npm run lint

format:
	cd backend && poetry run ruff format .
