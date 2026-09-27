# TaskFlow Pro — Dependency-Aware Workflow & DAG Scheduling Engine

A production-grade Kanban board powered by a **DAG (Directed Acyclic Graph)** scheduling engine, featuring AI-augmented dependency suggestions, critical path visualization, and a "What-If" scenario simulator.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

| Feature | Description |
|---------|-------------|
| **Kanban Board** | 4-column drag-and-drop board (Backlog, In Progress, Review, Done) |
| **DAG Engine** | Cycle detection, schedule propagation, blocked/ready status computation |
| **No Compounding** | Diamond dependencies propagate correctly (A->B->D + A->C->D = +3 not +6) |
| **Rollback Cascading** | Moving a Done task back re-evaluates all downstream statuses |
| **AI Suggestions** | NVIDIA NIM-powered dependency suggestions with confidence scores |
| **Critical Path** | Longest dependency chain visualization |
| **What-If Simulator** | Preview schedule cascade before committing changes |
| **Health Dashboard** | Live metrics: blocked count, critical path, bottleneck detection |
| **Persistence** | SQLite database — state survives browser refresh |

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, SQLite
- **Frontend:** Vanilla HTML/CSS/JS (served by FastAPI)
- **AI:** NVIDIA NIM API (DeepSeek R1 via OpenAI-compatible endpoint)
- **Styling:** Custom design system with Dark & Light modes (solid corporate colors)

---

## Documentation

- 🚀 **[Deployment Guide](docs/DEPLOYMENT.md)** — Step-by-step instructions to take this app online (Render, Railway, Docker, Cloudflare).
- 📡 **[REST API Documentation](docs/API_DOCUMENTATION.md)** — Complete endpoint references, request/response payloads, and DAG algorithms.
- 🤖 **[NVIDIA NIM AI Setup Guide](docs/NVIDIA_NIM_SETUP.md)** — Guide to getting an API key and configuring AI suggestions.

---

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/taskflow-pro.git
cd taskflow-pro/backend

# Install dependencies
pip install -r requirements.txt

# (Optional) Add your NVIDIA NIM API key for AI features
# Edit .env and set NVIDIA_API_KEY=nvapi-your-key-here

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

The database is created automatically on first run with 10 seeded tasks and 13 dependencies.

### Running Tests

```bash
cd backend
python app/tests/test_dag_engine.py
```

---

## Seed Data

10 realistic tasks modeling a software project lifecycle:

```
1. Define Product Requirements (Done)
2. Design Database Schema (Done)        -> depends on 1
3. Set Up CI/CD Pipeline (In Progress)  -> depends on 1
4. Implement User Auth API (In Progress)-> depends on 2
5. Build REST API Endpoints (In Prog.)  -> depends on 2
6. Create Frontend Component Library (Review) -> depends on 1
7. Integrate Auth with Frontend (Backlog) -> depends on 4, 6  (diamond)
8. Write Integration Tests (Backlog)    -> depends on 4, 5
9. Perform Security Audit (Backlog)     -> depends on 7, 8  (diamond)
10. Deploy to Production (Backlog)      -> depends on 3, 9  (convergence)
```

This data demonstrates:
- Diamond dependencies (tasks 7 and 9)
- Multiple convergence points (task 10)
- Various chain depths for critical path testing

---

## AI / LLM Integration

### Model
NVIDIA NIM (DeepSeek R1) via the OpenAI-compatible API at `integrate.api.nvidia.com/v1`.

### How It Works
1. User clicks "AI Suggest Dependencies" in the task edit modal
2. System sends all existing tasks + target task to NVIDIA NIM with a structured prompt
3. The model returns suggested prerequisites with confidence scores (0-100) and reasoning
4. User reviews and explicitly accepts or rejects each suggestion
5. Accepted suggestions pass through cycle detection before persistence

### Hallucination Prevention
- **Context grounding:** Only existing task IDs are valid — LLM cannot invent tasks
- **Server-side validation:** All suggested IDs are checked against the database
- **Cycle detection:** Accepted suggestions are validated by the DAG engine
- **Confidence threshold:** Only suggestions >= 40% confidence are shown
- **Structured output:** JSON schema enforced to prevent free-text hallucination
- **Human-in-the-loop:** ALL suggestions require explicit user approval

### Without API Key
The app works fully without an NVIDIA API key. AI features gracefully show "No API key configured" — all other features remain functional.

---

## Key Algorithms

### Cycle Detection — Kahn's Algorithm
- Before adding any edge, temporarily insert it and run topological sort via in-degree counting
- If unvisited nodes remain after the sort, a cycle exists -> reject with clear error
- O(V + E) time complexity

### Schedule Propagation — BFS with No Compounding
- When an upstream task shifts by N days, BFS walks all downstream nodes
- `max_shift` map tracks the maximum shift arriving at each node from any path
- Each node shifts by `max(delta from all incoming paths)`, not the sum
- Prevents the diamond compounding bug (A->B->D + A->C->D = +N, not +2N)

### Blocked/Ready Status
- Computed at query time, never stored
- A task is READY if all upstream dependencies are in DONE column
- A task is BLOCKED if any upstream dependency is not DONE
- Re-evaluated on every state change

### Critical Path — Longest Path via DP
- Process nodes in reverse topological order
- `longest_path[node] = duration[node] + max(longest_path[successor])`
- Backtrack to extract the full chain

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List all tasks with computed status |
| POST | `/api/tasks` | Create a new task |
| PUT | `/api/tasks/{id}` | Update task details |
| PATCH | `/api/tasks/{id}/move` | Move task to different column |
| DELETE | `/api/tasks/{id}` | Delete task and dependencies |
| GET | `/api/dependencies` | List all dependency edges |
| POST | `/api/dependencies` | Add dependency (cycle-checked) |
| DELETE | `/api/dependencies/{id}` | Remove dependency |
| GET | `/api/dag/critical-path` | Get critical path |
| GET | `/api/dag/health` | Health dashboard metrics |
| POST | `/api/dag/what-if` | Simulate date change preview |
| POST | `/api/ai/suggest-dependencies` | AI-powered suggestions |

Full interactive docs available at `/docs` (Swagger UI).

---

## Key Assumptions and Limitations

### Assumptions
- **Single-user / small-team:** No real-time multi-user sync via WebSockets. Designed for individual or small team use where concurrent writes are rare.
- **Calendar days:** All scheduling uses calendar days. No business day or holiday awareness.
- **Task scale:** Optimized for 10-200 tasks per board. SQLite handles this without performance issues.
- **Sequential execution:** Critical path assumes tasks execute sequentially along dependency chains. No parallelism modeling within a single chain.
- **AI is advisory only:** AI suggestions never auto-apply. Human approval and DAG validation are mandatory.

### Limitations
- **No authentication:** The app runs in demo mode without user login. All users share the same board.
- **No WebSocket real-time sync:** Changes by one user aren't pushed to others in real-time. Manual refresh shows the latest state.
- **AI requires internet:** The NVIDIA NIM API call needs internet access. Without a valid API key, AI features degrade gracefully.
- **No undo/redo in v1:** DAG snapshot table exists in the schema but undo/redo UI is not implemented in this sprint.
- **No timezone awareness:** All dates are naive (no timezone information).
- **Canvas DAG view:** The DAG visualization uses a simple canvas renderer. For very large graphs (200+ nodes), a force-directed layout library like React Flow would be better.

---

## Project Structure

```
taskflow-pro/
  backend/
    app/
      main.py             # FastAPI entry point
      config.py            # Settings & env vars
      database.py          # Async SQLAlchemy setup
      models.py            # SQLAlchemy models (Task, Dependency, DAGSnapshot)
      schemas.py           # Pydantic request/response schemas
      dag_engine.py        # Core DAG algorithms (pure Python, no DB deps)
      dag_helpers.py       # DB-to-DAGEngine bridge
      ai_service.py        # NVIDIA NIM integration
      seed.py              # 10 seeded tasks + 13 dependencies
      routes/
        tasks.py           # Task CRUD + movement
        dependencies.py    # Dependency CRUD + DAG analysis
        ai.py              # AI suggestion endpoint
      tests/
        test_dag_engine.py # 17 unit tests
    static/
      index.html           # Main HTML page
      css/styles.css        # Dark theme + glassmorphism
      js/
        api.js              # Fetch-based API client
        dag-canvas.js       # Canvas-based DAG renderer
        app.js              # Main app logic + interactions
    .env                    # Environment variables
    requirements.txt        # Python dependencies
  README.md                 # This file
```

---

## License

MIT
