.PHONY: help install up down restart logs backend frontend migrate test lint format

help:
	@echo "ThinkTank Monitor commands:"
	@echo "  make install   install backend and frontend dependencies"
	@echo "  make up        start Docker services"
	@echo "  make down      stop Docker services"
	@echo "  make backend   start FastAPI backend"
	@echo "  make frontend  start Next.js frontend"
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

migrate:
	cd backend && poetry run alembic upgrade head

test:
	cd backend && poetry run pytest

lint:
	cd frontend && npm run lint

format:
	cd backend && poetry run black app