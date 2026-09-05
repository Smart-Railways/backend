# AI-Powered Automatic Block Planning — Backend

Backend service for the **SIH Railways AI-Powered Automatic Block Planning** system.

The backend is built with **Django + Django REST Framework (DRF)**, uses **PostgreSQL (Supabase)** as the database, **Celery + Redis** for asynchronous task execution & live train tracking, and integrates with **RailKit API** for real-time timetable and train movement data.

---

## 🚀 Key Features

- **Railway Corridor & Asset Management**: Tracks railway sections, station codes (`source_station_code`, `destination_station_code`), and corridor assets with department categorization.
- **Maintenance Task Management**: Tracks pending maintenance activities, duration requirements, severity ratings, urgency levels, and deadlines.
- **Train Schedules & Live Movements (Read-Only)**: Exposes scheduled timetables (including weekly running patterns and day offsets) and daily train movements (actual times and delays), automatically managed and kept up-to-date by background sync tasks.
- **Live Operations Aggregation**: Aggregated live tracking API combining master train data, scheduled timetable, and live-synced movement info with calculated delay in minutes.
- **Automated Timetable & Live Tracking Sync**: Celery periodic tasks continuously poll timetable data and track live train progress via the RailKit API.
- **Conflict Detection Engine**: Detects time-window collisions between scheduled/actual train movements and proposed maintenance blocks.
- **Feasible Maintenance Window Calculation**: Computes optimal non-conflicting gaps inside block windows to safely schedule maintenance tasks.
- **1-Click Bruno API Test Suite**: Complete automated end-to-end API test collection for every endpoint.

---

## 1. Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python** (>= 3.12) | Core programming language |
| **Django** (6.x) | Primary web framework |
| **Django REST Framework** | REST API architecture |
| **PostgreSQL** (Supabase) | Primary relational database |
| **Celery** (5.6+) | Asynchronous task queue & periodic scheduler |
| **Redis** (Hosted / Local) | Celery message broker & result backend |
| **RailKit API** | Live train tracking & timetable data provider |
| **psycopg (v3)** | High-performance PostgreSQL database driver |
| **dj-database-url** | Database URL parser and configuration |
| **django-cors-headers** | Cross-Origin Resource Sharing (CORS) |
| **WhiteNoise** | Static files serving in production |
| **Gunicorn** | WSGI production web server |
| **Bruno** | Fast, git-friendly API client & test suite |
| **Docker & Compose** | Containerized development and deployment |

---

## 2. Project Structure

```text
backend/
├── manage.py
├── pyproject.toml / requirements.txt
├── Dockerfile / .dockerignore
├── docker-compose.yml
├── .env.example
├── Makefile
├── COMMANDS.md
├── ENUMS.md
├── README.md
│
├── bruno/                             # Bruno API test collection
│   ├── bruno.json
│   ├── environments/
│   │   ├── Local.bru
│   │   └── Production.bru
│   ├── 01-Corridors-Sections/         # Sections CRUD
│   │   ├── List Sections.bru
│   │   ├── Create Section.bru
│   │   ├── Get Section by ID.bru
│   │   ├── Update Section.bru
│   │   ├── Partial Update Section.bru
│   │   └── Delete Section.bru
│   ├── 02-Assets/                     # Assets CRUD
│   │   ├── List Assets.bru
│   │   ├── Create Asset.bru
│   │   ├── Get Asset by ID.bru
│   │   ├── Update Asset.bru
│   │   ├── Partial Update Asset.bru
│   │   └── Delete Asset.bru
│   ├── 03-Maintenance-Tasks/          # Maintenance Tasks CRUD
│   │   ├── List Maintenance Tasks.bru
│   │   ├── Create Maintenance Task.bru
│   │   ├── Get Task by ID.bru
│   │   ├── Update Maintenance Task.bru
│   │   ├── Partial Update Maintenance Task.bru
│   │   └── Delete Maintenance Task.bru
│   ├── 04-Trains/                     # Trains (Read-Only & Operations)
│   │   ├── List Trains.bru
│   │   ├── Get Train by ID.bru
│   │   └── Get Train Operations.bru
│   ├── 05-Train-Schedules/            # Weekly Timetables (Read-Only)
│   │   ├── List Train Schedules.bru
│   │   └── Get Schedule by ID.bru
│   ├── 06-Train-Movements/            # Daily Movements (Read-Only)
│   │   ├── List Train Movements.bru
│   │   └── Get Train Movement by ID.bru
│   └── 07-Block-Windows/              # Block Windows & Conflict Engines
│       ├── List Block Windows.bru
│       ├── Create Block Window.bru
│       ├── Get Block Window by ID.bru
│       ├── Update Block Window.bru
│       ├── Partial Update Block Window.bru
│       ├── Delete Block Window.bru
│       ├── Check Train Conflicts.bru
│       └── Calculate Feasible Windows.bru
│
├── config/
│   ├── settings.py                   # Django, DB, DRF, Redis & Celery configuration
│   ├── celery.py                     # Celery application setup
│   ├── router.py                     # DRF DefaultRouter route registrations
│   ├── urls.py                       # Root URL configuration
│   └── wsgi.py / asgi.py
│
└── apps/
    ├── corridors/                    # Corridor & Section models, serializers, views
    │   ├── models.py                 # RailwaySection
    │   ├── serializers.py
    │   └── views.py
    ├── assets/                       # Asset management
    │   ├── models.py                 # Asset
    │   ├── serializers.py
    │   └── views.py
    ├── maintenance/                  # Maintenance tasks
    │   ├── models.py                 # MaintenanceTask
    │   ├── serializers.py
    │   └── views.py
    ├── trains/                       # Trains, schedules, live tracking & sync services
    │   ├── models.py                 # Train, TrainSchedule, TrainMovement
    │   ├── serializers.py
    │   ├── views.py                  # Read-only TrainViewSet, TrainScheduleViewSet, TrainMovementViewSet
    │   ├── tasks.py                  # Celery periodic and queued sync tasks
    │   └── services/
    │       ├── railkit.py            # RailKit external API client
    │       ├── timetable_parser.py   # Raw timetable JSON parser
    │       ├── timetable_sync.py     # Timetable database synchronization logic
    │       ├── live_sync.py          # Live tracking synchronization logic
    │       ├── parser.py             # Live tracking payload parser
    │       ├── train_classification.py
    │       └── train_selection.py
    ├── blocks/                       # Block windows & calculation services
    │   ├── models.py                 # BlockWindow
    │   ├── serializers.py
    │   ├── views.py                  # BlockWindowViewSet (with conflict & feasible window actions)
    │   └── services.py               # Time-window conflict detection & feasible window algorithms
    └── planning/                     # Maintenance planning and automated scheduling engine
        ├── models.py                 # MaintenancePlan
        ├── serializers.py
        ├── views.py                  # MaintenancePlanViewSet (with generate, evaluate, approve, reject actions)
        └── services.py               # Priority scoring and automated proposal generation
```

---

## 3. Base API & Timezone

All API routes are served under `/railways/`:

- **Local API Base**: `http://127.0.0.1:8000/railways/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`

### Timezone: Indian Standard Time (IST - Asia/Kolkata)

All datetime inputs and outputs use formatted IST (`YYYY-MM-DD HH:MM:SS`):

```text
2026-09-04 14:30:00
```

---

## 4. API Endpoints Reference

All application endpoints are registered via the Django REST Framework router under `/railways/`.

### 4.1 Summary Table

| Resource | HTTP Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Corridors / Sections** | `GET` / `POST` | `/railways/sections/` | List all sections or create a new section |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/sections/{id}/` | Retrieve, update, partial update, or delete a section |
| **Assets** | `GET` / `POST` | `/railways/assets/` | List all assets or create a new asset |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/assets/{id}/` | Retrieve, update, partial update, or delete an asset |
| **Maintenance Tasks** | `GET` / `POST` | `/railways/maintenance-tasks/` | List all maintenance tasks or create a new task |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/maintenance-tasks/{id}/` | Retrieve, update, partial update, or delete a task |
| **Trains** *(Read-Only)* | `GET` | `/railways/trains/` | List all trains *(synced via RailKit timetable sync)* |
| | `GET` | `/railways/trains/{id}/` | Retrieve train details by ID |
| **Live Operations View** | `GET` | `/railways/trains/operations/` | Combined live tracking view (`?date=YYYY-MM-DD&source=CODE&destination=CODE`) |
| **Train Schedules** *(Read-Only)* | `GET` | `/railways/train-schedules/` | List timetable schedules (supports pagination `?page=&page_size=` and filters `?date=YYYY-MM-DD&source=&destination=`) |
| | `GET` | `/railways/train-schedules/{id}/` | Retrieve timetable schedule by ID |
| **Train Movements** *(Read-Only)* | `GET` | `/railways/train-movements/` | List all daily actual train movement records |
| | `GET` | `/railways/train-movements/{id}/` | Retrieve daily movement record by ID |
| **Block Windows** | `GET` / `POST` | `/railways/block-windows/` | List all block windows or create a new block window |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/block-windows/{id}/` | Retrieve, update, partial update, or delete a block window |
| **Conflict Check Engine** | `POST` | `/railways/block-windows/check-conflict/` | Check train movement conflicts during proposed maintenance window |
| **Feasible Window Engine**| `POST` | `/railways/block-windows/feasible-windows/` | Compute available safe sub-windows for a specific maintenance task |
| **Maintenance Plans** | `GET` / `POST` | `/railways/plans/` | List all maintenance plans or create a new plan |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/plans/{id}/` | Retrieve, update, partial update, or delete a plan |
| **Plan Generator Engine** | `POST` | `/railways/plans/generate/` | Auto-generate maintenance plan proposals for pending tasks |
| **Plan Evaluation Engine**| `POST` | `/railways/plans/{id}/evaluate/` | Evaluate train conflict and impact for a plan |
| **Plan Actions** | `POST` | `/railways/plans/{id}/approve/` | Approve a proposed plan and schedule task |
| | `POST` | `/railways/plans/{id}/reject/` | Reject a proposed plan |

> **Note**: Trains, Train Schedules, and Train Movements are **read-only (`GET` only)** resources for client APIs. Master records, weekly schedules, and daily actual movements are populated and synchronized automatically via Celery background tasks from the RailKit API.

---

## 5. Sample API Payloads & Usage

### 5.1 Railway Sections (`POST /railways/sections/`)

```json
{
  "section_name": "New Delhi - Ghaziabad Main Section",
  "origin_station": "New Delhi",
  "source_station_code": "NDLS",
  "end_station": "Ghaziabad Junction",
  "destination_station_code": "GZB",
  "distance": 25.6,
  "status": true
}
```

### 5.2 Assets (`POST /railways/assets/`)

```json
{
  "asset_title": "OHE Traction Line Pole #42",
  "category": "OHE",
  "division": "TRACTION",
  "risk_level": 4,
  "setup_date": "2024-01-15",
  "section": 1
}
```
> *Allowed `division` choices: `ENGINEERING`, `SNT`, `TRACTION`.*

### 5.3 Maintenance Tasks (`POST /railways/maintenance-tasks/`)

```json
{
  "task_code": "TASK-OHE-101",
  "asset": 1,
  "details": "Routine OHE tension wire check and insulator cleaning",
  "risk_rating": 3,
  "urgency": "HIGH",
  "deadline": "2026-09-10",
  "estimated_duration": 120,
  "task_status": "PENDING"
}
```
> *Allowed `urgency` choices: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.*  
> *Allowed `task_status` choices: `PENDING`, `SCHEDULED`, `COMPLETED`, `CANCELLED`.*

### 5.4 Live Operations Dashboard (`GET /railways/trains/operations/?date=2026-09-04&source=NDLS&destination=GZB`)

Combines master train, timetable schedule, and live tracking movement into an operational view:

```json
{
  "date": "2026-09-04",
  "source": "NDLS",
  "destination": "GZB",
  "count": 1,
  "trains": [
    {
      "train_number": "12004",
      "train_name": "Lucknow Shatabdi Express",
      "train_type": "SHATABDI",
      "priority": 9,
      "section": {
        "name": "New Delhi - Ghaziabad Main Section",
        "source": "New Delhi",
        "source_code": "NDLS",
        "destination": "Ghaziabad Junction",
        "destination_code": "GZB"
      },
      "schedule": {
        "entry_time": "06:10:00",
        "exit_time": "06:45:00"
      },
      "movement": {
        "actual_entry_time": "2026-09-04 06:15:00",
        "actual_exit_time": "2026-09-04 06:50:00"
      },
      "delay_minutes": 5
    }
  ]
}
```

### 5.5 Block Windows (`POST /railways/block-windows/`)

```json
{
  "section": 1,
  "start_time": "2026-09-04 01:00:00",
  "end_time": "2026-09-04 05:00:00",
  "status": "AVAILABLE"
}
```
> *Allowed `status` choices: `AVAILABLE`, `RESERVED`, `BLOCKED`.*

### 5.6 Conflict Check Engine (`POST /railways/block-windows/check-conflict/`)

**Request:**
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
      "train_name": "Lucknow Shatabdi Express",
      "entry_time": "2026-09-04 02:30:00",
      "exit_time": "2026-09-04 03:15:00"
    }
  ]
}
```

### 5.7 Feasible Windows Engine (`POST /railways/block-windows/feasible-windows/`)

**Request:**
```json
{
  "task_id": "TASK-OHE-101",
  "block_window_id": 1
}
```

**Response:**
```json
{
  "task_id": "TASK-OHE-101",
  "block_window_id": 1,
  "section": "New Delhi - Ghaziabad Main Section",
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

Celery handles periodic timetable synchronization and live train tracking with API quota protection, local/production Redis isolation, and retry mechanisms:

| Task Name | Schedule | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `apps.trains.tasks.sync_relevant_live_trains` | Every 3 hours (`crontab(minute=0, hour="*/3")`) *(Requires `ENABLE_LIVE_SYNC=true`)* | — | Selects up to 40 active corridor trains using IST (`Asia/Kolkata`) and queues live tracking jobs |
| `apps.trains.tasks.sync_live_train_task` | Triggered by Live Sync | **15/m** (smoothed) | Fetches live train status from RailKit API, updates `TrainMovement` records, with exponential backoff on transient errors |
| `apps.trains.tasks.sync_all_timetables` | Daily at 02:00 AM (`crontab(minute=0, hour=2)`) | — | Syncs full station timetable data across all active sections wrapped in atomic database transactions |

### 🛡️ Production & Quota Protection Features

- **Live Sync Flag (`ENABLE_LIVE_SYNC`)**: Controls automatic periodic live tracking sync (default `false` to conserve RailKit API quota during development/testing).
- **Rate Limiting (`15/m`)**: Throttles live-tracking calls to 15 per minute, preventing concurrency bursts and RailKit `429 Too Many Requests` errors.
- **Auto-Retry with Exponential Backoff**: Transient API errors automatically retry up to 3 times (`1s, 2s, 4s...`).
- **Timezone Awareness**: Tasks use `timezone.localdate()` (`Asia/Kolkata`) to guarantee accurate service date resolution regardless of server UTC time.
- **Result Expiration (`CELERY_TASK_RESULT_EXPIRES = 3600`)**: Prevents Redis broker memory bloat by automatically purging completed task results after 1 hour.
- **Environment Isolation (`USE_LOCAL_REDIS`)**: Allows running against a local or containerized Redis (`redis://redis:6379/0`) without pulling or executing tasks from Cloud Redis (Upstash).

---

## 7. Running the Project (Makefile & Docker)

For detailed workflows, refer to [COMMANDS.md](COMMANDS.md).

### Quick Commands:

```bash
# 1. Start all services in Docker (Django + Celery Worker + Celery Beat + Redis)
make up

# 2. Hybrid Mode: Run Redis + Celery in Docker, Django Server locally
make dev-local

# 3. Stop all Docker services
make down

# 4. Database Migrations
make migrate
make makemigrations

# 5. Flush Redis and Purge Celery Task Queues
celery -A config purge -f
```

---

## 8. 🧪 1-Click Bruno API Test Suite

The repository includes a comprehensive, ready-to-use **[Bruno Collection](bruno/)** containing **33 API requests** testing all active endpoints and operations.

### Collection Structure:

1. **`01-Corridors-Sections`**: List, Create, Get by ID, Full Update (PUT), Partial Update (PATCH), Delete
2. **`02-Assets`**: List, Create, Get by ID, Full Update (PUT), Partial Update (PATCH), Delete
3. **`03-Maintenance-Tasks`**: List, Create, Get by ID, Full Update (PUT), Partial Update (PATCH), Delete
4. **`04-Trains`**: List, Get by ID, Live Operations View *(Read-Only)*
5. **`05-Train-Schedules`**: List, Get by ID *(Read-Only)*
6. **`06-Train-Movements`**: List, Get by ID *(Read-Only)*
7. **`07-Block-Windows`**: List, Create, Get by ID, Full Update (PUT), Partial Update (PATCH), Delete, Check Train Conflicts, Calculate Feasible Windows

### How to Run:

#### Option A: Using the Bruno Desktop App (GUI)

1. Open **Bruno**.
2. Click **Open Collection** and select the [`bruno/`](bruno/) folder in this repository.
3. Select your environment from the top-right dropdown (**Local** for `http://127.0.0.1:8000` or **Production** for `https://backend-oz3h.onrender.com`).
4. Right-click the collection name (`Smart-Railways-Backend`) and click **Run Collection** to execute all tests with 1 click!

#### Option B: Using Bruno CLI

```bash
# Install Bruno CLI (if not already installed)
npm install -g @usebruno/cli

# Run all test suites against the Local environment
bru run bruno/ --env Local

# Run all test suites against Production
bru run bruno/ --env Production
```