.PHONY: help install dev up down logs test migrate clean

help: ## Show this help message
	@echo "FameShield - AI Athlete Protection Platform"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	cd backend && pip install -r requirements.txt
	cd backend && playwright install chromium

dev: ## Start development environment with docker-compose
	docker-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/api/docs"
	@echo ""

up: dev ## Alias for 'dev'

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

logs-backend: ## Show backend logs only
	docker-compose logs -f backend

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	cd backend && alembic revision --autogenerate -m "$(MESSAGE)"

test: ## Run tests
	cd backend && pytest

test-cov: ## Run tests with coverage
	cd backend && pytest --cov=app --cov-report=html

clean: ## Clean up containers and volumes
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

shell: ## Open a shell in the backend container
	docker-compose exec backend bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U fameshield -d fameshield

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

format: ## Format code with black
	cd backend && black app/

lint: ## Run linter
	cd backend && flake8 app/

init-db: ## Initialize database with sample data
	docker-compose exec backend python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
