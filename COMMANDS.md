# Backend CLI & Makefile Commands Reference

This guide details all available `make` commands and workflows for running, developing, and managing the **Smart-Railways Backend**.

---

## ⚡ Quick Start Workflows

### Option 1: Run Everything in Docker (Full Containerization)
Use this mode if you want everything (Django Web Server, Celery Worker, Celery Beat Scheduler, and Redis) running completely inside Docker containers.

```bash
# Start all containers in foreground (logs streamed to terminal)
make up

# OR start all containers in background (detached mode)
make up-d

# Stop all containers
make down
```

---

### Option 2: Hybrid Mode (Docker Services + Local Server)
Use this mode when developing the Django application locally on your machine (with hot reloading and interactive debugging), while offloading Redis and Celery to Docker.

```bash
# Starts Redis, Celery & Beat in Docker, then runs Django server on localhost:8000
make dev-local
```

> **Note:** If you want to start only the background services without launching the local server automatically:
> ```bash
> make dev-services
> ```
> And when you want to stop the background services:
> ```bash
> make down
> ```

---

### Option 3: Redis Only in Docker (Run Celery & Server Locally)
If you want to run Redis in Docker, but run both the Celery workers and Django server on your host machine:

```bash
# 1. Start Redis in Docker
make dev-redis

# 2. Run Celery Worker locally (in a separate terminal)
uv run celery -A config worker --loglevel=info

# 3. Run Celery Beat locally (in a separate terminal)
uv run celery -A config beat --loglevel=info

# 4. Run Django server locally
uv run python manage.py runserver
```

---

## 📖 Complete Command Reference

### 🐳 Docker Management

| Command | Action | Underlying Command |
| :--- | :--- | :--- |
| `make up` | Start all services in foreground | `docker compose up` |
| `make up-d` | Start all services in background | `docker compose up -d` |
| `make down` | Stop and remove all containers | `docker compose down` |
| `make restart` | Restart all running containers | `docker compose restart` |
| `make build` | Rebuild all Docker images | `docker compose build` |
| `make logs` | Stream logs from all services | `docker compose logs -f` |
| `make logs-web` | Stream logs for Django web service | `docker compose logs -f web` |
| `make logs-celery`| Stream logs for Celery worker & beat | `docker compose logs -f celery celery-beat` |
| `make logs-redis` | Stream logs for Redis service | `docker compose logs -f redis` |

---

### 💻 Hybrid & Local Development

| Command | Action | Details |
| :--- | :--- | :--- |
| `make dev-local` | Hybrid development mode | Starts `redis`, `celery`, `celery-beat` in Docker, runs `manage.py runserver` locally |
| `make dev-services` | Background services in Docker | Starts `redis`, `celery`, and `celery-beat` in background |
| `make dev-redis` | Redis only | Starts only Redis container on `localhost:6379` |

---

### 🗄️ Database & Django Operations

| Command | Action | Environment |
| :--- | :--- | :--- |
| `make migrate` | Apply database migrations | Local Python environment |
| `make makemigrations` | Create new migration files | Local Python environment |
| `make docker-migrate` | Apply migrations inside container | Docker `web` container |
| `make shell` | Open Django interactive shell | Local Python environment |
| `make docker-shell` | Open Django shell inside container | Docker `web` container |
| `make superuser` | Create an admin superuser | Local Python environment |
| `make test` | Run test suite | Local Python environment |

---

### 🧹 Utilities

| Command | Action | Description |
| :--- | :--- | :--- |
| `make help` | Show command helper | Prints colorized list of all available commands |
| `make clean` | Clean build artifacts | Removes `__pycache__`, `*.pyc`, `.pytest_cache`, and egg-info |

---

## ⚙️ Environment Variables Summary

Make sure your `.env` file contains the following configurations:

```dotenv
# Database (PostgreSQL / Supabase)
DATABASE_URL=postgresql://user:password@host:5432/postgres

# Redis
# Use localhost for local runs, or let Docker Compose override it with redis://redis:6379/0
REDIS_URL=redis://localhost:6379/0

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True
```
