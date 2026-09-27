# TaskFlow Pro — Dependency-Aware Workflow & DAG Scheduling Engine

TaskFlow Pro is a production-grade Kanban board powered by a **DAG (Directed Acyclic Graph)** scheduling engine, featuring AI-augmented dependency suggestions via **Google Gemini**, critical path visualization, and a "What-If" schedule simulator.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google%20Gemini-gemini--3.8--flash-4285F4?style=flat&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat)

---

## 🌟 Key Features

| Feature | Description |
|:---|:---|
| **Interactive Kanban Board** | 4-column drag-and-drop workflow (Backlog, In Progress, Review, Done) with strict sequential sorting. |
| **Deterministic DAG Engine** | Pure Python topological sorting, cycle detection, and schedule propagation. |
| **No Compounding Bug** | Diamond dependencies correctly calculate $\max(\text{shifts})$ across parallel branches rather than summing delays. |
| **Rollback Cascading** | Moving a Done task backwards dynamically recalculates readiness and marks dependent tasks as blocked. |
| **AI Dependency Suggestions** | Context-grounded recommendations using **Google Gemini** (`gemini-3.8-flash`) with confidence scores and reasoning. |
| **Critical Path Analysis** | Highlights the project bottleneck chain using reverse topological dynamic programming. |
| **What-If Schedule Simulator** | Interactive slider/date preview showing exact downstream ripple effects before committing changes. |
| **Graph Health Dashboard** | Real-time counts of blocked tasks, completed tasks, bottleneck nodes, and critical path metrics. |
| **State Persistence** | Backed by SQLite (`aiosqlite`) — survive browser reloads and server restarts. |

---

## 📚 Documentation Hub

All technical documentation is organized in the [`docs/`](docs/) directory:

- 📖 **[Documentation Hub](docs/README.md)** — Master index and guide to editing documentation.
- 🏗️ **[Architecture & Design](docs/ARCHITECTURE.md)** — In-depth graph algorithms, data models, and system design.
- 📡 **[REST API Reference](docs/API_DOCUMENTATION.md)** — Complete endpoint specs, schemas, payloads, and status codes.
- 🚀 **[Deployment Guide](docs/DEPLOYMENT.md)** — Instructions for Render.com, Docker, Railway, Fly.io, and Cloudflare.
- 🤖 **[Gemini AI Setup Guide](docs/GEMINI_SETUP.md)** — Step-by-step key acquisition, model config, and guardrails.
- 🛡️ **[AI Tool Declaration](AI_TOOL_DECLARATION.md)** — Development and runtime AI usage and safety disclosures.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/HybridAmandeep/taskflow-pro.git
cd taskflow-pro

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example backend/.env
```

To enable AI dependency suggestions, add your free Google AI Studio key in `backend/.env`:
```env
DATABASE_URL=sqlite+aiosqlite:///./taskflow.db
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
```
*(If no API key is provided, the application runs normally with AI suggestions disabled).*

### 3. Start the Server

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **`http://localhost:8000`** in your browser.

The database initializes automatically on first run with 10 realistic software engineering tasks and 13 dependencies modeling diamond paths and convergence points.

---

## 🧪 Running Tests

### Run Unit Tests (DAG Engine)
```bash
cd backend
python -m pytest app/tests/test_dag_engine.py
```
*(All 22 unit tests verify cycle detection, Kahn's algorithm, BFS schedule propagation, critical path DP, and diamond non-compounding).*

---

## 🎯 Realistic Seed Data

The seeded project models a modern software development lifecycle:

```
1. Define Product Requirements (Done)
├── 2. Design Database Schema (Done)
│   ├── 4. Implement User Auth API (In Progress) ──────┐
│   │   ├── 7. Integrate Auth with Frontend (Backlog) ─┼── 9. Security Audit ── 10. Deploy to Prod
│   │   └── 8. Write Integration Tests (Backlog) ─────┤
│   └── 5. Build REST API Endpoints (In Progress) ─────┘
└── 3. Set Up CI/CD Pipeline (In Progress) ──────────────────────────────────── 10. Deploy to Prod
6. Create Frontend Component Library (Review) ───────── 7. Integrate Auth
```

This graph provides:
- **Diamond Dependencies:** Tasks 7 and 9 test parallel path convergence.
- **Multiple Entry Points:** Tasks 1 and 6 start independent tracks.
- **Critical Path Chains:** Tests the longest execution sequence to task 10.

---

## 🤖 AI / LLM Guardrails & Governance

TaskFlow Pro adheres to strict AI safety principles:

1. **Context Grounding:** The model is provided only with tasks in the current project. Hallucinating fictional task IDs is strictly prohibited.
2. **Server-Side Verification:** Every suggested ID is cross-checked against database records; invalid IDs are dropped.
3. **Cycle Rejection:** AI suggestions cannot introduce circular dependencies; every edge must pass Kahn's algorithm before saving.
4. **Mandatory Human-in-the-Loop:** Suggestions are advisory cards. The user must explicitly click **"Accept"**.
5. **Confidence Filter:** Recommendations with confidence under 40% are discarded.

---

## 📂 Project Structure

```
taskflow-pro/
├── .env.example              # Template environment configuration
├── .gitignore                # Cleaned & comprehensive git ignore rules
├── AI_TOOL_DECLARATION.md    # Transparent declaration of AI tooling
├── Dockerfile                # Production multi-stage Docker container
├── README.md                 # Primary project overview (this file)
├── render.yaml               # Infrastructure-as-code for Render.com
│
├── docs/                     # Central Documentation Hub
│   ├── README.md             # Documentation index & editing standards
│   ├── ARCHITECTURE.md       # Graph theory, data models & system design
│   ├── API_DOCUMENTATION.md  # Complete REST API reference
│   ├── DEPLOYMENT.md         # Cloud & Docker deployment workflows
│   └── GEMINI_SETUP.md       # Google Gemini AI configuration guide
│
└── backend/                  # Backend application & static UI
    ├── .env                  # Local environment file (ignored by git)
    ├── .env.example          # Backend-specific environment template
    ├── requirements.txt      # Python dependencies
    │
    ├── app/                  # Application source code
    │   ├── main.py           # FastAPI entrypoint & static mount
    │   ├── config.py         # Pydantic/dotenv settings loader
    │   ├── database.py       # Async SQLAlchemy database session
    │   ├── models.py         # Task, Dependency & DAGSnapshot models
    │   ├── schemas.py        # Pydantic request/response schemas
    │   ├── dag_engine.py     # Pure algorithmic DAG engine (no DB deps)
    │   ├── dag_helpers.py    # Bridge between SQLAlchemy and DAGEngine
    │   ├── ai_service.py     # Google Gemini API client & guardrails
    │   ├── seed.py           # Initial 10 tasks & 13 dependencies
    │   │
    │   ├── routes/           # REST API endpoints
    │   │   ├── tasks.py          # CRUD & Kanban column transitions
    │   │   ├── dependencies.py   # Dependency edges & DAG analysis
    │   │   └── ai.py             # AI suggestion trigger endpoint
    │   │
    │   └── tests/            # Test suite
    │       ├── test_dag_engine.py      # 22 pure unit tests for DAG engine
    │       └── test_api_requirements.py# API requirements integration suite
    │
    └── static/               # Frontend single-page application
        ├── index.html        # Semantic HTML5 Kanban & canvas layout
        ├── css/
        │   └── styles.css    # Responsive dark/light theme CSS tokens
        └── js/
            ├── api.js        # REST API client
            ├── dag-canvas.js # Interactive HTML5 Canvas graph visualizer
            └── app.js        # Kanban board controller & state management
```

---

## 📄 License

This project is licensed under the **MIT License**.
