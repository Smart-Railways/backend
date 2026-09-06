# Backend Enums & Choices Reference

This document provides a comprehensive reference of all Enumerations (`models.TextChoices`) and categorical choices used throughout the backend API, models, and background services.

---

## 📋 Quick Index

1. [Asset Department (`Asset.Department`)](#1-asset-department)
2. [Maintenance Task Urgency / Priority (`MaintenanceTask.Priority`)](#2-maintenance-task-urgency--priority)
3. [Maintenance Task Status (`MaintenanceTask.Status`)](#3-maintenance-task-status)
4. [Block Window Status (`BlockWindow.Status`)](#4-block-window-status)
5. [Maintenance Plan Status (`MaintenancePlan.Status`)](#5-maintenance-plan-status)
6. [Train Type (`Train.TrainType`)](#6-train-type)
7. [Schedule Running Days Pattern](#7-schedule-running-days-pattern)

---

## 1. Asset Department

- **Model**: `apps.assets.models.Asset`
- **Field**: `department` (API alias / field name: `division` or `department`)
- **Type**: `models.TextChoices`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `ENGINEERING` | Engineering | Track, rails, sleepers, ballast, civil structures, bridges |
| `SNT` | Signal & Telecom | Signaling equipment, interlocking, points, telecommunications |
| `TRACTION` | Traction | Overhead Electrification (OHE), power supply, sub-stations, mast poles |

### Example Payload
```json
{
  "asset_title": "OHE Tension Wire Mast #104",
  "category": "OHE",
  "division": "TRACTION",
  "risk_level": 4,
  "section": 1
}
```

---

## 2. Maintenance Task Urgency / Priority

- **Model**: `apps.maintenance.models.MaintenanceTask`
- **Field**: `priority` (API alias: `urgency`)
- **Type**: `models.TextChoices`

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

## 3. Maintenance Task Status

- **Model**: `apps.maintenance.models.MaintenanceTask`
- **Field**: `status` (API alias: `task_status`)
- **Type**: `models.TextChoices`
- **Default**: `PENDING`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `PENDING` | Pending | Task is created, awaiting scheduling and block allocation |
| `SCHEDULED` | Scheduled | Block window or maintenance plan has been allocated / approved |
| `COMPLETED` | Completed | Maintenance work has finished successfully |
| `CANCELLED` | Cancelled | Task has been dismissed or superseded |

---

## 4. Block Window Status

- **Model**: `apps.blocks.models.BlockWindow`
- **Field**: `status`
- **Type**: `models.TextChoices`
- **Default**: `AVAILABLE`

| Key / Value (Database & API) | Display Label | Description |
| :--- | :--- | :--- |
| `AVAILABLE` | Available | The section window is open and available for maintenance scheduling |
| `RESERVED` | Reserved | The block window has been provisionally reserved for planning/approval |
| `BLOCKED` | Blocked | Corridor is blocked / occupied; maintenance execution in effect |

### Example Payload
```json
{
  "section": 1,
  "start_time": "2026-09-06 01:00:00",
  "end_time": "2026-09-06 04:00:00",
  "status": "AVAILABLE"
}
```

---

## 5. Maintenance Plan Status

- **Model**: `apps.planning.models.MaintenancePlan`
- **Field**: `status`
- **Type**: `models.TextChoices`
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

### Example Payload
```json
{
  "plan_id": "PLAN-20260906-001",
  "title": "Track Maintenance Block - Delhi to Agra",
  "section": 1,
  "task": 1,
  "block_window": 1,
  "planned_start_time": "2026-09-06 01:30:00",
  "planned_end_time": "2026-09-06 03:30:00",
  "status": "PENDING_APPROVAL"
}
```

---

## 6. Train Type

- **Model**: `apps.trains.models.Train`
- **Field**: `train_type`
- **Type**: `models.TextChoices`

| Key / Value (Database & API) | Display Label | Default Train Priority (1-10) | Description |
| :--- | :--- | :--- | :--- |
| `VB` | Vande Bharat | 10 | Semi-high speed premium Vande Bharat train sets |
| `SHATABDI` | Shatabdi | 10 | Superfast day express (Shatabdi, Jan Shatabdi) |
| `RAJDHANI` | Rajdhani | 10 | High-priority long-distance express connecting national capital |
| `EXPRESS` | Express | 6 - 9 | Premium & standard express services (Duronto, Humsafar, Superfast, Mail) |
| `PASSENGER` | Passenger | 5 | Ordinary passenger and local shuttle services |
| `FREIGHT` | Freight | 5 | Goods, container, and freight rake movements |

---

## 7. Schedule Running Days Pattern

- **Model**: `apps.trains.models.TrainSchedule`
- **Field**: `running_days`
- **Type**: 7-character binary string regex `^[01]{7}$` representing **Monday to Sunday**

| Pattern (`running_days`) | Description | Active Days |
| :--- | :--- | :--- |
| `1111111` | Daily service (Runs every day) | Mon, Tue, Wed, Thu, Fri, Sat, Sun |
| `1111100` | Weekday service | Mon, Tue, Wed, Thu, Fri |
| `0000011` | Weekend service | Sat, Sun |
| `1000000` | Weekly service (Mondays only) | Mon |
| `0000100` | Weekly service (Fridays only) | Fri |
