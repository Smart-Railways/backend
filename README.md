# AI-Powered Automatic Block Planning --- Backend

Backend service for the **SIH Railways AI-Powered Automatic Block
Planning** system.

The backend is built with **Django + Django REST Framework (DRF)** and
uses **PostgreSQL (Supabase)** as the database.

The current backend handles:

-   Railway corridor sections
-   Railway assets
-   Maintenance tasks
-   Trains
-   Train movements through sections
-   Maintenance block windows
-   Train/block conflict detection
-   Feasible maintenance-window calculation
-   REST APIs for CRUD operations

The ML risk-scoring and OR-Tools automatic scheduling layers are the
next stage of development.

------------------------------------------------------------------------

## 1. Tech Stack

  Technology              Purpose
  ----------------------- ------------------------------------------
  Python                  Backend language
  Django                  Web framework
  Django REST Framework   REST API
  PostgreSQL              Database
  Supabase                Hosted PostgreSQL
  `psycopg`               PostgreSQL driver
  `dj-database-url`       Database URL configuration
  `python-dotenv`         Environment variables
  uv                      Python package/project management
  Celery + Redis          Planned/used for asynchronous processing
  XGBoost                 Planned ML risk model
  scikit-learn            Planned ML preprocessing/model pipeline
  OR-Tools                Planned schedule optimization

------------------------------------------------------------------------

# 2. Project Structure

``` text
backend/
├── manage.py
├── pyproject.toml
├── uv.lock
├── .env
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── router.py
│
└── apps/
    ├── corridors/
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   └── ...
    │
    ├── assets/
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   └── ...
    │
    ├── maintenance/
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   └── ...
    │
    ├── trains/
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   └── ...
    │
    └── blocks/
        ├── models.py
        ├── serializers.py
        ├── views.py
        ├── services.py
        └── ...
```

------------------------------------------------------------------------

# 3. Base API URL

All API routes are registered under:

``` text
/api/
```

For local development:

``` text
http://127.0.0.1:8000/api/
```

Django admin:

``` text
http://127.0.0.1:8000/admin/
```

------------------------------------------------------------------------

# 4. Database Configuration

The backend uses a PostgreSQL database hosted on Supabase.

The connection is configured through:

``` env
DATABASE_URL=postgresql://...
```

`settings.py`:

``` python
import os
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL")
    )
}
```

Do **not** commit `.env` to Git.

------------------------------------------------------------------------

# 5. Timezone

The backend uses Indian Standard Time:

``` python
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
```

Django stores timezone-aware timestamps and handles UTC internally.

Frontend requests should preferably send timezone-aware ISO timestamps:

``` text
2026-09-03T10:00:00+05:30
```

------------------------------------------------------------------------

# 6. Data Models

## 6.1 RailwaySection

Location:

``` text
apps/corridors/models.py
```

Represents a railway corridor section.

``` python
class RailwaySection(models.Model):
    name = models.CharField(max_length=200)
    source_station = models.CharField(max_length=100)
    destination_station = models.CharField(max_length=100)
    distance_km = models.FloatField()
    is_active = models.BooleanField(default=True)
```

### Fields

  Field                   Type      Description
  ----------------------- --------- ---------------------------
  `id`                    Integer   Primary key
  `name`                  String    Section name
  `source_station`        String    Starting station
  `destination_station`   String    Destination station
  `distance_km`           Float     Section distance
  `is_active`             Boolean   Whether section is active

Example:

``` json
{
    "id": 1,
    "name": "New Delhi - Mathura",
    "source_station": "New Delhi",
    "destination_station": "Mathura",
    "distance_km": 58.0,
    "is_active": true
}
```

------------------------------------------------------------------------

# 7. Asset Model

Location:

``` text
apps/assets/models.py
```

An asset belongs to a railway section and a railway department.

## Departments

``` python
class Department(models.TextChoices):
    ENGINEERING = "ENGINEERING", "Engineering"
    SNT = "SNT", "Signal & Telecom"
    TRACTION = "TRACTION", "Traction"
```

## Model

``` python
class Asset(models.Model):
    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="assets"
    )
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=100)
    department = models.CharField(
        max_length=20,
        choices=Department.choices
    )
    criticality = models.PositiveIntegerField()
    installation_date = models.DateField(
        null=True,
        blank=True
    )
```

### Fields

  Field                 Description
  --------------------- ------------------------------
  `id`                  Primary key
  `section`             Railway section
  `name`                Asset name
  `asset_type`          Type of railway asset
  `department`          Engineering / S&T / Traction
  `criticality`         Asset criticality, 1--10
  `installation_date`   Installation date

------------------------------------------------------------------------

# 8. MaintenanceTask Model

Location:

``` text
apps/maintenance/models.py
```

Represents a maintenance job that needs to be performed.

## Priority

``` python
class Priority(models.TextChoices):
    CRITICAL = "CRITICAL", "Critical"
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"
```

## Status

``` python
class Status(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SCHEDULED = "SCHEDULED", "Scheduled"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
```

## Model

``` python
class MaintenanceTask(models.Model):
    task_id = models.CharField(
        max_length=100,
        unique=True
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="maintenance_tasks"
    )

    description = models.TextField()
    severity = models.PositiveIntegerField()
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices
    )
    due_date = models.DateField()
    duration_minutes = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default="PENDING"
    )

    is_overdue = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )
```

### Fields

  Field                Description
  -------------------- ------------------------------------
  `task_id`            Unique maintenance task identifier
  `asset`              Asset requiring maintenance
  `description`        Maintenance description
  `severity`           Problem severity, 1--10
  `priority`           CRITICAL / HIGH / MEDIUM / LOW
  `due_date`           Maintenance deadline
  `duration_minutes`   Required maintenance duration
  `status`             Current task status
  `is_overdue`         Whether task is overdue
  `created_at`         Creation timestamp

Example:

``` json
{
    "task_id": "TMS-001",
    "asset": 1,
    "description": "Rail crack inspection and repair",
    "severity": 9,
    "priority": "CRITICAL",
    "due_date": "2026-09-05",
    "duration_minutes": 90,
    "status": "PENDING",
    "is_overdue": false
}
```

------------------------------------------------------------------------

# 9. Train Model

Location:

``` text
apps/trains/models.py
```

Represents a train operating through the railway network.

## Train Types

``` python
class TrainType(models.TextChoices):
    PASSENGER = "PASSENGER", "Passenger"
    EXPRESS = "EXPRESS", "Express"
    RAJDHANI = "RAJDHANI", "Rajdhani"
    VB = "VB", "Vande Bharat"
    SHATABDI = "SHATABDI", "Shatabdi"
    FREIGHT = "FREIGHT", "Freight"
```

## Model

``` python
class Train(models.Model):
    train_number = models.CharField(
        max_length=10,
        unique=True
    )

    name = models.CharField(max_length=100)

    train_type = models.CharField(
        max_length=20,
        choices=TrainType.choices
    )

    priority = models.PositiveIntegerField(
        default=5
    )
```

Train priority is constrained to:

``` text
1–10
```

Higher value means higher operational priority.

------------------------------------------------------------------------

# 10. TrainMovement Model

A train itself does not tell us when it occupies a section.

`TrainMovement` represents the time interval during which a train
occupies a specific railway section.

``` python
class TrainMovement(models.Model):
    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name="movements"
    )

    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="train_movements"
    )

    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField()
```

Example:

``` json
{
    "train": 1,
    "section": 1,
    "entry_time": "2026-09-03T16:20:00+05:30",
    "exit_time": "2026-09-03T16:35:00+05:30"
}
```

This is used by the block conflict engine.

------------------------------------------------------------------------

# 11. BlockWindow Model

Location:

``` text
apps/blocks/models.py
```

A `BlockWindow` represents a period during which maintenance can
potentially be performed on a railway section.

## Status

``` python
class Status(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    RESERVED = "RESERVED", "Reserved"
    BLOCKED = "BLOCKED", "Blocked"
```

## Model

``` python
class BlockWindow(models.Model):
    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="block_windows"
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default="AVAILABLE"
    )
```

Example:

``` json
{
    "section": 1,
    "start_time": "2026-09-03T16:00:00+05:30",
    "end_time": "2026-09-03T18:30:00+05:30",
    "status": "AVAILABLE"
}
```

------------------------------------------------------------------------

# 12. API Routing

The project uses DRF's `DefaultRouter`.

Current routes:

``` text
/api/sections/
/api/assets/
/api/maintenance/
/api/trains/
/api/movements/
/api/blocks/
```

Router configuration is maintained in:

``` text
config/router.py
```

Example:

``` python
router.register(
    "sections",
    RailwaySectionViewSet,
    basename="section"
)

router.register(
    "assets",
    AssetViewSet,
    basename="asset"
)

router.register(
    "maintenance",
    MaintenanceTaskViewSet,
    basename="maintenance"
)

router.register(
    "trains",
    TrainViewSet,
    basename="train"
)

router.register(
    "movements",
    TrainMovementViewSet,
    basename="movement"
)

router.register(
    "blocks",
    BlockWindowViewSet,
    basename="block"
)
```

------------------------------------------------------------------------

# 13. CRUD Endpoints

All CRUD endpoints are implemented using DRF `ModelViewSet`.

Therefore each resource supports:

``` text
GET     collection
POST    collection
GET     detail
PUT     detail
PATCH   detail
DELETE  detail
```

------------------------------------------------------------------------

## 13.1 Railway Sections

### List sections

``` http
GET /api/sections/
```

### Create section

``` http
POST /api/sections/
Content-Type: application/json
```

Example:

``` json
{
    "name": "New Delhi - Mathura",
    "source_station": "New Delhi",
    "destination_station": "Mathura",
    "distance_km": 58.0,
    "is_active": true
}
```

### Get section

``` http
GET /api/sections/{id}/
```

### Update section

``` http
PUT /api/sections/{id}/
```

### Partial update

``` http
PATCH /api/sections/{id}/
```

### Delete

``` http
DELETE /api/sections/{id}/
```

------------------------------------------------------------------------

# 14. Asset Endpoints

### List assets

``` http
GET /api/assets/
```

### Create asset

``` http
POST /api/assets/
```

Example:

``` json
{
    "section": 1,
    "name": "NDLS-MTJ Track Section 01",
    "asset_type": "Track",
    "department": "ENGINEERING",
    "criticality": 9,
    "installation_date": "2020-01-15"
}
```

### Get asset

``` http
GET /api/assets/{id}/
```

### Update

``` http
PUT /api/assets/{id}/
```

### Partial update

``` http
PATCH /api/assets/{id}/
```

### Delete

``` http
DELETE /api/assets/{id}/
```

The asset API also exposes the related section name through a read-only
field:

``` json
{
    "section": 1,
    "section_name": "New Delhi - Mathura"
}
```

------------------------------------------------------------------------

# 15. Maintenance Endpoints

### List maintenance tasks

``` http
GET /api/maintenance/
```

### Create task

``` http
POST /api/maintenance/
```

Example:

``` json
{
    "task_id": "TMS-001",
    "asset": 1,
    "description": "Rail crack inspection and repair",
    "severity": 9,
    "priority": "CRITICAL",
    "due_date": "2026-09-05",
    "duration_minutes": 90,
    "status": "PENDING",
    "is_overdue": false
}
```

### Get task

``` http
GET /api/maintenance/{id}/
```

### Update task

``` http
PUT /api/maintenance/{id}/
```

### Partial update

``` http
PATCH /api/maintenance/{id}/
```

### Delete

``` http
DELETE /api/maintenance/{id}/
```

------------------------------------------------------------------------

# 16. Train Endpoints

### List trains

``` http
GET /api/trains/
```

### Create train

``` http
POST /api/trains/
```

Example:

``` json
{
    "train_number": "12951",
    "name": "Mumbai Rajdhani",
    "train_type": "RAJDHANI",
    "priority": 10
}
```

### Get train

``` http
GET /api/trains/{id}/
```

### Update

``` http
PUT /api/trains/{id}/
```

### Partial update

``` http
PATCH /api/trains/{id}/
```

### Delete

``` http
DELETE /api/trains/{id}/
```

------------------------------------------------------------------------

# 17. Train Movement Endpoints

### List movements

``` http
GET /api/movements/
```

### Create movement

``` http
POST /api/movements/
```

Example:

``` json
{
    "train": 1,
    "section": 1,
    "entry_time": "2026-09-03T16:20:00+05:30",
    "exit_time": "2026-09-03T16:35:00+05:30"
}
```

### Get movement

``` http
GET /api/movements/{id}/
```

### Update

``` http
PUT /api/movements/{id}/
```

### Partial update

``` http
PATCH /api/movements/{id}/
```

### Delete

``` http
DELETE /api/movements/{id}/
```

------------------------------------------------------------------------

# 18. Block Window Endpoints

### List block windows

``` http
GET /api/blocks/
```

### Create block window

``` http
POST /api/blocks/
```

Example:

``` json
{
    "section": 1,
    "start_time": "2026-09-03T16:00:00+05:30",
    "end_time": "2026-09-03T18:30:00+05:30",
    "status": "AVAILABLE"
}
```

### Get block

``` http
GET /api/blocks/{id}/
```

### Update

``` http
PUT /api/blocks/{id}/
```

### Partial update

``` http
PATCH /api/blocks/{id}/
```

### Delete

``` http
DELETE /api/blocks/{id}/
```

------------------------------------------------------------------------

# 19. Block Conflict Detection

This is one of the first actual planning/railway-specific services in
the backend.

Endpoint:

``` http
POST /api/blocks/check-conflict/
```

It checks whether trains occupy the requested railway section during the
proposed maintenance period.

## Request

``` json
{
    "section": 1,
    "maintenance_start": "2026-09-03T16:00:00+05:30",
    "maintenance_end": "2026-09-03T17:30:00+05:30"
}
```

## Validation

The backend rejects:

``` text
maintenance_end <= maintenance_start
```

with a validation error.

## Conflict rule

A train movement conflicts with maintenance when:

``` python
entry_time < maintenance_end
AND
exit_time > maintenance_start
```

In Django:

``` python
TrainMovement.objects.filter(
    section=section,
    entry_time__lt=maintenance_end,
    exit_time__gt=maintenance_start,
)
```

This correctly handles overlapping intervals.

For example:

``` text
Maintenance:
16:00 ───────────────── 17:30

Train:
          16:20 ─ 16:35
          ↑ conflict
```

## Response

Example:

``` json
{
    "has_conflict": true,
    "conflict_count": 2,
    "conflicts": [
        {
            "train_number": "12951",
            "train_name": "Mumbai Rajdhani",
            "entry_time": "2026-09-03T16:20:00+05:30",
            "exit_time": "2026-09-03T16:35:00+05:30"
        },
        {
            "train_number": "12002",
            "train_name": "Bhopal Shatabdi",
            "entry_time": "2026-09-03T17:10:00+05:30",
            "exit_time": "2026-09-03T17:25:00+05:30"
        }
    ]
}
```

If no train conflicts:

``` json
{
    "has_conflict": false,
    "conflict_count": 0,
    "conflicts": []
}
```

------------------------------------------------------------------------

# 20. Feasible Maintenance Windows

Endpoint:

``` http
POST /api/blocks/feasible-windows/
```

This endpoint determines **where a maintenance task can fit inside an
available block window without overlapping train movements**.

It combines:

``` text
MaintenanceTask
+
BlockWindow
+
TrainMovement
```

------------------------------------------------------------------------

## Request

``` json
{
    "task_id": "TMS-001",
    "block_id": 1
}
```

The backend:

1.  Finds the maintenance task.
2.  Finds the block window.
3.  Checks that both belong to the same railway section.
4.  Gets the task's required duration.
5.  Finds train movements inside the block window.
6.  Calculates gaps between trains.
7.  Returns gaps large enough for the maintenance task.

------------------------------------------------------------------------

## Section validation

A maintenance task and block must belong to the same section.

For example:

``` text
Task:
New Delhi - Mathura

Block:
Agra - Gwalior
```

returns:

``` json
{
    "error": "Maintenance task and block belong to different sections."
}
```

with HTTP status:

``` text
400 Bad Request
```

------------------------------------------------------------------------

## Example

Suppose:

``` text
Block:
16:00 ───────────────────────── 18:30

Train 1:
       16:20 ─ 16:35

Train 2:
                    17:10 ─ 17:25

Task duration:
90 minutes
```

The algorithm examines:

``` text
16:00 ─ 16:20 = 20 min
16:35 ─ 17:10 = 35 min
17:25 ─ 18:30 = 65 min
```

None of these can fit a 90-minute task.

Therefore:

``` json
{
    "feasible": false,
    "windows": []
}
```

If a sufficiently large gap exists, it is returned.

------------------------------------------------------------------------

## Example response

``` json
{
    "task_id": "TMS-001",
    "block_id": 1,
    "section": "New Delhi - Mathura",
    "required_duration_minutes": 90,
    "feasible": true,
    "windows": [
        {
            "start": "2026-09-03T01:00:00+05:30",
            "end": "2026-09-03T03:00:00+05:30",
            "duration_minutes": 120
        }
    ]
}
```

The returned window represents an available interval **inside the
selected block window**.

------------------------------------------------------------------------

# 21. Feasible Window Algorithm

Implemented in:

``` text
apps/blocks/services.py
```

Function:

``` python
find_feasible_windows(
    section,
    block_start,
    block_end,
    duration_minutes
)
```

The algorithm:

``` text
Block Start
     │
     ↓
Get train movements overlapping block
     │
     ↓
Sort by entry time
     │
     ↓
Check gap before each train
     │
     ├── gap >= required duration → feasible
     │
     └── gap < required duration → ignore
     │
     ↓
Check final gap after last train
     │
     ↓
Return all feasible windows
```

Train movements are filtered using:

``` python
TrainMovement.objects.filter(
    section=section,
    entry_time__lt=block_end,
    exit_time__gt=block_start,
).order_by("entry_time")
```

This prevents irrelevant train movements outside the block from
affecting the result.

------------------------------------------------------------------------

# 22. Current Backend Architecture

``` text
                    Next.js Frontend
                           │
                           │ REST API
                           ↓
                Django REST Framework
                           │
          ┌────────────────┼─────────────────┐
          ↓                ↓                 ↓
      ViewSets         Serializers       Services
          │                                  │
          └────────────────┬─────────────────┘
                           ↓
                     Django ORM
                           │
                           ↓
                  Supabase PostgreSQL
```

------------------------------------------------------------------------

# 23. Current Planning Logic

The current backend has three levels of logic.

### Level 1 --- CRUD

``` text
Sections
Assets
Maintenance
Trains
Train Movements
Block Windows
```

### Level 2 --- Rule-based planning

``` text
Train Movement
       +
Maintenance period
       ↓
Conflict Detection
```

and:

``` text
Maintenance Task
       +
Block Window
       +
Train Movements
       ↓
Feasible Windows
```

### Level 3 --- AI/Optimization --- NEXT

``` text
Maintenance + Asset + Section
              ↓
             ML
              ↓
         Risk Score
              ↓
       OR-Tools Optimizer
              ↑
      Train Movements
      Block Windows
              ↓
       Final Schedule
```

------------------------------------------------------------------------

# 24. ML Layer --- Planned

The ML model will predict maintenance risk.

The model will use meaningful features from multiple Django models.

### MaintenanceTask features

``` text
severity
priority
days_until_due
is_overdue
duration_minutes
```

### Asset features

``` text
criticality
department
asset_type
```

### RailwaySection features

``` text
distance_km
```

The training feature vector will therefore look like:

``` text
severity
criticality
priority
days_until_due
is_overdue
duration_minutes
department
asset_type
section_distance
```

The model will produce:

``` text
risk_score
risk_level
```

Example:

``` json
{
    "task_id": "TMS-001",
    "risk_score": 91.7,
    "risk_level": "CRITICAL"
}
```

The first version will be trained using synthetic data. Later, the
synthetic training data will be replaced with real historical railway
maintenance data.

Important:

**The ML model determines risk/urgency. It does not determine the final
maintenance time.**

------------------------------------------------------------------------

# 25. Optimization Layer --- Planned

After ML calculates risk:

``` text
Maintenance Tasks
       ↓
Risk Scores
       ↓
OR-Tools
       ↑
Train Movements
Block Windows
Task Durations
Department compatibility
       ↓
Optimized Schedule
```

The optimizer will eventually handle:

-   Maintenance priority
-   Task duration
-   Train conflicts
-   Available block windows
-   Multi-department coordination
-   Combining compatible maintenance tasks
-   Minimizing operational disruption
-   Maximizing block utilization
-   Weekly/monthly planning

Example:

``` text
Engineering task ────┐
                     │
S&T task ────────────┼──→ SAME BLOCK
                     │
Traction task ───────┘
```

Instead of:

``` text
Engineering → Block 1
S&T         → Block 2
Traction    → Block 3
```

the optimizer should eventually find:

``` text
Engineering
S&T
Traction
     ↓
ONE coordinated block
```

when operationally feasible.

------------------------------------------------------------------------

# 26. Representative Corridor

The current MVP uses representative sections of the New Delhi--Mumbai
corridor:

``` text
New Delhi
    ↓
Mathura
    ↓
Agra
    ↓
Gwalior
    ↓
Jhansi
    ↓
Bina
    ↓
Bhopal
    ↓
Ratlam
    ↓
Vadodara
    ↓
Surat
    ↓
Mumbai
```

The first implementation can use the initial seven representative
sections:

``` text
1. New Delhi → Mathura
2. Mathura → Agra
3. Agra → Gwalior
4. Gwalior → Jhansi
5. Jhansi → Bina
6. Bina → Bhopal
7. Bhopal → Ratlam
```

These are prototype planning sections for the MVP and should not be
treated as official railway block-section definitions.

------------------------------------------------------------------------

# 27. Running the Backend

From the backend directory:

``` bash
uv run python manage.py runserver
```

The server will normally start at:

``` text
http://127.0.0.1:8000/
```

API:

``` text
http://127.0.0.1:8000/api/
```

------------------------------------------------------------------------

# 28. Database Migrations

After changing models:

``` bash
uv run python manage.py makemigrations
```

Then:

``` bash
uv run python manage.py migrate
```

To inspect migration status:

``` bash
uv run python manage.py showmigrations
```

------------------------------------------------------------------------

# 29. Django Admin

Create an admin user:

``` bash
uv run python manage.py createsuperuser
```

Then open:

``` text
/admin/
```

Admin is useful for quickly creating and inspecting:

-   Railway sections
-   Assets
-   Maintenance tasks
-   Trains
-   Train movements
-   Block windows

------------------------------------------------------------------------

# 30. API Summary

  ---------------------------------------------------------------------------------
  Method                  Endpoint                          Purpose
  ----------------------- --------------------------------- -----------------------
  GET                     `/api/sections/`                  List sections

  POST                    `/api/sections/`                  Create section

  GET                     `/api/sections/{id}/`             Get section

  PUT/PATCH               `/api/sections/{id}/`             Update section

  DELETE                  `/api/sections/{id}/`             Delete section

  GET                     `/api/assets/`                    List assets

  POST                    `/api/assets/`                    Create asset

  GET                     `/api/assets/{id}/`               Get asset

  PUT/PATCH               `/api/assets/{id}/`               Update asset

  DELETE                  `/api/assets/{id}/`               Delete asset

  GET                     `/api/maintenance/`               List maintenance tasks

  POST                    `/api/maintenance/`               Create maintenance task

  GET                     `/api/maintenance/{id}/`          Get task

  PUT/PATCH               `/api/maintenance/{id}/`          Update task

  DELETE                  `/api/maintenance/{id}/`          Delete task

  GET                     `/api/trains/`                    List trains

  POST                    `/api/trains/`                    Create train

  GET                     `/api/trains/{id}/`               Get train

  PUT/PATCH               `/api/trains/{id}/`               Update train

  DELETE                  `/api/trains/{id}/`               Delete train

  GET                     `/api/movements/`                 List train movements

  POST                    `/api/movements/`                 Create movement

  GET                     `/api/movements/{id}/`            Get movement

  PUT/PATCH               `/api/movements/{id}/`            Update movement

  DELETE                  `/api/movements/{id}/`            Delete movement

  GET                     `/api/blocks/`                    List block windows

  POST                    `/api/blocks/`                    Create block window

  GET                     `/api/blocks/{id}/`               Get block

  PUT/PATCH               `/api/blocks/{id}/`               Update block

  DELETE                  `/api/blocks/{id}/`               Delete block

  POST                    `/api/blocks/check-conflict/`     Check train/maintenance
                                                            conflict

  POST                    `/api/blocks/feasible-windows/`   Find feasible
                                                            maintenance windows
  ---------------------------------------------------------------------------------

------------------------------------------------------------------------

# 31. Current Status

### Completed

-   [x] Django project
-   [x] Django REST Framework
-   [x] PostgreSQL/Supabase connection
-   [x] IST timezone configuration
-   [x] Railway section model
-   [x] Asset model
-   [x] Maintenance task model
-   [x] Train model
-   [x] Train movement model
-   [x] Block window model
-   [x] CRUD APIs
-   [x] DRF router
-   [x] Conflict detection
-   [x] Conflict validation
-   [x] Feasible-window calculation
-   [x] Task/block section validation

### In Progress / Next

-   [ ] Synthetic ML dataset
-   [ ] XGBoost risk model
-   [ ] Model evaluation
-   [ ] Saved ML pipeline
-   [ ] Django ML predictor
-   [ ] `/api/planning/predict-risk/`
-   [ ] OR-Tools optimization
-   [ ] Automatic block allocation
-   [ ] Multi-department task grouping
-   [ ] Weekly/monthly planning
-   [ ] Dynamic rescheduling
-   [ ] Frontend integration

------------------------------------------------------------------------

# 32. Intended Final Architecture

``` text
                     ┌──────────────────┐
                     │    Next.js FE     │
                     └────────┬─────────┘
                              │
                              ↓
                     ┌──────────────────┐
                     │       DRF        │
                     └────────┬─────────┘
                              │
               ┌──────────────┼──────────────┐
               ↓              ↓              ↓
          PostgreSQL         ML          OR-Tools
               │              │              │
               │              ↓              │
               │        Risk Prediction      │
               │              │              │
               └──────────────┼──────────────┘
                              ↓
                     Final Block Plan
                              │
                              ↓
                    Controller Approval
                              │
                              ↓
                             BDMS
```

The backend is therefore designed to evolve from a CRUD + rule-based
system into an **AI-assisted railway maintenance planning engine**
without changing the core domain models.
