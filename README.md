# AI-Powered Automatic Block Planning — Backend

Backend service for the **SIH Railways AI-Powered Automatic Block Planning** system.

The backend is built with **Django + Django REST Framework (DRF)** and uses **PostgreSQL (Supabase)** as the database.

The current backend handles:

- Railway corridor sections
- Railway assets
- Maintenance tasks
- Trains
- Train movements through sections
- Maintenance block windows
- Train/block conflict detection
- Feasible maintenance-window calculation
- REST APIs for CRUD operations
- Production hosting setup (CORS, WhiteNoise, Gunicorn, Docker, Render/Railway configs)

---

## 1. Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python** (>= 3.12) | Backend language |
| **Django** (6.x) | Web framework |
| **Django REST Framework** | REST API framework |
| **PostgreSQL** | Database (Supabase) |
| **psycopg (v3)** | PostgreSQL driver |
| **dj-database-url** | Database URL configuration |
| **django-cors-headers** | Cross-Origin Resource Sharing (CORS) |
| **WhiteNoise** | Production static files serving |
| **Gunicorn** | WSGI production web server |
| **python-dotenv** | Environment variable management |
| **uv** | Python package/project management |

---

## 2. Project Structure

```text
backend/
├── manage.py
├── pyproject.toml
├── requirements.txt
├── Procfile
├── build.sh
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── router.py
│   ├── wsgi.py
│   └── asgi.py
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

---

## 3. Base API URL

All API routes are registered under:

```text
/railways/
```

- **Local Development API**: `http://127.0.0.1:8000/railways/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`
- **Production API**: `https://<your-domain>/railways/`

---

## 4. Timezone Configuration

The backend operates under **Indian Standard Time (IST - Asia/Kolkata)**:

```python
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
```

All datetime fields returned by the API are formatted in human-readable IST format:
```text
YYYY-MM-DD HH:MM:SS  (e.g., "2026-09-03 17:30:00")
```

---

## 5. API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET / POST** | `/railways/sections/` | List or create railway sections |
| **GET / PUT / PATCH / DELETE** | `/railways/sections/{id}/` | Retrieve, update, or delete a railway section |
| **GET / POST** | `/railways/assets/` | List or create railway assets |
| **GET / PUT / PATCH / DELETE** | `/railways/assets/{id}/` | Retrieve, update, or delete an asset |
| **GET / POST** | `/railways/maintenances/` | List or create maintenance tasks |
| **GET / PUT / PATCH / DELETE** | `/railways/maintenances/{id}/` | Retrieve, update, or delete a maintenance task |
| **GET / POST** | `/railways/trains/` | List or create trains |
| **GET / PUT / PATCH / DELETE** | `/railways/trains/{id}/` | Retrieve, update, or delete a train |
| **GET / POST** | `/railways/train-movements/` | List or create train movements |
| **GET / PUT / PATCH / DELETE** | `/railways/train-movements/{id}/` | Retrieve, update, or delete a train movement |
| **GET / POST** | `/railways/blocks/` | List or create block windows |
| **GET / PUT / PATCH / DELETE** | `/railways/blocks/{id}/` | Retrieve, update, or delete a block window |
| **POST** | `/railways/blocks/check-conflict/` | Check train vs maintenance conflicts |
| **POST** | `/railways/blocks/feasible-windows/` | Find feasible maintenance gaps inside a block window |

---

## 6. Detailed Endpoint Documentation

### 6.1 Railway Sections (`/railways/sections/`)

#### List Sections
`GET /railways/sections/`

#### Create Section
`POST /railways/sections/`

```json
{
  "section_name": "New Delhi - Mathura",
  "origin_station": "New Delhi",
  "end_station": "Mathura",
  "distance": 140.0,
  "status": true
}
```

#### Response:
```json
{
  "id": 1,
  "section_name": "New Delhi - Mathura",
  "origin_station": "New Delhi",
  "end_station": "Mathura",
  "distance": 140.0,
  "status": true
}
```

---

### 6.2 Assets (`/railways/assets/`)

#### List Assets
`GET /railways/assets/`

#### Create Asset
`POST /railways/assets/`

```json
{
  "section": 1,
  "asset_title": "Track Circuit 01",
  "category": "TRACK_CIRCUIT",
  "division": "SNT",
  "risk_level": 7,
  "setup_date": "2024-01-15"
}
```

#### Response:
```json
{
  "id": 1,
  "asset_title": "Track Circuit 01",
  "category": "TRACK_CIRCUIT",
  "division": "SNT",
  "risk_level": 7,
  "setup_date": "2024-01-15",
  "section": 1,
  "section_name": "New Delhi - Mathura"
}
```

---

### 6.3 Maintenance Tasks (`/railways/maintenances/`)

#### List Tasks
`GET /railways/maintenances/`

#### Create Task
`POST /railways/maintenances/`

```json
{
  "task_code": "TMS-001",
  "asset": 1,
  "details": "Routine track circuit inspection and relay testing",
  "risk_rating": 8,
  "urgency": "HIGH",
  "deadline": "2026-09-10",
  "estimated_duration": 45,
  "task_status": "PENDING"
}
```

#### Response:
```json
{
  "id": 1,
  "task_code": "TMS-001",
  "asset": 1,
  "asset_name": "Track Circuit 01",
  "section_name": "New Delhi - Mathura",
  "details": "Routine track circuit inspection and relay testing",
  "risk_rating": 8,
  "urgency": "HIGH",
  "deadline": "2026-09-10",
  "estimated_duration": 45,
  "task_status": "PENDING",
  "is_delayed": false,
  "logged_at": "2026-09-02 21:50:00"
}
```

---

### 6.4 Trains (`/railways/trains/`)

#### List Trains
`GET /railways/trains/`

#### Create Train
`POST /railways/trains/`

```json
{
  "train_number": "22222",
  "name": "CSMT Rajdhani",
  "train_type": "RAJDHANI",
  "priority": 10
}
```

#### Response:
```json
{
  "id": 1,
  "train_number": "22222",
  "name": "CSMT Rajdhani",
  "train_type": "RAJDHANI",
  "priority": 10
}
```

---

### 6.5 Train Movements (`/railways/train-movements/`)

#### List Train Movements
`GET /railways/train-movements/`

#### Create Train Movement
`POST /railways/train-movements/`

```json
{
  "train": 1,
  "section": 1,
  "entry_time": "2026-09-03 17:40:00",
  "exit_time": "2026-09-03 18:10:00"
}
```

#### Response:
```json
{
  "id": 1,
  "train": 1,
  "train_number": "22222",
  "train_name": "CSMT Rajdhani",
  "section": 1,
  "section_name": "New Delhi - Mathura",
  "entry_time": "2026-09-03 17:40:00",
  "exit_time": "2026-09-03 18:10:00"
}
```

---

### 6.6 Block Windows (`/railways/blocks/`)

#### List Block Windows
`GET /railways/blocks/`

#### Create Block Window
`POST /railways/blocks/`

```json
{
  "section": 1,
  "start_time": "2026-09-03 17:30:00",
  "end_time": "2026-09-03 18:30:00",
  "status": "BLOCKED"
}
```

#### Response:
```json
{
  "id": 1,
  "section": 1,
  "section_name": "New Delhi - Mathura",
  "start_time": "2026-09-03 17:30:00",
  "end_time": "2026-09-03 18:30:00",
  "status": "BLOCKED"
}
```

---

### 6.7 Check Conflict (`/railways/blocks/check-conflict/`)

Checks if any train movements overlap with a proposed maintenance time window on a section.

#### Request:
`POST /railways/blocks/check-conflict/`

```json
{
  "section": 1,
  "maintenance_start": "2026-09-03 17:30:00",
  "maintenance_end": "2026-09-03 18:30:00"
}
```

#### Response (Conflict Found):
```json
{
  "has_conflict": true,
  "conflict_count": 1,
  "conflicts": [
    {
      "train_number": "22222",
      "train_name": "CSMT Rajdhani",
      "entry_time": "2026-09-03 17:40:00",
      "exit_time": "2026-09-03 18:10:00"
    }
  ]
}
```

#### Response (No Conflict):
```json
{
  "has_conflict": false,
  "conflict_count": 0,
  "conflicts": []
}
```

---

### 6.8 Feasible Windows (`/railways/blocks/feasible-windows/`)

Finds all feasible sub-windows inside an existing block window where a maintenance task can fit without interfering with train traffic.

#### Request:
`POST /railways/blocks/feasible-windows/`

```json
{
  "task_id": "TMS-001",
  "block_id": 1
}
```

#### Response:
```json
{
  "task_id": "TMS-001",
  "block_id": 1,
  "section": "New Delhi - Mathura",
  "required_duration_minutes": 10,
  "feasible": true,
  "windows": [
    {
      "start": "2026-09-03 17:30:00",
      "end": "2026-09-03 17:40:00",
      "duration_minutes": 10
    },
    {
      "start": "2026-09-03 18:10:00",
      "end": "2026-09-03 18:30:00",
      "duration_minutes": 20
    }
  ]
}
```

---

## 7. Running Locally

1. **Activate Virtual Environment & Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up `.env`**:
   ```env
   DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
   DEBUG=True
   ```

3. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```
   Access at: `http://127.0.0.1:8000/railways/`

---

## 8. Deployment (Render / Railway / Docker)

### Environment Variables for Production
- `DATABASE_URL`: Your PostgreSQL database URL
- `SECRET_KEY`: A secure random secret key
- `DEBUG`: `False`
- `ALLOWED_HOSTS`: `*` (or your domain)
- `CORS_ALLOW_ALL_ORIGINS`: `True`
- `CSRF_TRUSTED_ORIGINS`: `https://your-service.onrender.com,http://localhost:3000`

### Build Command
```bash
./build.sh
```

### Start Command
```bash
gunicorn config.wsgi:application
```
