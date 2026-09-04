# ==============================================================================
# Smart-Railways Backend - Makefile
# ==============================================================================

.DEFAULT_GOAL := help
.PHONY: help up up-d down restart build logs logs-web logs-celery logs-redis \
        dev-local dev-services dev-redis docker-migrate migrate makemigrations \
        shell docker-shell superuser test clean

# ------------------------------------------------------------------------------
# Configuration & Python Environment Detection
# ------------------------------------------------------------------------------
DOCKER_COMPOSE ?= docker compose

# Automatically use 'uv run python' if available, otherwise virtual environment or python3
PYTHON := $(shell if command -v uv >/dev/null 2>&1; then echo "uv run python"; \
                  elif [ -f .venv/bin/python ]; then echo ".venv/bin/python"; \
                  elif command -v python3 >/dev/null 2>&1; then echo "python3"; \
                  else echo "python"; fi)

# ------------------------------------------------------------------------------
# Help Screen
# ------------------------------------------------------------------------------
help:
	@echo "========================================================================"
	@echo "                   Backend Management Commands"
	@echo "========================================================================"
	@echo "🚀 DOCKER (ALL SERVICES):"
	@echo "  make up               - Run all services (web, celery, beat) in Docker"
	@echo "  make up-d             - Run all services in Docker (detached / background)"
	@echo "  make down             - Stop and remove all Docker containers"
	@echo "  make restart          - Restart all Docker containers"
	@echo "  make build            - Rebuild all Docker containers"
	@echo "  make logs             - Tail logs of all running Docker containers"
	@echo ""
	@echo "💻 HYBRID MODE (DOCKER SERVICES + LOCAL SERVER):"
	@echo "  make dev-local        - Start Celery & Beat in Docker, run Web Server LOCALLY"
	@echo "  make dev-services     - Start background services (Celery, Beat) in Docker"
	@echo ""
	@echo "📦 DATABASE & DJANGO:"
	@echo "  make migrate          - Apply migrations locally"
	@echo "  make makemigrations   - Generate new migrations locally"
	@echo "  make docker-migrate   - Apply migrations inside Docker container"
	@echo "  make shell            - Open Django shell locally"
	@echo "  make docker-shell     - Open Django shell inside Docker"
	@echo "  make superuser        - Create superuser locally"
	@echo ""
	@echo "🛠️ UTILITIES & MAINTENANCE:"
	@echo "  make test             - Run tests"
	@echo "  make clean            - Remove cache, bytecode, and temp files"
	@echo "========================================================================"

# ------------------------------------------------------------------------------
# Mode 1: All Services in Docker
# ------------------------------------------------------------------------------
## Run all services in Docker in foreground
up:
	@echo "Starting all services (web, celery, celery-beat, redis) in Docker..."
	$(DOCKER_COMPOSE) up --build

## Run all services in Docker in background (detached)
up-d:
	@echo "Starting all services in Docker (detached mode)..."
	$(DOCKER_COMPOSE) up -d --build

## Stop all Docker containers
down:
	@echo "Stopping Docker containers and removing orphans..."
	$(DOCKER_COMPOSE) down --remove-orphans

## Restart all Docker containers
restart:
	@echo "Restarting Docker containers..."
	$(DOCKER_COMPOSE) restart

## Rebuild Docker containers
build:
	@echo "Building Docker containers..."
	$(DOCKER_COMPOSE) build --no-cache

## View logs from all services
logs:
	$(DOCKER_COMPOSE) logs -f

logs-web:
	$(DOCKER_COMPOSE) logs -f web

logs-celery:
	$(DOCKER_COMPOSE) logs -f celery celery-beat

logs-redis:
	$(DOCKER_COMPOSE) logs -f redis

# ------------------------------------------------------------------------------
# Mode 2: Hybrid Mode (Backend Services on Docker + Local Web Server)
# ------------------------------------------------------------------------------
## Start backend services (celery, celery-beat) in Docker, then run Django server locally
dev-local:
	@echo "Starting background services (celery, celery-beat) in Docker..."
	$(DOCKER_COMPOSE) up -d --build celery celery-beat
	@echo ""
	@echo "========================================================================"
	@echo "Backend services are running in Docker."
	@echo "Starting Django server locally on http://localhost:8000 using: $(PYTHON)"
	@echo "Press Ctrl+C to stop local server (run 'make down' to stop Docker services)"
	@echo "========================================================================"
	@echo ""
	$(PYTHON) manage.py runserver 0.0.0.0:8000

## Start only backend background services in Docker (detached)
dev-services:
	@echo "Starting Celery worker and Celery Beat in Docker..."
	$(DOCKER_COMPOSE) up -d --build celery celery-beat
	@echo "Background services are running! You can now run your local server."


# ------------------------------------------------------------------------------
# Django / Database Shortcuts
# ------------------------------------------------------------------------------
migrate:
	$(PYTHON) manage.py migrate

makemigrations:
	$(PYTHON) manage.py makemigrations

docker-migrate:
	$(DOCKER_COMPOSE) run --rm web python manage.py migrate

shell:
	$(PYTHON) manage.py shell

docker-shell:
	$(DOCKER_COMPOSE) run --rm web python manage.py shell

superuser:
	$(PYTHON) manage.py createsuperuser

test:
	$(PYTHON) manage.py test

test-api:
	@echo "Running Bruno API test suite against local server..."
	npx @usebruno/cli run bruno/ --env Local


# ------------------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------------------
clean:
	@echo "Cleaning cache and bytecode files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@echo "Done!"
