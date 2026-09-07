# Frontend Integration Guide: Maintenance & Block Windows Workflow

This document details the backend architectural changes, API contracts, and frontend integration patterns for the Maintenance and Block Window management system.

---

## 1. High-Level Architecture & Workflow

### Status Lifecycle
1. **Creation**: When a maintenance task is created without a block window, its status is **`PENDING`** (displayed on the UI as **`Block Window Needed`**).
2. **Block Allocation**:
   - A block window is created or assigned to the task (via manual form or AI recommendation).
   - The backend automatically transitions the maintenance task to **`SCHEDULED`**.
3. **AI Recommendation & Optimization**:
   - During or after creation, the unified recommendation endpoint provides non-conflicting time slots evaluated with Google OR-Tools CP-SAT solver.
   - When the user selects an AI-recommended slot, it updates the block window and keeps the task in sync.
4. **Cascade Deletion**:
   - Deleting a maintenance task automatically deletes the associated block window from the database (`CASCADE`), preventing orphaned slots.

---

## 2. API Endpoints Reference

### Base URL
- **Local**: `http://127.0.0.1:8000`
- **Render Production**: `https://backend-oz3h.onrender.com`

---

### A. Unified AI Recommendation Endpoint
**Replaces the 3 deprecated endpoints** (`/feasible-windows/`, `/{id}/recommendation/`, `/{id}/apply-recommendation/`).

- **Endpoint**: `POST /railways/block-windows/recommendation/` *(or `GET` with query params)*

#### Use Case 1: Pre-creation Feasible Slot Discovery
Search for available time windows on a given date before creating a block window:
```json
// POST /railways/block-windows/recommendation/
{
  "task_id": "TMS-190",
  "date": "2026-09-08"
}
```
**Response**:
```json
{
  "task_id": "TMS-190",
  "date": "2026-09-08",
  "feasible": true,
  "windows": [
    {
      "start_time": "2026-09-08 02:00:00",
      "end_time": "2026-09-08 04:00:00",
      "duration_minutes": 120,
      "conflicts_count": 0,
      "score": 95.0
    }
  ]
}
```

#### Use Case 2: Post-creation Conflict Check & AI Improvement
Check if an existing block window has train conflicts and get optimal AI alternatives:
```json
// POST /railways/block-windows/recommendation/
{
  "block_window_id": 15,
  "task_id": "TMS-190"
}
```
**Response**:
```json
{
  "block_window_id": 15,
  "task_id": "TMS-190",
  "current_slot": {
    "start_time": "2026-09-08 09:00:00",
    "end_time": "2026-09-08 11:00:00",
    "conflicts_count": 2,
    "conflicts": ["Train 12004", "Train 12002"]
  },
  "has_better_slot": true,
  "recommendation_reason": "Slot 02:00 - 04:00 has 0 train conflicts compared to 2 current conflicts.",
  "recommended_slot": {
    "start_time": "2026-09-08 02:00:00",
    "end_time": "2026-09-08 04:00:00",
    "conflicts_count": 0
  }
}
```

#### Use Case 3: 1-Click Accept / Apply Recommendation
Accept the recommended AI slot to immediately update the block window in the database:
```json
// POST /railways/block-windows/recommendation/
{
  "block_window_id": 15,
  "task_id": "TMS-190",
  "apply": true
}
```
**Response**:
```json
{
  "applied": true,
  "message": "Block window updated to AI recommended slot.",
  "block_window": {
    "id": 15,
    "section": 1,
    "task": 12,
    "task_id": "TMS-190",
    "task_code": "TMS-190",
    "start_time": "2026-09-08 02:00:00",
    "end_time": "2026-09-08 04:00:00",
    "status": "RESERVED"
  }
}
```

---

### B. Block Window Operations by Task ID (`task_id`)
Instead of tracking internal primary keys (`id`), the frontend can interact directly using the maintenance task code (e.g. `TMS-190`).

#### 1. Retrieve Block Window for a Task
- **Endpoint**: `GET /railways/block-windows/by-task/{task_id}/`
- **Example**: `GET /railways/block-windows/by-task/TMS-190/`
- **Response** (`200 OK` or `404 Not Found`):
```json
{
  "id": 15,
  "section": 1,
  "section_name": "NDLS - GZB",
  "task": 12,
  "task_id": "TMS-190",
  "task_code": "TMS-190",
  "task_details": "Overhead traction line inspection",
  "task_asset_name": "OHE Section 4",
  "start_time": "2026-09-08 02:00:00",
  "end_time": "2026-09-08 04:00:00",
  "status": "RESERVED"
}
```

#### 2. Update (PUT / PATCH) Block Window by Task ID
Updates the existing block window linked to the task. If no block window existed yet for this task, `PUT` creates one automatically.
- **Endpoint**: `PUT /railways/block-windows/by-task/{task_id}/` (or `PATCH`)
- **Example**: `PUT /railways/block-windows/by-task/TMS-190/`
- **Payload**:
```json
{
  "start_time": "2026-09-08 03:00:00",
  "end_time": "2026-09-08 05:00:00",
  "status": "RESERVED"
}
```
*(Note: `section` is optional; if omitted, it defaults to the task's asset section).*

#### 3. Delete Block Window by Task ID
- **Endpoint**: `DELETE /railways/block-windows/by-task/{task_id}/`
- **Response**: `204 No Content`

---

### C. Standard Block Window CRUD with Task Linking
When creating or updating a block window via standard endpoints, you can pass either `task` (integer PK) or `task_id` (string identifier):

#### Create Block Window:
- **Endpoint**: `POST /railways/block-windows/`
```json
{
  "section": 1,
  "task_id": "TMS-190",
  "start_time": "2026-09-08 02:00:00",
  "end_time": "2026-09-08 04:00:00",
  "status": "RESERVED"
}
```

#### Filter Block Windows List:
- `GET /railways/block-windows/?task_id=TMS-190`
- `GET /railways/block-windows/?task=12`

---

### D. Maintenance Tasks Embed Block Window
When fetching maintenance tasks (`GET /railways/maintenance-tasks/`), each task object includes its linked block window:
```json
{
  "id": 12,
  "task_id": "TMS-190",
  "task_code": "TMS-190",
  "status": "SCHEDULED",
  "block_window": {
    "id": 15,
    "section": 1,
    "start_time": "2026-09-08 02:00:00",
    "end_time": "2026-09-08 04:00:00",
    "status": "RESERVED"
  }
}
```

---

## 3. TypeScript Interfaces

Update or reference these types in `@/types/blocks.ts` and `@/types/maintenance.ts`:

```typescript
// Block Window
export interface BlockWindow {
  id: number;
  section: number;
  section_name?: string;
  task?: number | null;
  task_id?: string | null;
  task_code?: string | null;
  task_details?: string | null;
  task_asset_name?: string | null;
  start_time: string;
  end_time: string;
  status: "AVAILABLE" | "RESERVED" | "BLOCKED";
}

// Payload for creating/updating
export interface CreateBlockWindowInput {
  section: number;
  task?: number | null;
  task_id?: string | null;
  start_time: string;
  end_time: string;
  status?: "AVAILABLE" | "RESERVED" | "BLOCKED";
}

// Embedded Block Window on MaintenanceTask
export interface EmbeddedBlockWindow {
  id: number;
  section: number;
  start_time: string;
  end_time: string;
  status: string;
}

// Maintenance Task with embedded block window
export interface MaintenanceTask {
  id: number;
  task_id: string;
  task_code: string;
  status: "PENDING" | "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED" | "DELAYED";
  block_window?: EmbeddedBlockWindow | null;
  // ... other task fields
}
```

---

## 4. Frontend Action Helpers (`src/actions/blocks.ts`)

Available helper functions ready to import:

```typescript
import {
  getBlockWindowByTaskId,
  updateBlockWindowByTaskId,
  getBlockWindowsRecommendation,
} from "@/actions/blocks";

// 1. Fetch block window by task_id
const { data: bw } = await getBlockWindowByTaskId("TMS-190");

// 2. Update block window by task_id
await updateBlockWindowByTaskId("TMS-190", {
  start_time: "2026-09-08 03:00:00",
  end_time: "2026-09-08 05:00:00",
  status: "RESERVED",
});

// 3. 1-Click apply recommendation
await getBlockWindowsRecommendation({
  block_window_id: bw.id,
  task_id: "TMS-190",
  apply: true,
});
```

---

## 5. React Query Cache Invalidation Guidelines

When performing mutations, invalidate both `["maintenance-tasks"]` and `["blocks"]` so the UI stays completely synchronized:

```typescript
// On deleting a maintenance task:
queryClient.invalidateQueries({ queryKey: ["maintenance-tasks"] });
queryClient.invalidateQueries({ queryKey: ["blocks"] });

// On creating/updating a block window:
queryClient.invalidateQueries({ queryKey: ["blocks"] });
queryClient.invalidateQueries({ queryKey: ["maintenance-tasks"] });
```

---

## 6. Bruno API Requests

All requests are pre-configured in `backend/bruno/07-Block-Windows/`:
- `AI Block Window Recommendation.bru` — Unified recommendation endpoint (Discovery, Evaluation, and 1-Click Apply).
- `Get Block Window by Task ID.bru` — `GET /railways/block-windows/by-task/TMS-190/`.
- `Update Block Window by Task ID.bru` — `PUT /railways/block-windows/by-task/TMS-190/`.
- `List Block Windows.bru` — List with optional `?task_id=TMS-190` filter.
- `Get Block Window by ID.bru` — `GET /railways/block-windows/{id}/`.
