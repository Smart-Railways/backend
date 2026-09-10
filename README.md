# AI-Powered Automatic Block Planning — Unified Backend & Intelligence Engine

Enterprise-grade backend service and intelligence engine for the **SIH Railways AI-Powered Automatic Block Planning** system.

The platform is architected as a **unified, high-performance monolith**:
- **Web & API Framework**: **Django 6.1+ & Django REST Framework (DRF)**.
- **Relational Persistence**: **PostgreSQL 16** (Supabase / Managed PaaS) with zero-config local **SQLite** fallback.
- **Embedded AI/ML Intelligence**: **Google OR-Tools CP-SAT** discrete constraint optimizer and **Calibrated XGBoost** failure predictor running **in-memory** (0ms latency, zero extra microservice ports).
- **Asynchronous Task Workers**: **Celery 5.6+ & Redis** for timetable synchronization and live train telemetry.
- **External Telemetry Provider**: **RailKit API** for real-time timetables, master train data, and train movement updates.
- **Client Test Suite**: 35 automated tests in a git-friendly **Bruno API Collection** across 7 functional domains.

---

## 🚀 Key Features

### 🧠 Embedded AI & Constraint Optimization
- **In-Memory Google OR-Tools CP-SAT Solver**: Solves discrete 30-minute interval block window scheduling with hard safety constraints (crew capacity, train traffic conflict avoidance, track isolation) and soft objectives (maximizing maintenance decision score, minimizing ripple delays).
- **Calibrated XGBoost Failure Predictor**: Predicts empirical 30-day asset failure probabilities using isotonic probability calibration over 11 pre-trained model artifacts (`calibrated_xgboost.pkl`, deep neural checkpoints).
- **Multi-Tier Zero-Crash Resilience**:
  1. *Tier 1 (Active)*: In-memory CP-SAT constraint optimization.
  2. *Tier 2 (Fallback)*: Remote HTTP microservice bridge (if `PREFER_EMBEDDED_AI=False`).
  3. *Tier 3 (Fail-Safe)*: Heuristic database timestamp gap calculation guaranteeing zero crashdowns.

### 🚆 Railway Operations & Asset Management
- **Railway Corridor & Section Management**: Complete CRUD tracking section lengths, source/destination station codes (`source_station_code`, `destination_station_code`), and activity flags.
- **Asset Hierarchy & Criticality**: Tracks corridor assets (track segments, OHE traction, signaling) categorized by department (`ENGINEERING`, `SNT`, `TRACTION`) and criticality rating (1–5).
- **Maintenance Task Lifecycle & Auto-Overdue Detection**: Tracks defect logs, required durations, severity ratings, urgency levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and task states (`PENDING`, `SCHEDULED`, `DELAYED`, `COMPLETED`, `CANCELLED`). Expired tasks whose `due_date < today` (in `Asia/Kolkata`) automatically transition to `DELAYED` status with `is_overdue=True` via model hooks, API queries, and daily Celery beat cron.
- **Train Schedules & Live Movements (Read-Only)**: Exposes weekly timetables (with 7-day running bitmasks, day offsets, multi-field station filtering, and configurable pagination) and daily actual train movements with live delay calculations.
- **Live Operations Aggregation View**: Aggregated corridor view combining master train data, scheduled timetables, and live tracking movements for up to 30 trains with calculated entry/exit delays.

### ⚡ Celery Background Sync & RailKit Quota Guards
- **Intelligent Timetable Sync**: Daily atomic sync of full corridor timetables across active sections at 02:00 AM IST.
- **Active-Day Pre-Filtering**: Evaluates each train's 7-day running mask (`running_days`) *before* queueing live tracking tasks, eliminating unnecessary API queries for trains not operating on the target date.
- **Strict Quota Protection (30 Trains / Cycle)**: Hard-capped at 30 trains per corridor section and 30 trains globally per sync cycle, prioritizing up to 10 premium services (Vande Bharat, Rajdhani, Shatabdi, Tejas).
- **Graceful Error Handling**: Missing RailKit data (HTTP 400 `Train data not available for date`) is caught and marked as `SKIPPED` (`TRAIN_DATA_NOT_AVAILABLE`) rather than triggering failing retries.
- **Rate Limiting & Smoothing**: Live sync tasks are throttled to 15 calls per minute (`rate_limit="15/m"`), preventing HTTP 429 rate limit errors.

---

## 1. Unified Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python** (3.12+) | Core runtime environment |
| **Django** (6.1+) | Primary web framework & ORM gateway |
| **Django REST Framework** | REST API serialization, viewsets, routers, and pagination |
| **Google OR-Tools** (9.8+) | CP-SAT discrete constraint satisfaction solver |
| **XGBoost & Scikit-Learn** | Calibrated machine learning failure risk models |
| **Pandas & NumPy** | In-memory feature vectors, timetable matrices, and dataframe pipelines |
| **PostgreSQL** (16.x) | Production relational database (Supabase / Managed PaaS) |
| **SQLite** (3.x) | Automatic zero-config local development database fallback |
| **Celery** (5.6+) | Distributed asynchronous task queue & periodic cron scheduler |
| **Redis** (7.x) | Message broker, result backend, and task cache |
| **RailKit API** | Upstream live train tracking and timetable data provider |
| **psycopg (v3)** | High-performance binary PostgreSQL driver |
| **WhiteNoise** | High-performance static file serving |
| **Gunicorn** | WSGI production application server |
| **Bruno** | 33-request automated API test collection |
| **Docker & Docker Compose** | Containerized single-service development and deployment |

---

## 2. Project Architecture & Directory Structure

```text
backend/
├── manage.py                          # Django management CLI
├── requirements.txt                   # Production dependencies (Django + OR-Tools + ML)
├── Dockerfile / .dockerignore         # Unified production container definition
├── docker-compose.yml                 # Local multi-service orchestration (Redis + Web + Celery)
├── .env.example / .env                # Environment templates and local configuration
├── Makefile / COMMANDS.md             # Developer workflow shortcuts
├── ENUMS.md                           # Comprehensive documentation of model enums
├── README.md                          # This documentation
│
├── src/                               # 🧠 Embedded Railway AI/ML Intelligence Engine
│   ├── decision/                      # Multi-factor maintenance decision & urgency scoring
│   │   └── maintenance_decision_engine.py
│   ├── optimization/                  # Google OR-Tools CP-SAT discrete constraint optimizer
│   │   ├── block_optimizer.py         # Notebook 23-derived 30-min discrete slotting solver
│   │   └── multi_horizon_planner.py   # Tactical 6-hr, 24-hr, and weekly planners
│   ├── models/                        # ML model predictors & feature pipelines
│   │   └── failure_predictor.py       # Calibrated XGBoost & survival inference
│   ├── features/                      # Operational context enrichers & pressure builders
│   ├── data/                          # Ingestion, adapters, and normalization pipelines
│   └── services/                      # High-level engine orchestrators
│       └── ml_engine.py               # RailwayMLEngine service entry point
│
├── models/                            # 📦 11 Serialized AI/ML Pre-Trained Artifacts
│   ├── calibrated_xgboost.pkl         # 3.4 MB Calibrated XGBoost model artifact
│   ├── cox_survival_model.pkl         # Cox Proportional Hazards survival analysis model
│   ├── best_cnn_failure_model.pt      # 1D CNN waveform defect detection checkpoint
│   ├── best_lstm_failure_model.pt     # LSTM temporal degradation model checkpoint
│   ├── best_railway_autoencoder.pt    # Telemetry anomaly detection model checkpoint
│   ├── best_railway_transformer.pt    # Attention-based network delay checkpoint
│   └── *.json                         # Hyperparameters, configs, and thresholds
│
├── data/                              # 📊 Ground-Truth Validation & Evidence Datasets
│   ├── processed_real/                # Operational features and section mapping evidence
│   ├── raw/                           # Raw reference CSVs (assets, failures, freight)
│   └── raw_real/railkit/              # Telemetry snapshots and manifest metadata
│
├── apps/                              # 🚆 Django Business Logic Applications
│   ├── corridors/                     # Corridor sections and station codes
│   ├── assets/                        # Track, OHE, traction, and signaling assets
│   ├── maintenance/                   # Defect logs, severity ratings, deadlines & overdue automation
│   │   ├── models.py                  # MaintenanceTask with DELAYED status & auto-overdue hook
│   │   ├── tasks.py                   # Celery periodic task marking expired tasks DELAYED
│   │   └── views.py                   # MaintenanceTaskViewSet with auto-overdue synchronization
│   ├── trains/                        # Timetables, live train movements & Celery tasks
│   │   ├── tasks.py                   # Celery periodic live-sync and timetable jobs
│   │   └── services/                  # RailKit client, timetable sync, train selectors
│   └── blocks/                        # Maintenance windows & AI constraint solver bridge
│       ├── ai_client.py               # In-memory bridge to RailwayMLEngine (0ms latency)
│       ├── services.py                # Conflict detection & CP-SAT feasible window calculations
│       ├── views.py                   # BlockWindowViewSet (check-conflict, feasible-windows)
│       └── serializers.py             # Serializers with decision_score & algorithm fields
│
├── config/                            # ⚙️ Django System Configuration
│   ├── settings.py                    # Database fallback, CORS, Celery & DRF config
│   ├── urls.py                        # Django administration and API router includes (/railways/)
│   ├── router.py                      # DRF DefaultRouter endpoint registrations
│   ├── celery.py                      # Celery application instantiation
│   └── wsgi.py / asgi.py              # WSGI and ASGI entry points
│
├── tests/                             # 🧪 Automated Test Suites
│   └── test_embedded_ai.py            # Unit tests for in-memory CP-SAT & XGBoost engine
│
└── bruno/                             # 🚀 33-Request Automated API Test Collection
    ├── bruno.json
    ├── environments/                  # Local (127.0.0.1:8000) & Production environments
    └── 01 to 07 subfolders/           # Full CRUD & action tests for all endpoints
```

---

## 3. Base URLs & Architecture

| URL Path | Method | Description | Sample Output |
|---|:---:|---|---|
| **`http://127.0.0.1:8000/railways/`** | `GET` | **DRF Browsable API Root**: Interactive directory of all REST endpoints. | Links to sections, assets, tasks, trains, block-windows, etc. |
| **`http://127.0.0.1:8000/admin/`** | `GET` | **Django Administration Panel**: Visual model browser and data editor. | Django Admin login interface. |

### Timezone Standard: Indian Standard Time (IST - Asia/Kolkata)
All API inputs, outputs, and Celery cron evaluations operate on formatted IST (`YYYY-MM-DD HH:MM:SS`):
```text
2026-09-08 00:30:00
```
- **Database Storage**: Aware datetimes are persisted in PostgreSQL in UTC (`+00:00`).
- **Serialization Guarantee**: When serving API responses, both `MaintenanceTaskSerializer` and `BlockWindowSerializer` automatically convert timestamps to the local `Asia/Kolkata` timezone (`+05:30`) via `timezone.localtime()`. This ensures complete timestamp consistency between maintenance queue rows and block window recommendations with zero date drift.

---

## 4. API Endpoints Reference

All application endpoints are served under `/railways/`:

| Domain | Method | Endpoint | Description |
|---|:---:|---|---|
| **Corridors** | `GET` / `POST` | `/railways/sections/` | List all sections or create a new section |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/sections/{id}/` | Retrieve, update, partial update, or delete a section |
| **Assets** | `GET` / `POST` | `/railways/assets/` | List all assets or create a new asset |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/assets/{id}/` | Retrieve, update, partial update, or delete an asset |
| **Maintenance** | `GET` / `POST` | `/railways/maintenance-tasks/` | List all maintenance tasks or create a new task |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/maintenance-tasks/{id}/` | Retrieve, update, partial update, or delete a task |
| **Trains** *(Read-Only)* | `GET` | `/railways/trains/` | List all trains *(synced via RailKit timetable sync)* |
| | `GET` | `/railways/trains/{id}/` | Retrieve train details by ID |
| **Live Operations** | `GET` | `/railways/trains/operations/` | Combined live tracking view (up to 30 tracked trains for `?date=YYYY-MM-DD&source=CODE&destination=CODE`) |
| **Train Schedules** *(Read-Only)* | `GET` | `/railways/train-schedules/` | List weekly timetables (paginated, supports `?date=`, `?source=`, `?destination=`) |
| | `GET` | `/railways/train-schedules/{id}/` | Retrieve timetable schedule by ID |
| **Train Movements** *(Read-Only)* | `GET` | `/railways/train-movements/` | List all daily actual train movement records |
| | `GET` | `/railways/train-movements/{id}/` | Retrieve daily movement record by ID |
| **Block Windows** | `GET` / `POST` | `/railways/block-windows/` | List all block windows or create a new block window |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/block-windows/{id}/` | Retrieve, update, partial update, or delete a block window |
| | `GET` / `PUT` / `PATCH` / `DELETE` | `/railways/block-windows/by-task/{task_id}/` | Retrieve, create, update, or delete the block window directly by maintenance task code |
| **Conflict Check** | `POST` | `/railways/block-windows/check-conflict/` | Check train movement collisions during a proposed window |
| **Feasible Windows (AI)** | `POST` | `/railways/block-windows/feasible-windows/` | **Executes Google OR-Tools CP-SAT Solver** (or gap fallback) to compute optimal maintenance windows for a task on a given date |
| **Window Recommendation (AI)** | `GET` | `/railways/block-windows/{id}/recommendation/` | Get AI recommendation for the best conflict-free slot on an existing block window (includes `suggested_put_payload`) |
| **Unified AI Recommendation** | `GET` / `POST` | `/railways/block-windows/recommendation/` | Unified AI endpoint: discover feasible slots, monitor conflicts, or auto-apply |
| **Apply AI Recommendation** | `POST` | `/railways/block-windows/{id}/apply-recommendation/` | 1-Click action to automatically update the block window to the AI-recommended slot |

---

## 5. Sample API Payloads & AI Engine Outputs

### 5.1 Feasible Maintenance Windows with CP-SAT Solver (`POST /railways/block-windows/feasible-windows/`)

When a maintenance task and a target date are submitted, the backend dynamically resolves the task's corridor section and computes optimal safe maintenance windows using the in-memory **Google OR-Tools CP-SAT discrete constraint solver** (or database timestamp gap heuristic fallback):

> [!NOTE]
> A virtual 24-hour planning horizon (`00:00:00` to `23:59:59` IST) on the requested `date` is constructed automatically for the section associated with the task (`task.asset.section`). No pre-existing `BlockWindow` database record is required to calculate feasibility. Once an approved slot is chosen, the actual `BlockWindow` can be persisted via `POST /railways/block-windows/`.

**Request Body:**
```json
{
  "task_id": "TASK-OHE-101",
  "date": "2026-09-04"
}
```

**Response (`200 OK` returned in ~0.1s):**
```json
{
  "task_id": "TASK-OHE-101",
  "date": "2026-09-04",
  "section": {
    "id": 1,
    "name": "New Delhi - Mathura Junction",
    "source": "New Delhi",
    "source_code": "NDLS",
    "destination": "Mathura Junction",
    "destination_code": "MTJ"
  },
  "required_duration_minutes": 120,
  "feasible": true,
  "windows": [
    {
      "start": "2026-09-04 04:00:00",
      "end": "2026-09-04 06:00:00",
      "duration_minutes": 120,
      "decision_score": 0.85,
      "algorithm": "CP-SAT Constraint Solver"
    }
  ]
}
```

#### 📊 Understanding `decision_score` & `algorithm`
- **`algorithm`**:
  - `"CP-SAT Constraint Solver"`: Automatically invoked for tasks in `PENDING` or `SCHEDULED` status (enabling both initial allocation and dynamic rescheduling). The Google OR-Tools discrete optimizer allocates optimal safe 30-minute interval slots avoiding train movements.
  - `"Database Timestamp Gap"`: Deterministic fail-safe fallback used when trains are inactive, no discrete slot satisfies solver constraints, or the AI engine is bypassed. Computes available time intervals between actual train movements and calculates the normalized maintenance decision score from task attributes.
- **`decision_score` (Scale: `0.0` to `1.0`)**: Normalized multi-factor maintenance suitability index combining:
  - Asset Failure Risk (25%) + Urgency Score (20%) + Asset Criticality (15%) + Section Traffic & Pressure (25%) + Duration/Overdue Impact (15%). Always populated across both solver and fallback algorithms.
- **Score Interpretations for UI / Dashboard**:
  - `0.75 – 1.00` 🔴 **Critical Priority / Immediate Need**: High failure probability or overdue track defect; must schedule immediately.
  - `0.40 – 0.74` 🟡 **Moderate Priority / Recommended Window**: Routine wear and tear; window has low passenger train impact.
  - `0.00 – 0.39` 🟢 **Low / Routine Maintenance**: Discretionary inspection; can be shifted if high-priority trains require the corridor.

### 5.2 Dynamic AI Recommendation & Slot Rescheduling (`GET /railways/block-windows/{id}/recommendation/`)

Once a user or controller creates a `BlockWindow` on a corridor, the AI engine evaluates the window for train traffic collisions, delay risks, or sub-optimal timing, and recommends the **best feasible conflict-free slot** on that corridor:

**Request:**
```text
GET /railways/block-windows/1/recommendation/?task_id=TMS-696
```

**Response (`200 OK`):**
```json
{
  "block_window_id": 1,
  "task_id": "TMS-696",
  "section": {
    "id": 10,
    "name": "Surat-Mumbai",
    "source": "Surat",
    "source_code": "ST",
    "destination": "Mumbai",
    "destination_code": "MMCT"
  },
  "current_slot": {
    "start_time": "2026-09-04 13:00:00",
    "end_time": "2026-09-04 17:00:00",
    "duration_minutes": 240,
    "status": "RESERVED",
    "has_conflict": true,
    "conflict_count": 1,
    "conflicts": [
      {
        "train_number": "12002",
        "train_name": "New Delhi - Bhopal Shatabdi Express",
        "entry_time": "2026-09-04 14:00:00",
        "exit_time": "2026-09-04 14:35:00"
      }
    ]
  },
  "has_better_slot": true,
  "recommendation_reason": "Current window has 1 train conflict(s) with train(s) 12002. AI recommends shifting to 03:00:00 - 05:00:00 which is 100% collision-free with a decision score of 0.850.",
  "recommended_slot": {
    "start": "2026-09-04 03:00:00",
    "end": "2026-09-04 05:00:00",
    "duration_minutes": 120,
    "decision_score": 0.85,
    "algorithm": "CP-SAT Constraint Solver"
  },
  "suggested_put_payload": {
    "section": 10,
    "start_time": "2026-09-04 03:00:00",
    "end_time": "2026-09-04 05:00:00",
    "status": "RESERVED"
  },
  "put_url": "/railways/block-windows/1/"
}
```

#### 🔄 How the Frontend Applies the Recommendation:

- **Option A: Standard `PUT` Request** (Client-Triggered):
  Send a `PUT` request to `/railways/block-windows/{id}/` using the provided `suggested_put_payload`:
  ```json
  PUT /railways/block-windows/1/
  {
    "section": 10,
    "start_time": "2026-09-04 03:00:00",
    "end_time": "2026-09-04 05:00:00",
    "status": "RESERVED"
  }
  ```

- **Option B: 1-Click Auto-Apply Endpoint**:
  Call `POST /railways/block-windows/{id}/apply-recommendation/` to automatically update the block window to the recommended optimal slot in a single click.

- **Option C: Direct Task-Based `PUT` Request (`PUT /railways/block-windows/by-task/{task_id}/`)**:
  Update or reserve the block window directly using the human-readable task code (e.g. `TMS-746` or `TASK-OHE-101`), without needing to look up the internal numeric block window ID:
  ```json
  PUT /railways/block-windows/by-task/TASK-OHE-101/
  {
    "section": 10,
    "start_time": "2026-09-04 03:00:00",
    "end_time": "2026-09-04 05:00:00",
    "status": "RESERVED"
  }
  ```

### 5.3 Conflict Check Engine (`POST /railways/block-windows/check-conflict/`)

Detects whether any scheduled or live trains overlap with a proposed maintenance time range:

**Request Body:**
```json
{
  "section": 1,
  "maintenance_start": "2026-09-04 13:00:00",
  "maintenance_end": "2026-09-04 17:00:00"
}
```

**Response:**
```json
{
  "has_conflict": true,
  "conflict_count": 1,
  "conflicts": [
    {
      "train_number": "12002",
      "train_name": "New Delhi - Bhopal Shatabdi Express",
      "entry_time": "2026-09-04 14:00:00",
      "exit_time": "2026-09-04 14:35:00"
    }
  ]
}
```

### 5.4 Train Schedules & Timetable Filtering (`GET /railways/train-schedules/`)

Lists weekly timetables with support for corridor section filtering, operating day-of-week verification (`running_days` 7-character mask), and pagination:

**Query Parameters:**
- `source`: Station code (e.g., `NDLS`) or partial station name
- `destination`: Station code (e.g., `MTJ`) or partial station name
- `date`: Service date (`YYYY-MM-DD`); evaluates whether the train operates on that specific day of the week
- `page` & `page_size`: Pagination control (e.g. `page=1&page_size=20`)

**Sample Request:**
```text
GET /railways/train-schedules/?source=NDLS&destination=MTJ&page=1&page_size=20&date=2026-09-04
```

**Response:**
```json
{
  "count": 18,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "train": 1,
      "train_number": "12002",
      "train_name": "New Delhi - Bhopal Shatabdi Express",
      "section": 1,
      "section_name": "New Delhi - Mathura Junction",
      "scheduled_entry_time": "06:00:00",
      "scheduled_exit_time": "07:20:00",
      "running_days": "1111111",
      "day_offset": 0
    }
  ]
}
```

### 5.5 Live Operations Dashboard (`GET /railways/trains/operations/?date=2026-09-04&source=NDLS&destination=GZB`)

Aggregates master train data, scheduled arrival/departure, and live-synced tracking records:

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

### 5.6 Maintenance Tasks & Automatic DELAYED Lifecycle (`/railways/maintenance-tasks/`)

Maintenance tasks represent track, traction, or signaling repair activities with severity ratings, durations, and deadlines (`due_date`).

#### 🏷️ Status Enum Values:
| Status | Description |
|---|---|
| `PENDING` | Created; awaiting scheduling or block window allocation |
| `SCHEDULED` | Provisionally scheduled or approved with a linked block window |
| `DELAYED` | **Deadline elapsed**: The scheduled `due_date` has passed (`< today` in IST) and the task was not completed |
| `COMPLETED` | Work successfully executed on site |
| `CANCELLED` | Work retracted or superseded |

#### ⚙️ Multi-Layer Auto-Delayed Transition Mechanism:
Whenever a task's `due_date` is earlier than today (`due_date < timezone.localdate()` in `Asia/Kolkata`), the backend automatically updates its status to `DELAYED` and sets `is_overdue = True` (provided it is not already `COMPLETED` or `CANCELLED`). This is enforced across three redundant layers:

1. **Model-Level Save Hook**: `MaintenanceTask.save()` invokes `check_and_update_overdue()` before committing to the database.
2. **On-the-Fly API Viewset Sync**: When calling `GET /railways/maintenance-tasks/` or `GET /railways/maintenance-tasks/{id}/`, `MaintenanceTaskViewSet.get_queryset()` runs a bulk database update over all expired tasks, guaranteeing zero-stale data in frontend views even before the cron fires.
3. **Daily Midnight Celery Beat Task**: Scheduled at `00:00 IST` daily (`apps.maintenance.tasks.update_expired_maintenance_tasks`) to sweep and log all overdue tasks.

#### 🤖 Optimizer Integration:
Tasks in `DELAYED` status are automatically prioritized by the CP-SAT Block Optimizer and `get_block_window_recommendation()` service when resolving unallocated high-urgency defects on a corridor section.

#### Sample Task Response (`DELAYED` with Reserved Block Window):
```json
{
  "id": 6,
  "task_code": "TASK-OHE-201",
  "asset": 1,
  "asset_name": "OHE Tension Wire Mast #104",
  "section_name": "New Delhi - Mathura Junction",
  "details": "Emergency OHE tension wire readjustment",
  "risk_rating": 4,
  "urgency": "CRITICAL",
  "deadline": "2026-09-04",
  "estimated_duration": 120,
  "task_status": "DELAYED",
  "block_window": {
    "id": 14,
    "section": 1,
    "section_name": "New Delhi - Mathura Junction",
    "date": "2026-09-04",
    "start_time": "2026-09-04 03:00:00",
    "end_time": "2026-09-04 05:00:00",
    "duration_minutes": 120,
    "status": "RESERVED"
  },
  "block_window_date": "2026-09-04",
  "is_delayed": true,
  "logged_at": "2026-09-01 10:00:00"
}
```

---

## 6. Celery Background & Periodic Tasks

Celery coordinates automated timetable synchronization and live train telemetry:

| Task Name | Trigger / Schedule | Rate Limit | Description |
|---|---|:---:|---|
| `apps.trains.tasks.sync_relevant_live_trains` | Every 3 hours (`crontab(minute=0, hour="*/3")`) *(Requires `ENABLE_LIVE_SYNC=true`)* | — | Evaluates `running_days` weekly masks in IST, selects up to 30 operating trains (max 10 premium), and dispatches individual tracking tasks. |
| `apps.trains.tasks.sync_live_train_task` | Triggered by Live Sync | **15/m** (smoothed) | Queries RailKit API, updates `TrainMovement` actual entry/exit timestamps, and skips missing dates (`TRAIN_DATA_NOT_AVAILABLE`) gracefully without failing retries. |
| `apps.trains.tasks.sync_all_timetables` | Daily at 02:00 AM IST (`crontab(minute=0, hour=2)`) | — | Syncs full timetable schedules across all active sections wrapped in atomic database transactions. |
| `apps.maintenance.tasks.update_expired_maintenance_tasks` | Daily at 00:00 AM IST (`crontab(minute=0, hour=0)`) | — | Automatically finds expired maintenance tasks (`due_date < today`) not yet completed or cancelled, marking their status as `DELAYED` and `is_overdue=True`. |

### 🛡️ Production & Quota Protection Features

- **Live Sync Flag (`ENABLE_LIVE_SYNC`)**: Controls automatic periodic live tracking sync (default `false` to conserve RailKit API quota during development/testing).
- **Strict Quota Protection (30 Trains / Sync Cycle)**: Enforces a hard cap of maximum 30 trains per corridor section and 30 trains globally per sync cycle, prioritizing up to 10 premium express services (Vande Bharat, Shatabdi, Rajdhani, Tejas) followed by regular trains.
- **Pre-Sync Operating Day Filter**: Trains that do not operate on the target `service_date` are filtered out using their 7-day running mask (`running_days[day_index] == "1"`) *before* scheduling live tracking tasks, avoiding wasted API calls.
- **Graceful Missing-Date Error Handling**: When RailKit returns HTTP 400 (`Train data not available for date`), the task catches `RailKitError` and marks the train as skipped (`TRAIN_DATA_NOT_AVAILABLE`) rather than triggering failing retries or marking the Celery task as failed.
- **Deterministic Train Ordering**: Trains and sections are sorted deterministically before selection to guarantee stable tracking cycles across periodic runs.
- **Rate Limiting (`15/m`)**: Throttles live-tracking calls to 15 per minute, preventing concurrency bursts and RailKit `429 Too Many Requests` errors.
- **Timezone Awareness**: Tasks use `timezone.localdate()` (`Asia/Kolkata`) to guarantee accurate service date resolution regardless of server UTC time.
- **Result Expiration (`CELERY_TASK_RESULT_EXPIRES = 3600`)**: Prevents Redis broker memory bloat by automatically purging completed task results after 1 hour.
- **Environment Isolation (`USE_LOCAL_REDIS`)**: Allows running against a local or containerized Redis (`redis://redis:6379/0`) without pulling or executing tasks from Cloud Redis (Upstash).

---

## 7. Running & Developing Locally

### 7.1 Setup Environment

#### Option A: Using `uv` (Recommended — Fastest)
```bash
# Install dependencies into uv virtual environment
uv pip install -r requirements.txt

# Run migrations
uv run python manage.py migrate

# Start dev server
uv run python manage.py runserver 8000
```

#### Option B: Standard Python Virtualenv
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000

# Windows PowerShell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### 7.2 Configure Local Environment File (`.env`)
Create a `.env` file in the backend root:
```env
DEBUG=True
SECRET_KEY=django-insecure-local-dev-key-railway-ai-2026
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True

# Global Development Security Key (enforced in headers when DEBUG=True)
DEV_KEY=railway-dev-secret-2026

# Optional: Leave DATABASE_URL unset for zero-config local SQLite (db.sqlite3)
# DATABASE_URL=postgresql://user:pass@localhost:5432/railway_db

# External Railway Telemetry
RAILKIT_API_KEY=your_railkit_api_key_here
ENABLE_LIVE_SYNC=False
```

> [!TIP]
> **Anti-Spam `X-DEV-KEY` Header (when `DEBUG=True`)**:
> To prevent unauthorized access or spam in local/staging deployments when `DEBUG=True`, all API requests must include the header `X-DEV-KEY: <DEV_KEY>` (default: `railway-dev-secret-2026`). Preflight `OPTIONS`, static files, and `/admin/` are automatically exempted.

> [!NOTE]
> **DRF API Rate Limiting & Anti-Spam Throttling**:
> Built-in DRF throttling protects all API endpoints from spam and automated flooding:
> - **Public/Anonymous**: `100 requests/minute` (IP-based).
> - **Authenticated**: `300 requests/minute`.
> - **AI / Solver Endpoints**: `30 requests/minute` (dedicated throttle on CP-SAT feasible window calculation & recommendation endpoints).
> Exceeding limits returns `HTTP 429 Too Many Requests` with a `Retry-After` header. Configurable via `THROTTLE_RATE_ANON`, `THROTTLE_RATE_USER`, and `THROTTLE_RATE_AI`.


---

## 8. 🧪 Automated Testing & Verification

### 8.1 Embedded AI Unit Test Suite
Verify that the in-memory CP-SAT optimizer, XGBoost risk predictor, and fallback paths run cleanly:
```bash
# With uv
uv run python -m unittest tests/test_embedded_ai.py

# Or standard python
python -m unittest tests/test_embedded_ai.py
```
*Expected Result:* `Ran 4 tests in ~0.1s — OK`

### 8.2 ML Engine Diagnostics (One-Liner)
Directly verify that all 6 ML components and calibrated model artifacts are active:
```bash
uv run python -c "from src.services.ml_engine import RailwayMLEngine; print(RailwayMLEngine().health())"
```

### 8.3 1-Click Bruno API Test Suite
The repository includes a ready-to-use **[Bruno Collection](bruno/)** containing **35 automated API requests across 7 functional domains**:

1. Open **Bruno Desktop App**.
2. Click **Open Collection** and select the [`bruno/`](bruno/) directory.
3. Select environment: **Local** (`http://127.0.0.1:8000`) or **Production** (`https://backend-oz3h.onrender.com`).
4. Right-click the collection and select **Run Collection** to execute all 35 endpoint tests in one click!

Alternatively, run via **Bruno CLI**:
```bash
bru run bruno/ --env Local
```

---

## 9. Connecting with the Frontend

The Frontend (Next.js / React) communicates **exclusively** with this backend. It never needs an external ML port:

- **Local Development**: In `frontend/.env.local`, set:
  ```env
  NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/railways
  ```
- **Production Cloud Deployment**: When the unified backend is deployed, set:
  ```env
  NEXT_PUBLIC_API_URL=https://backend-oz3h.onrender.com/railways
  ```

### 📖 Frontend Integration Documentation
For complete TypeScript interfaces, custom React hook (`useBlockRecommendation`), and ready-to-use UI components that execute the `PUT` request to update recommended slots, see the dedicated guide:
👉 **[FRONTEND_AI_RECOMMENDATION_GUIDE.md](FRONTEND_AI_RECOMMENDATION_GUIDE.md)**

---

## 10. ☁️ Production Deployment (Render / Docker)

The backend runs as a single unified service with embedded ML capabilities.

### 10.1 Key Deployment Details
- **No Separate AI Container**: The AI/ML models run in-memory within the Django process. No extra microservices or `AI_SERVICE_URL` configurations are needed.
- **Prebuilt Linux Wheels**: PyPI provides precompiled Linux wheels for `ortools`, `xgboost`, and `scikit-learn`, requiring no C++ build tools on Render.

### 10.2 Memory Management on Render (512 MB Free Tier)
To prevent Out-Of-Memory (OOM / error 137) errors on Render's 512 MB Free Tier, configure Gunicorn to run with **2 workers and 2 threads**:

```bash
gunicorn config.wsgi:application --workers 2 --threads 2 --bind 0.0.0.0:$PORT
```

### 10.3 Required Environment Variables on Render
- `DEBUG=False`
- `SECRET_KEY=<strong-random-key>`
- `DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require`
- `ALLOWED_HOSTS=*` (or `backend-oz3h.onrender.com`)
- `CSRF_TRUSTED_ORIGINS=https://backend-oz3h.onrender.com`
- `REDIS_URL=redis://...` *(if using Celery with Upstash/Cloud Redis)*
- `RAILKIT_API_KEY=<your_api_key>`