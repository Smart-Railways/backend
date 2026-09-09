# Backend & Frontend Enums & Choices Reference

This document provides a comprehensive, unified reference of all Enumerations (`models.TextChoices`, TypeScript `enum`), categorical choices, status lifecycles, and API field mappings used across the backend and frontend.

---

## 📋 Quick Index

1. [Asset Department (`Asset.Department` / `AssetDepartment`)](#1-asset-department)
2. [Asset Categories (`AssetCategory`)](#2-asset-categories)
3. [Maintenance Task Urgency / Priority (`MaintenanceTask.Priority` / `MaintenancePriority`)](#3-maintenance-task-urgency--priority)
4. [Maintenance Task Status (`MaintenanceTask.Status` / `MaintenanceStatus`)](#4-maintenance-task-status)
5. [Block Window Status (`BlockWindow.Status` / `BlockStatus`)](#5-block-window-status)
6. [AI Optimization Algorithms (`algorithm`)](#6-ai-optimization-algorithms)
7. [Maintenance Plan Status (`MaintenancePlan.Status` / `MaintenancePlanStatus`)](#7-maintenance-plan-status)
8. [Train Type (`Train.TrainType` / `TrainType`)](#8-train-type)
9. [Schedule Running Days Pattern (`RunningDaysPattern`)](#9-schedule-running-days-pattern)
10. [API Field Mappings & Serialization Aliases](#10-api-field-mappings--serialization-aliases)

---

## 1. Asset Department

- **Backend Model**: `apps.assets.models.Asset`
- **Field**: `department` (API alias / field name: `division` or `department`)
- **Type**: `models.TextChoices` / TypeScript `AssetDepartment`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `ENGINEERING` | Engineering | Track, rails, sleepers, ballast, civil structures, bridges |
| `SNT` | Signal & Telecom | Signaling equipment, interlocking, points, telecommunications |
| `TRACTION` | Traction | Overhead Electrification (OHE), power supply, sub-stations, mast poles |

### Example Payload
```json
{
  "asset_title": "OHE Tension Wire Mast #104",
  "category": "OVERHEAD_EQUIPMENT",
  "division": "TRACTION",
  "risk_level": 4,
  "section": 1
}
```

---

## 2. Asset Categories

- **Backend Model**: `apps.assets.models.Asset`
- **Field**: `asset_type` (API alias: `category`)
- **Frontend Enum**: `AssetCategory`

| Key / Value | Display Label | Primary Department | Typical Maintenance Window |
| :--- | :--- | :--- | :--- |
| `TRACK_CIRCUIT` | Track Circuit | `SNT` | 30 - 60 mins |
| `SIGNAL` | Signal & Interlocking | `SNT` | 45 - 90 mins |
| `POINT_MACHINE` | Point Machine / Switch | `SNT` | 45 - 60 mins |
| `OVERHEAD_EQUIPMENT` | OHE / Traction Catenary | `TRACTION` | 60 - 180 mins |
| `TRANSFORMER` | Traction Substation Transformer | `TRACTION` | 90 - 240 mins |
| `TRACK_SEGMENT` | Track Segment / Rail | `ENGINEERING` | 60 - 180 mins |
| `AXLE_COUNTER` | Axle Counter | `SNT` | 30 - 45 mins |
| `INTERLOCKING` | Electronic Interlocking | `SNT` | 60 - 120 mins |
| `OTHER` | Other Asset | `ENGINEERING` / `SNT` / `TRACTION` | Variable |

---

## 3. Maintenance Task Urgency / Priority

- **Backend Model**: `apps.maintenance.models.MaintenanceTask`
- **Field**: `priority` (API alias: `urgency`)
- **Type**: `models.TextChoices` / TypeScript `MaintenancePriority`

| Key / Value (Database & API) | Display Label | Default Weight in Planning | Description |
| :--- | :--- | :--- | :--- |
| `CRITICAL` | Critical | 40.0 | Severe safety risk or immediate operational hazard; highest priority |
| `HIGH` | High | 30.0 | Significant wear or disruption risk; requires near-term maintenance |
| `MEDIUM` | Medium | 20.0 | Standard routine inspection, preventive repair, or periodic check |
| `LOW` | Low | 10.0 | Minor maintenance or aesthetic/non-critical work |

### Example Payload
```json
{
  "task_code": "TASK-OHE-201",
  "asset": 1,
  "details": "Routine OHE tension wire check",
  "risk_rating": 4,
  "urgency": "HIGH",
  "deadline": "2026-09-12",
  "estimated_duration": 90,
  "task_status": "PENDING"
}
```

---

## 4. Maintenance Task Status

- **Backend Model**: `apps.maintenance.models.MaintenanceTask`
- **Field**: `status` (API alias: `task_status`)
- **Type**: `models.TextChoices` / TypeScript `MaintenanceStatus`
- **Default**: `PENDING`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `PENDING` | Block Window Needed / Pending | Task is created, awaiting block window allocation |
| `SCHEDULED` | Scheduled | Block window has been reserved and linked to the task |
| `DELAYED` | Delayed | Deadline (`due_date`) has passed without completion (`is_overdue = true`) |
| `COMPLETED` | Completed | Maintenance work has finished successfully |
| `CANCELLED` | Cancelled | Task has been dismissed or superseded |

### Automatic Status Lifecycle Rules
1. **Automatic Overdue Detection**:
   When `due_date < today` (in `Asia/Kolkata` time) and the task status is not `COMPLETED` or `CANCELLED`, the system automatically transitions the status to `DELAYED` and sets `is_overdue = true`.
2. **Automatic Scheduling**:
   When a `BlockWindow` is created or assigned to a maintenance task (via standard CRUD, `/by-task/` PUT, or 1-Click AI slot accept), the task status automatically transitions to `SCHEDULED`.

### Serialized Task Response Format
```json
{
  "id": 18,
  "task_code": "TMS-746",
  "asset": 12,
  "asset_name": "Point Machine",
  "section_name": "Mathura-Agra",
  "details": "Switch point calibration",
  "risk_rating": 8,
  "urgency": "CRITICAL",
  "deadline": "2026-09-14",
  "estimated_duration": 45,
  "task_status": "SCHEDULED",
  "block_window": {
    "id": 21,
    "section": 2,
    "section_name": "Mathura-Agra",
    "date": "2026-09-08",
    "start_time": "2026-09-08 00:00:00",
    "end_time": "2026-09-08 01:00:00",
    "duration_minutes": 60,
    "status": "RESERVED"
  },
  "block_window_date": "2026-09-08",
  "is_delayed": false,
  "logged_at": "2026-09-07 17:29:13"
}
```

---

## 5. Block Window Status

- **Backend Model**: `apps.blocks.models.BlockWindow`
- **Field**: `status`
- **Type**: `models.TextChoices` / TypeScript `BlockStatus`
- **Default**: `AVAILABLE`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `AVAILABLE` | Available | The section window is open and available for maintenance scheduling |
| `RESERVED` | Reserved | The corridor block is reserved for a maintenance task |
| `BLOCKED` | Blocked | Corridor is blocked; maintenance execution actively in effect |

### Timezone & Formatting Notice
- **Storage**: Datetimes are stored in UTC in PostgreSQL.
- **Serialization**: Both `apps.maintenance` and `apps.blocks` automatically serialize `start_time` and `end_time` in the Indian Standard Time (`Asia/Kolkata`, UTC+05:30) zone formatted as `YYYY-MM-DD HH:MM:SS`.
- **Direct Task Access**: Block windows can be directly retrieved or updated by task code via `/railways/block-windows/by-task/{task_id}/`.

### Example Payload
```json
{
  "section": 1,
  "task": 18,
  "task_id": "TMS-746",
  "start_time": "2026-09-08 00:00:00",
  "end_time": "2026-09-08 01:00:00",
  "status": "RESERVED"
}
```

---

## 6. AI Optimization Algorithms

- **API Field**: `algorithm` (returned in recommendation payloads)
- **Endpoint**: `POST /railways/block-windows/recommendation/`

| Algorithm Key | Display Name | Optimization Mechanism |
| :--- | :--- | :--- |
| `CP-SAT Constraint Solver` | OR-Tools CP-SAT | Constraint programming solver evaluating task priority, safety buffers, network delay impact, and train headway |
| `Database Timestamp Gap` | Timetable Gap Heuristic | Deterministic fallback finding optimal collision-free intervals between live train movements |

---

## 7. Maintenance Plan Status

- **Backend Model**: `apps.planning.models.MaintenancePlan`
- **Field**: `status`
- **Type**: `models.TextChoices` / TypeScript `MaintenancePlanStatus`
- **Default**: `DRAFT`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `DRAFT` | Draft | Initial proposed plan generated manually or by planning engine |
| `PENDING_APPROVAL` | Pending Approval | Submitted for section controller / engineer review |
| `APPROVED` | Approved | Approved by section controller; marks linked task as `SCHEDULED` |
| `REJECTED` | Rejected | Proposal rejected due to timetable conflicts or operational reasons |
| `IN_PROGRESS` | In Progress | Maintenance activity is actively being executed on site |
| `COMPLETED` | Completed | Maintenance activity completed successfully |
| `CANCELLED` | Cancelled | Plan was retracted or aborted |

### Status Lifecycle Diagram
```text
[DRAFT] ──> [PENDING_APPROVAL] ──> [APPROVED] ──> [IN_PROGRESS] ──> [COMPLETED]
     │               │                 │
     └──> [CANCELLED] └──> [REJECTED]   └──> [CANCELLED]
```

---

## 8. Train Type

- **Backend Model**: `apps.trains.models.Train`
- **Field**: `train_type`
- **Type**: `models.TextChoices` / TypeScript `TrainType`

| Key / Value (Database & API) | Display Label | Default Train Priority (1-10) | Description |
| :--- | :--- | :--- | :--- |
| `VB` | Vande Bharat | 10 | Semi-high speed premium Vande Bharat train sets |
| `SHATABDI` | Shatabdi | 10 | Superfast day express (Shatabdi, Jan Shatabdi) |
| `RAJDHANI` | Rajdhani | 10 | High-priority long-distance express connecting national capital |
| `EXPRESS` | Express | 8 (6 - 9) | Premium & standard express services (Duronto, Humsafar, Superfast, Mail) |
| `PASSENGER` | Passenger | 5 | Ordinary passenger and local shuttle services |
| `FREIGHT` | Freight | 5 | Goods, container, and freight rake movements |

---

## 9. Schedule Running Days Pattern

- **Backend Model**: `apps.trains.models.TrainSchedule`
- **Field**: `running_days`
- **Type**: 7-character binary string regex `^[01]{7}$` representing **Monday to Sunday**

| Pattern (`running_days`) | Enum Constant | Description | Active Days |
| :--- | :--- | :--- | :--- |
| `1111111` | `DAILY` | Daily service (Runs every day) | Mon, Tue, Wed, Thu, Fri, Sat, Sun |
| `1111100` | `WEEKDAY` | Weekday service | Mon, Tue, Wed, Thu, Fri |
| `0000011` | `WEEKEND` | Weekend service | Sat, Sun |
| `1000000` | `MON_ONLY` | Weekly service (Mondays only) | Mon |
| `0000100` | `FRI_ONLY` | Weekly service (Fridays only) | Fri |

---

## 10. API Field Mappings & Serialization Aliases

| Resource | Frontend API Key | Backend Model Field | Notes |
| :--- | :--- | :--- | :--- |
| **Asset** | `asset_title` | `name` | Asset name/title |
| | `category` | `asset_type` | Category choice |
| | `division` | `department` | Engineering / SNT / Traction |
| | `risk_level` | `criticality` | Integer rating (1-10) |
| | `setup_date` | `installation_date` | ISO date string `YYYY-MM-DD` |
| | `section` | `section_id` | Foreign key ID to `RailwaySection` |
| **Task** | `task_code` | `task_id` | Unique string code (e.g. `TMS-746`) |
| | `details` | `description` | Task description |
| | `risk_rating` | `severity` | Severity rating (1-10) |
| | `urgency` | `priority` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| | `deadline` | `due_date` | Due date `YYYY-MM-DD` |
| | `estimated_duration` | `duration_minutes` | Duration in minutes |
| | `task_status` | `status` | `PENDING`, `SCHEDULED`, `DELAYED`, `COMPLETED`, `CANCELLED` |
| | `block_window` | *(computed)* | Nested active block window object |
| | `block_window_date` | *(computed)* | Active window date `YYYY-MM-DD` |
| | `is_delayed` | `is_overdue` | Boolean flag (true if past deadline) |
| **Block Window** | `section` | `section_id` | Section Foreign Key |
| | `task` | `task_id` | Task integer PK or string code |
| | `start_time` | `start_time` | Format `YYYY-MM-DD HH:MM:SS` (IST) |
| | `end_time` | `end_time` | Format `YYYY-MM-DD HH:MM:SS` (IST) |
| | `status` | `status` | `AVAILABLE`, `RESERVED`, `BLOCKED` |
