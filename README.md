# AI-Powered Automatic Block Planning — Backend

Backend service for the **SIH Railways AI-Powered Automatic Block Planning** system.

The backend is built with **Django + Django REST Framework (DRF)**, uses **PostgreSQL (Supabase)** as the database, **Celery + Redis** for asynchronous task execution & live train tracking, and integrates with **RailKit API** for real-time timetable and train movement data.

---

## 🚀 Key Features

- **Railway Corridor & Asset Management**: Tracks railway sections, station codes (`source_station_code`, `destination_station_code`), and corridor assets.
- **Maintenance Task Management**: Tracks pending maintenance activities, duration requirements, severity ratings, and deadlines.
- **Train Schedules & Live Movements**: Manages scheduled timetables (including weekly running patterns and day offsets) and syncs actual train movements.
- **Automated Timetable & Live Tracking Sync**: Celery periodic tasks continuously poll timetable data and track live train progress via the RailKit API.
- **Conflict Detection Engine**: Detects time-window collisions between scheduled/actual train movements and proposed maintenance blocks.
- **Feasible Maintenance Window Calculation**: Computes optimal non-conflicting gaps inside block windows to safely schedule maintenance tasks.
- **1-Click Bruno API Test Suite**: Automated end-to-end API test collection for every endpoint.

---

## 1. Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python** (>= 3.12) | Core language |
| **Django** (6.x) | Web framework |
| **Django REST Framework** | REST API framework |
| **PostgreSQL** (Supabase) | Primary relational database |
| **Celery** (5.6+) | Asynchronous task queue & periodic scheduler |
| **Redis** (Hosted / Local) | Celery message broker & result backend |
| **RailKit API** | Live train tracking & timetable data provider |
| **psycopg (v3)** | Modern PostgreSQL driver |
| **dj-database-url** | Database URL configuration |
| **django-cors-headers** | Cross-Origin Resource Sharing (CORS) |
| **WhiteNoise** | Static files serving in production |
| **Gunicorn** | WSGI production web server |
| **Bruno** | Fast, git-friendly API client & test suite |
| **Docker & Compose** | Containerized development and deployment |

---

## 2. Project Structure

```text
backend/
├── Makefile                          # Development & Docker orchestration shortcuts
├── COMMANDS.md                       # Comprehensive CLI & Makefile guide
├── docker-compose.yml                # Multi-container Docker configuration
├── manage.py                         # Django management CLI
├── pyproject.toml / requirements.txt # Project dependencies
├── Dockerfile / .dockerignore        # Production container specs
├── .env.example                      # Environment variables template
│
├── bruno/                            # Bruno API 1-Click Test Collection
│   ├── bruno.json
│   ├── environments/                 # Local & Production environment variables
│   ├── 01-Corridors-Sections/
│   ├── 02-Assets/
│   ├── 03-Maintenance-Tasks/
│   ├── 04-Trains/
│   ├── 05-Train-Schedules/
│   ├── 06-Train-Movements/
│   └── 07-Block-Windows/
│
├── config/                           # Django project configuration
│   ├── settings.py                   # App settings, DB & Celery broker config
│   ├── celery.py                     # Celery app initialization & task discovery
│   ├── router.py                     # DRF API Router definitions
│   ├── urls.py                       # Root URL routing (/railways/)
│   └── wsgi.py / asgi.py
│
└── apps/                             # Modular Django applications
    ├── corridors/                    # Railway sections & station codes
    ├── assets/                       # Railway infrastructure assets
    ├── maintenance/                  # Maintenance tasks & scheduling deadlines
    ├── trains/                       # Trains, Schedules, Movements & RailKit sync
    │   ├── services/                 # Live tracking, timetable sync & parser logic
    │   └── tasks.py                  # Celery background tasks
    └── blocks/                       # Maintenance block windows & conflict engine
        └── services.py               # Conflict detection & feasible gap algorithms
```

---

## 3. Base API & Timezone

All API routes are served under `/railways/`:

- **Local API**: `http://127.0.0.1:8000/railways/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`

### Timezone: Indian Standard Time (IST - Asia/Kolkata)
All datetime fields accept and return values in formatted IST (`YYYY-MM-DD HH:MM:SS`):
```text
2026-09-04 14:30:00
```

---

## 4. API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **Railway Sections** | | |
| `GET / POST` | `/railways/sections/` | List or create railway sections (with station codes) |
| `GET / PUT / DELETE` | `/railways/sections/{id}/` | Retrieve, update, or delete a section |
| **Assets** | | |
| `GET / POST` | `/railways/assets/` | List or create railway assets |
| `GET / PUT / DELETE` | `/railways/assets/{id}/` | Retrieve, update, or delete an asset |
| **Maintenance Tasks** | | |
| `GET / POST` | `/railways/maintenances/` | List or create maintenance tasks |
| `GET / PUT / DELETE` | `/railways/maintenances/{id}/` | Retrieve, update, or delete a maintenance task |
| **Trains** | | |
| `GET / POST` | `/railways/trains/` | List or create trains |
| `GET / PUT / DELETE` | `/railways/trains/{id}/` | Retrieve, update, or delete a train |
| **Train Schedules** | | |
| `GET / POST` | `/railways/schedules/` | List or create weekly timetables |
| `GET / PUT / DELETE` | `/railways/schedules/{id}/` | Retrieve, update, or delete a schedule |
| **Train Movements** | | |
| `GET / POST` | `/railways/train-movements/` | List or create daily train movements (actual times) |
| `GET / PUT / DELETE` | `/railways/train-movements/{id}/` | Retrieve, update, or delete a train movement |
| **Block Windows & AI Engines** | | |
| `GET / POST` | `/railways/blocks/` | List or create maintenance block windows |
| `GET / PUT / DELETE` | `/railways/blocks/{id}/` | Retrieve, update, or delete a block window |
| `POST` | `/railways/blocks/check-conflict/` | **Conflict Detection Engine**: Detect overlapping trains |
| `POST` | `/railways/blocks/feasible-windows/` | **Feasible Window Engine**: Find safe maintenance gaps |

---

## 5. Sample API Payloads

### 5.1 Create Railway Section (`POST /railways/sections/`)
```json
{
  "section_name": "New Delhi - Ghaziabad Section",
  "origin_station": "New Delhi",
  "source_station_code": "NDLS",
  "end_station": "Ghaziabad Junction",
  "destination_station_code": "GZB",
  "distance": 25.6,
  "status": true
}
```

### 5.2 Conflict Check (`POST /railways/blocks/check-conflict/`)
```json
{
  "section": 1,
  "maintenance_start": "2026-09-04 02:00:00",
  "maintenance_end": "2026-09-04 05:00:00"
}
```
**Response:**
```json
{
  "has_conflict": true,
  "conflict_count": 1,
  "conflicts": [
    {
      "train_number": "12004",
      "train_name": "Lucknow Shatabdi",
      "entry_time": "2026-09-04 02:30:00",
      "exit_time": "2026-09-04 03:15:00"
    }
  ]
}
```

### 5.3 Feasible Windows Calculation (`POST /railways/blocks/feasible-windows/`)
```json
{
  "task_id": "TASK-OHE-101",
  "block_id": 1
}
```
**Response:**
```json
{
  "task_id": "TASK-OHE-101",
  "block_id": 1,
  "section": "New Delhi - Ghaziabad Section",
  "required_duration_minutes": 120,
  "feasible": true,
  "windows": [
    {
      "start": "2026-09-04 01:00:00",
      "end": "2026-09-04 03:00:00",
      "duration_minutes": 120
    }
  ]
}
```

---

## 6. Celery Background & Periodic Tasks

Celery handles periodic timetable synchronizations and live tracking:

| Task Name | Schedule | Description |
| :--- | :--- | :--- |
| `apps.trains.tasks.sync_relevant_live_trains` | Every 3 minutes | Selects active corridor trains and queries RailKit live tracking |
| `apps.trains.tasks.sync_all_timetables` | Daily at 02:00 AM | Syncs full station timetable data across all active sections |

---

## 7. Running the Project (Makefile & Docker)

For detailed workflows, refer to [COMMANDS.md](COMMANDS.md).

### Quick Commands:
```bash
# 1. Hybrid Mode: Run Celery in Docker & Django Server locally
make dev-local

# 2. Run All Services in Docker (Web + Celery Worker + Celery Beat)
make up

# 3. Stop all Docker services
make down

# 4. Database Migrations
make migrate
make makemigrations
```

---

## 8. 🧪 1-Click Bruno API Test Suite

The repository includes a ready-to-use **[Bruno Collection](bruno/)** that tests all API endpoints in one click.

### How to Run:

#### Option A: Using the Bruno Desktop App (GUI)
1. Open **Bruno**.
2. Click **Open Collection** and select the [`bruno/`](bruno/) folder in this repository.
3. Select the **Local** environment (top right dropdown).
4. Right-click the collection name (`Smart-Railways-Backend`) and click **Run Collection** to execute all tests with 1 click!

#### Option B: Using Bruno CLI
```bash
# Install Bruno CLI (if not already installed)
npm install -g @usebruno/cli

# Run all test suites against Local environment
bru run bruno/ --env Local
```
