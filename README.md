# AI-Powered Automatic Block Planning — Unified Backend & Intelligence Engine

Enterprise-grade backend service and intelligence engine for the **SIH Railways AI-Powered Automatic Block Planning** system.

The platform is architected as a **unified, high-performance monolith**:
- **Web & API Framework**: **Django 6.1+ & Django REST Framework (DRF)**.
- **Relational Persistence**: **PostgreSQL 16** (Supabase / Managed PaaS) with zero-config local **SQLite** fallback.
- **Embedded AI/ML Intelligence**: **Google OR-Tools CP-SAT** discrete constraint optimizer and **Calibrated XGBoost** failure predictor running **in-memory** (0ms latency, zero extra microservice ports).
- **Asynchronous Task Workers**: **Celery 5.6+ & Redis** for timetable synchronization and live train telemetry.
- **External Telemetry Provider**: **RailKit API** for real-time timetables, master train data, and train movement updates.
- **Client Test Suite**: 33 automated tests in a git-friendly **Bruno API Collection**.

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
- **Maintenance Task Lifecycle**: Tracks defect logs, required durations, severity ratings, urgency levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and task states (`PENDING`, `SCHEDULED`, `COMPLETED`, `CANCELLED`).
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
│   ├── maintenance/                   # Defect logs, severity ratings, and deadlines
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
│   ├── urls.py                        # Root API view (/), health probes, and router includes
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

## 3. Base URLs & Probes

| URL Path | Method | Description | Sample Output |
|---|:---:|---|---|
| **`http://127.0.0.1:8000/`** | `GET` | **Root API Index**: Service metadata, version, active endpoints, and AI capabilities. | `{"status": "online", "features": {"embedded_ai_engine": true, ...}}` |
| **`http://127.0.0.1:8000/ready/`** | `GET` | **Readiness Probe**: Verifies database connectivity and embedded AI engine health. | `{"status": "ready", "database": "connected", "ai_service": "online"}` |
| **`http://127.0.0.1:8000/health/`** | `GET` | **Liveness Probe**: Lightweight HTTP 200 ping for container orchestrators. | `{"status": "ok", "service": "railway-backend"}` |
| **`http://127.0.0.1:8000/railways/`** | `GET` | **DRF Browsable API**: Interactive directory of all REST endpoints. | Links to sections, assets, tasks, trains, block-windows, etc. |
| **`http://127.0.0.1:8000/admin/`** | `GET` | **Django Administration Panel**: Visual model browser and data editor. | Django Admin login interface. |

### Timezone Standard: Indian Standard Time (IST - Asia/Kolkata)
All API inputs, outputs, and Celery cron evaluations operate on formatted IST (`YYYY-MM-DD HH:MM:SS`):
```text
2026-09-06 14:30:00
```

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
| **Conflict Check** | `POST` | `/railways/block-windows/check-conflict/` | Check train movement collisions during a proposed window |
| **Feasible Windows (AI)** | `POST` | `/railways/block-windows/feasible-windows/` | **Executes Google OR-Tools CP-SAT Solver** to compute optimal maintenance windows |

---

## 5. Sample API Payloads & AI Engine Outputs

### 5.1 Feasible Maintenance Windows with CP-SAT Solver (`POST /railways/block-windows/feasible-windows/`)

When a maintenance task and a block window are submitted, the backend invokes the in-memory **Google OR-Tools CP-SAT solver**:

**Request Body:**
```json
{
  "task_id": "TSK-AI-FEASIBLE-1",
  "block_window_id": 1
}
```

**Response (`200 OK` returned in ~0.3s):**
```json
{
  "task_id": "TSK-AI-FEASIBLE-1",
  "block_window_id": 1,
  "section": "NDLS-CNB",
  "required_duration_minutes": 90,
  "feasible": true,
  "windows": [
    {
      "start": "2026-09-06 07:30:00",
      "end": "2026-09-06 09:00:00",
      "duration_minutes": 90,
      "decision_score": 0.3775,
      "algorithm": "CP-SAT Constraint Solver"
    }
  ]
}
```

### 5.2 Conflict Check Engine (`POST /railways/block-windows/check-conflict/`)

Detects whether any scheduled or live trains overlap with a proposed maintenance time range:

**Request Body:**
```json
{
  "section": 1,
  "maintenance_start": "2026-09-06 02:00:00",
  "maintenance_end": "2026-09-06 05:00:00"
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
      "entry_time": "2026-09-06 02:30:00",
      "exit_time": "2026-09-06 03:15:00"
    }
  ]
}
```

### 5.3 Live Operations Dashboard (`GET /railways/trains/operations/?date=2026-09-06&source=NDLS&destination=CNB`)

Aggregates master train data, scheduled arrival/departure, and live-synced tracking records:

```json
{
  "date": "2026-09-06",
  "source": "NDLS",
  "destination": "CNB",
  "count": 1,
  "trains": [
    {
      "train_number": "12004",
      "train_name": "Lucknow Shatabdi Express",
      "train_type": "SHATABDI",
      "priority": 9,
      "section": {
        "name": "New Delhi - Kanpur Central",
        "source": "New Delhi",
        "source_code": "NDLS",
        "destination": "Kanpur Central",
        "destination_code": "CNB"
      },
      "schedule": {
        "entry_time": "06:10:00",
        "exit_time": "06:45:00"
      },
      "movement": {
        "actual_entry_time": "2026-09-06 06:15:00",
        "actual_exit_time": "2026-09-06 06:50:00"
      },
      "delay_minutes": 5
    }
  ]
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

---

## 7. Running & Developing Locally

### 7.1 Setup Environment

1. **Activate Virtual Environment**:
   ```powershell
   # Windows PowerShell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure Local Environment File (`.env`)**:
   Create a `.env` file in the backend root:
   ```env
   DEBUG=True
   SECRET_KEY=django-insecure-local-dev-key-railway-ai-2026
   ALLOWED_HOSTS=*
   CORS_ALLOW_ALL_ORIGINS=True
   PREFER_EMBEDDED_AI=True

   # Optional: Leave DATABASE_URL commented out for zero-config local SQLite (db.sqlite3)
   # DATABASE_URL=postgresql://railway_admin:railway_secure_pass@localhost:5432/railway_prod
   ```

4. **Run Database Migrations**:
   ```powershell
   python manage.py migrate
   ```

5. **Start the Development Server**:
   ```powershell
   python manage.py runserver 8000
   ```
   Open `http://127.0.0.1:8000/` in your browser. The embedded AI engine will initialize automatically in-memory.

---

## 8. 🧪 Automated Testing & Verification

### 8.1 Embedded AI Unit Test Suite
Verify that the in-memory CP-SAT optimizer and failure predictors run cleanly:
```powershell
python -m unittest tests/test_embedded_ai.py
```
*Expected Result:* `Ran 4 tests in ~2.1s — OK`

### 8.2 Full Integration Test Suite
```powershell
python tests/test_local_integration.py
```
*Expected Result:* `Ran 4 tests in ~6.5s — OK`

### 8.3 1-Click Bruno API Test Suite
The repository includes a ready-to-use **[Bruno Collection](bruno/)** containing **33 API requests**:

1. Open **Bruno Desktop App**.
2. Click **Open Collection** and select the [`bruno/`](bruno/) directory.
3. Select environment: **Local** (`http://127.0.0.1:8000`) or **Production**.
4. Right-click the collection and select **Run Collection** to execute all 33 endpoint tests in one click!

Alternatively, run via **Bruno CLI**:
```bash
bru run bruno/ --env Local
```

---

## 9. Connecting with the Frontend

The Frontend (Next.js 16) communicates **exclusively** with this backend. It never communicates with an external ML port:

- **Local Development**: In `frontend/.env.local`, set:
  ```env
  NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/railways
  ```
- **Production Cloud Deployment**: When the unified backend is deployed (e.g. `https://api.yourdomain.com`), set:
  ```env
  NEXT_PUBLIC_API_URL=https://api.yourdomain.com/railways
  ```
  *(Deploying the backend automatically deploys the AI engine in the same container with zero extra configuration).*