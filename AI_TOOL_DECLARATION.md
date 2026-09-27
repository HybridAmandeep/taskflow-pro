# AI Tool Declaration — TaskFlow Pro

This document transparently declares the artificial intelligence (AI) and Large Language Model (LLM) tools utilized within TaskFlow Pro, covering both runtime in-product features and development assistance tools, as well as the governance and guardrail mechanisms in place.

---

## 1. In-Product AI Feature: Google Gemini (`gemini-3.8-flash`)

### Purpose & Role
TaskFlow Pro integrates **Google Gemini** (`gemini-3.8-flash`) via the official Google GenAI SDK (`google-genai`) to provide an intelligent dependency suggestion engine.

### Operational Workflow
1. **User Initiation:** When editing a task, the user can explicitly trigger AI assistance by clicking **"✨ AI Suggest Dependencies"**.
2. **Context Assembly:** The system extracts existing task titles, descriptions, statuses, and existing dependency pairs from the database.
3. **Structured Prompting:** The backend prompts Gemini with strict context grounding and schema requirements.
4. **Structured Response:** Gemini responds with structured JSON containing proposed prerequisites, calibrated confidence scores (0–100%), and reasoning sentences.
5. **Deterministic Filtering:** The backend validates every proposed task ID against the database, filters out suggestions below a 40% confidence threshold, and ensures no duplicate edges are proposed.
6. **Strict Human-in-the-Loop:** Suggestions are advisory only. No dependency is ever automatically applied. A user must review each suggestion and click **"Accept"** or **"Dismiss"**.
7. **DAG Integrity Check:** Accepted suggestions pass through Kahn's algorithm cycle detection before being written to SQLite.

### Hallucination & Risk Mitigation Guardrails
- **Context Grounding:** The prompt forbids the model from inventing fictional task IDs or dependencies.
- **Server-Side Validation:** The backend cross-checks all proposed task IDs against existing database entities; ungrounded IDs are silently discarded.
- **Cycle Prevention:** Algorithmic cycle detection (Tarjan/Kahn) prevents any suggestion from introducing graph deadlocks.
- **Confidence Calibration:** Low-confidence inferences (<40%) are suppressed to reduce noise.
- **Graceful Degradation:** If `GEMINI_API_KEY` is omitted or invalid, the core application and DAG scheduling engine remain 100% operational.

---

## 2. Development Assistance: Google Antigravity IDE & Pair Programming

### Tools Used
- **Google Antigravity IDE** (AI pair programming environment)
- **Advanced LLM Models** for code synthesis, architectural evaluation, refactoring, and documentation authoring.

### Scope of Assistance
- Scaffolded FastAPI router architecture and SQLAlchemy 2.0 async schemas.
- Implemented and unit-tested pure Python DAG algorithms (cycle detection, BFS schedule propagation, reverse-topological critical path calculation).
- Authored responsive UI styling with modern CSS custom properties and interactive HTML5 Canvas visualization.
- Drafted test suites, API documentation, deployment blueprints, and environment configurations.

### Human Verification & Oversight
- Every generated code component, mathematical graph algorithm, and schema definition was scrutinized, tested, and verified.
- Unit tests (`app/tests/test_dag_engine.py`) ensure algorithmic correctness independently of AI generation.
- Zero black-box AI logic is used in core scheduling: cycle detection, topological ordering, and critical path calculations are 100% deterministic algorithms.

---

## 3. Summary of Governance & Safety

| Area | Implementation |
|:---|:---|
| **Core Scheduling** | 100% deterministic (Kahn's algorithm, BFS, Dynamic Programming) |
| **AI Suggestion Engine** | Google Gemini (`gemini-3.8-flash`) |
| **Model Interaction** | Context-grounded prompts, JSON response parsing, ID validation |
| **Human Decision-Making** | 100% human-in-the-loop (mandatory explicit acceptance) |
| **Data Privacy** | Only task titles and descriptions are shared with Google GenAI API; no proprietary user credentials or secrets are transmitted |
