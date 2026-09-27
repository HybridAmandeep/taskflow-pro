# REST API Documentation — TaskFlow Pro

TaskFlow Pro exposes a comprehensive, RESTful JSON API powered by FastAPI.
When running locally, interactive documentation is accessible at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Base URL

| Environment | Base URL |
|:---|:---|
| **Local** | `http://localhost:8000/api` |
| **Production** | `https://your-domain.com/api` |

---

## 1. Tasks API (`/api/tasks`)

### 1.1 List All Tasks
Fetch all tasks on the board along with their computed readiness status.

* **Method:** `GET`
* **Path:** `/api/tasks`
* **Response:** `200 OK` (Array of Task objects)

#### Response Example:
```json
[
  {
    "id": "task-001",
    "title": "Define Product Requirements",
    "description": "Gather core requirements and success criteria",
    "column": "done",
    "sort_order": 0,
    "duration_days": 3,
    "start_date": "2026-10-01",
    "end_date": "2026-10-04",
    "status": "ready",
    "blocked_by": [],
    "created_at": "2026-09-25T10:00:00Z",
    "updated_at": "2026-09-25T10:00:00Z"
  }
]
```

### 1.2 Create Task
Create a new task on the Kanban board.

* **Method:** `POST`
* **Path:** `/api/tasks`
* **Body:**
```json
{
  "title": "Implement Payment Webhooks",
  "description": "Stripe webhook listener for subscription renewal",
  "column": "backlog",
  "duration_days": 2,
  "start_date": "2026-10-10",
  "end_date": "2026-10-12"
}
```
* **Response:** `201 Created`

### 1.3 Get Single Task
* **Method:** `GET`
* **Path:** `/api/tasks/{task_id}`
* **Response:** `200 OK` or `404 Not Found`

### 1.4 Update Task Details
* **Method:** `PUT`
* **Path:** `/api/tasks/{task_id}`
* **Body:**
```json
{
  "title": "Updated Task Title",
  "description": "Updated description",
  "duration_days": 4,
  "start_date": "2026-10-10",
  "end_date": "2026-10-14"
}
```

### 1.5 Move Task (Kanban Column / Reorder)
Move a task across columns or change its position within a column. Automatically triggers status re-evaluation for downstream dependencies (e.g. regression rollback).

* **Method:** `PATCH`
* **Path:** `/api/tasks/{task_id}/move`
* **Body:**
```json
{
  "column": "in_progress",
  "sort_order": 0
}
```
* **Allowed Columns:** `"backlog"`, `"in_progress"`, `"review"`, `"done"`

### 1.6 Delete Task
Deletes a task and removes any associated dependency edges.
* **Method:** `DELETE`
* **Path:** `/api/tasks/{task_id}`
* **Response:** `200 OK` (`{"message": "Task deleted successfully"}`)

---

## 2. Dependencies API (`/api/dependencies`)

### 2.1 List Dependencies
Get all dependency edges currently registered in the DAG.

* **Method:** `GET`
* **Path:** `/api/dependencies`
* **Response Example:**
```json
[
  {
    "id": "dep-001",
    "upstream_task_id": "task-001",
    "downstream_task_id": "task-002",
    "source": "manual",
    "created_at": "2026-09-25T10:00:00Z"
  }
]
```

### 2.2 Add Dependency (With Cycle Detection)
Creates a directed dependency edge: `upstream_task_id` must finish before `downstream_task_id` can start.

* **Method:** `POST`
* **Path:** `/api/dependencies`
* **Body:**
```json
{
  "upstream_task_id": "task-002",
  "downstream_task_id": "task-004",
  "source": "manual"
}
```

#### Cycle Protection (Kahn's Algorithm):
If the edge introduces a circular dependency (e.g., A → B → C → A), the request is rejected with `409 Conflict`.
```json
{
  "detail": "Adding this dependency would create a circular relationship: task-001 -> task-002 -> task-004 -> task-001. The dependency was rejected and the graph remains unchanged."
}
```

### 2.3 Remove Dependency
* **Method:** `DELETE`
* **Path:** `/api/dependencies/{dependency_id}`
* **Response:** `200 OK`

---

## 3. DAG Engine & Scheduling Analysis (`/api/dag`)

### 3.1 Get Critical Path
Identifies the longest path in the workflow using dynamic programming over topological order.

* **Method:** `GET`
* **Path:** `/api/dag/critical-path`
* **Response:**
```json
{
  "path": ["task-001", "task-002", "task-004", "task-007", "task-009", "task-010"],
  "total_duration": 18,
  "task_titles": [
    "Define Product Requirements",
    "Design Database Schema",
    "Implement User Auth API",
    "Integrate Auth with Frontend",
    "Perform Security Audit",
    "Deploy to Production"
  ]
}
```

### 3.2 Get Health Dashboard Metrics
Returns real-time health indicators of the project graph.

* **Method:** `GET`
* **Path:** `/api/dag/health`
* **Response:**
```json
{
  "total_tasks": 10,
  "completed_tasks": 2,
  "blocked_count": 4,
  "ready_count": 2,
  "in_progress_count": 2,
  "critical_path_length": 6,
  "bottlenecks": [
    {
      "task_id": "task-002",
      "task_title": "Design Database Schema",
      "downstream_count": 2
    }
  ]
}
```

### 3.3 What-If Scenario Simulator
Simulate how delaying or shifting an upstream task cascades downstream through the DAG, with zero diamond compounding.

* **Method:** `POST`
* **Path:** `/api/dag/what-if`
* **Body:**
```json
{
  "task_id": "task-004",
  "new_end_date": "2026-10-18"
}
```
* **Response:** Array of downstream tasks and their propagated shifts in calendar days:
```json
[
  {
    "task_id": "task-007",
    "task_title": "Integrate Auth with Frontend",
    "shift_days": 3,
    "current_end": "2026-10-21",
    "projected_end": "2026-10-24"
  },
  {
    "task_id": "task-009",
    "task_title": "Perform Security Audit",
    "shift_days": 3,
    "current_end": "2026-10-25",
    "projected_end": "2026-10-28"
  }
]
```

---

## 4. AI Dependency Suggestions (`/api/ai`)

### 4.1 Suggest Dependencies
Uses NVIDIA NIM to analyze project tasks and suggest logical prerequisites.

* **Method:** `POST`
* **Path:** `/api/ai/suggest-dependencies`
* **Body:**
```json
{
  "task_id": "task-008"
}
```

* **Response Example:**
```json
{
  "suggestions": [
    {
      "upstream_task_id": "task-004",
      "upstream_task_title": "Implement User Auth API",
      "confidence": 90,
      "reasoning": "Auth API endpoints must be implemented before integration tests can test them."
    },
    {
      "upstream_task_id": "task-005",
      "upstream_task_title": "Build REST API Endpoints",
      "confidence": 85,
      "reasoning": "Integration tests require the REST API endpoints to be in place."
    }
  ],
  "model_used": "deepseek-ai/deepseek-r1",
  "prompt_summary": "Analyzed 9 existing tasks to find prerequisites for 'Write Integration Tests'."
}
```

---

## 5. HTTP Status Codes & Error Formats

All API errors return standard FastAPI JSON payloads:
```json
{
  "detail": "Error description here"
}
```

| HTTP Status Code | Scenario |
|:---|:---|
| `200 OK` | Successful retrieval or update |
| `201 Created` | Successful creation of a task or dependency |
| `400 Bad Request` | Invalid input or dates |
| `404 Not Found` | Specified Task or Dependency ID does not exist |
| `409 Conflict` | Circular dependency detected via Kahn's topological sort |
| `500 Internal Error` | Unhandled server error |
