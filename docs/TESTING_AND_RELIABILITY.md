# Testing & Reliability — Known Failure Cases & Quality Assurance

TaskFlow Pro is engineered with deterministic graph algorithms, comprehensive unit and integration test suites, and defensive architectural guardrails. This document outlines the testing strategy, test coverage, and a catalog of **Known Failure Cases** along with their automated mitigations and failure recovery paths.

---

## 1. Quality Assurance Architecture Overview

The system employs a multi-tiered verification methodology:

```
+-----------------------------------------------------------------------+
|                       Application Layer (FastAPI)                     |
|         Request Validation (Pydantic v2) + HTTP Error Handlers        |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                      Algorithmic Core (DAG Engine)                    |
|   - 22 Pure Python Unit Tests (app/tests/test_dag_engine.py)          |
|   - Cycle Detection, Dynamic Programming, Topological Sorting         |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                  Integration & Requirements Test Suite                |
|      - 4 E2E Invariants Verified (app/tests/test_api_requirements.py) |
|      - Cycle Rejection, Non-Compounding, Regression, Persistence      |
+-----------------------------------------------------------------------+
```

---

## 2. Test Suites & Verification

### Suite 1: DAG Engine Unit Tests (`backend/app/tests/test_dag_engine.py`)
- **Framework:** `pytest` (22 tests, 100% pass rate in <0.15s)
- **Scope:**
  - Cycle detection for 2-node mutual dependencies, multi-node loops, and self-referencing loops.
  - Topological sorting via Kahn’s algorithm on linear chains, disconnected forests, and diamond graphs.
  - Forward schedule propagation via Breadth-First Search (BFS).
  - Reverse topological Dynamic Programming for Critical Path calculation.
  - Zero compounding delay validation across converging parallel paths.

### Suite 2: Core Requirements E2E Suite (`backend/app/tests/test_api_requirements.py`)
- **Requirement 1 (No Cycles):** Validates that attempting to close a loop returns HTTP 409 Conflict with the exact cycle cycle path, leaving the graph untouched.
- **Requirement 2 (No Compounding):** Validates that extending an upstream root in a diamond graph shifts downstream convergence nodes by $\max(\text{shifts})$, not $\sum(\text{shifts})$.
- **Requirement 3 (Rollback on Regression):** Validates that moving a "Done" task backward to "In Progress" dynamically triggers downstream dependent tasks to transition to "Blocked".
- **Requirement 4 (Persistence):** Validates that board positions, column indices, and strict sequential sorting survive database reloads.

---

## 3. Catalog of Known Failure Cases & System Mitigations

The table below catalogs every known failure case, its root cause, the protective mitigation implemented, and the system outcome.

| # | Known Failure Case | Trigger / Condition | System Mitigation | HTTP / System Outcome |
|:---|:---|:---|:---|:---|
| **F-01** | **Circular Dependency Deadlock** | User or AI attempts to add an edge that creates a directed cycle (e.g., $A \to B \to C \to A$). | Kahn's algorithm verifies acyclicity before database commit. The transaction is aborted. | **409 Conflict** with exact cycle path sequence in error detail. Graph remains unchanged. |
| **F-02** | **Self-Referential Edge** | A task attempts to depend on itself ($A \to A$). | Explicit check in `validate_dependency()` and Pydantic validation reject identical source/target IDs. | **400 Bad Request** ("Task cannot depend on itself"). |
| **F-03** | **Compounding Delay in Diamond Graphs** | Upstream node delays on multiple parallel branches converge on a single downstream task. | The scheduler computes new start dates as $\max_{p \in \text{parents}}(\text{end\_date}_p)$, preventing additive double-counting. | Verified by unit tests; downstream tasks shift strictly by max upstream delay, not sum. |
| **F-04** | **Unblocking Incomplete Work (Premature Start)** | User attempts to advance a task whose prerequisites are not in "Done". | Server-side status transition check computes `is_blocked()` and lists blocking prerequisites. | Kanban card displays lock badge with blocking task names; prevents invalid status. |
| **F-05** | **Regression Cascade Block** | A completed task is moved backward to "In Progress" or "Backlog". | Downstream dependents are immediately recalculated: if any prerequisite is no longer "Done", status flips to "Blocked". | Downstream tasks marked `blocked` with `blocked_by` list updated in real-time. |
| **F-06** | **AI Hallucination of Non-Existent Tasks** | LLM suggests prerequisites with fictional or invalid task IDs. | Backend extracts valid task IDs from database and strictly filters out any suggested ID not present in active tasks. | Ungrounded suggestions are discarded before reaching the frontend. |
| **F-07** | **AI Cycle Suggestion** | LLM suggests a prerequisite that would create a circular dependency. | When the user reviews and clicks "Accept", the edge passes through `detect_cycle()`. | Cycle rejected before database insertion; descriptive alert shown to user. |
| **F-08** | **AI Service Outage / Missing API Key** | `GEMINI_API_KEY` is invalid, expired, quota-exceeded, or network fails. | Graceful degradation pattern: backend catches SDK exceptions and returns an empty suggestion list with explanatory notice. | Core app, Kanban board, and DAG scheduling remain **100% operational**. |
| **F-09** | **Date Inversion (Negative Duration)** | Task created or updated with `start_date > end_date`. | Pydantic schema validator `@field_validator` rejects start dates occurring after end dates. | **422 Unprocessable Entity** with validation message. |
| **F-10** | **Orphaned Dependency Edges** | A task is deleted while other tasks depend on it or it depends on others. | Foreign key constraints configured with `ondelete="CASCADE"` in SQLAlchemy models (`TaskDependency`). | All associated upstream and downstream dependency edges are cleanly removed in the same transaction. |
| **F-11** | **Concurrent SQLite Write Contention** | Multiple simultaneous API requests attempt database writes. | Async SQLAlchemy session (`AsyncSession`) with connection pooling and atomic commit/rollback context managers. | Requests serialize safely; automatic rollback prevents partial or corrupted writes. |
| **F-12** | **Disconnected Subgraph Forests** | Project graph contains multiple isolated clusters of tasks with no common root. | DAG algorithms (topological sort, critical path DP) iterate across all root nodes ($\text{in-degree} = 0$). | Full graph health and metrics correctly calculate across all disconnected components. |

---

## 4. How to Run the Reliability Test Suite

### Running the Unit Tests
Execute the pure Python algorithmic tests:
```bash
cd backend
python -m pytest app/tests/test_dag_engine.py -v
```

Expected output:
```text
backend/app/tests/test_dag_engine.py::test_empty_graph_topological_sort PASSED
backend/app/tests/test_dag_engine.py::test_single_node_topological_sort PASSED
backend/app/tests/test_dag_engine.py::test_linear_chain_topological_sort PASSED
backend/app/tests/test_dag_engine.py::test_diamond_graph_topological_sort PASSED
backend/app/tests/test_dag_engine.py::test_disconnected_components PASSED
backend/app/tests/test_dag_engine.py::test_cycle_detection_no_cycle PASSED
backend/app/tests/test_dag_engine.py::test_cycle_detection_two_node_cycle PASSED
backend/app/tests/test_dag_engine.py::test_cycle_detection_three_node_cycle PASSED
backend/app/tests/test_dag_engine.py::test_cycle_detection_self_loop PASSED
backend/app/tests/test_dag_engine.py::test_schedule_propagation_no_dependencies PASSED
backend/app/tests/test_dag_engine.py::test_schedule_propagation_linear_chain PASSED
backend/app/tests/test_dag_engine.py::test_schedule_propagation_diamond_no_compounding PASSED
backend/app/tests/test_dag_engine.py::test_critical_path_linear PASSED
backend/app/tests/test_dag_engine.py::test_critical_path_diamond PASSED
...
============================== 22 passed in 0.12s ==============================
```

### Running the Core Requirements Invariant Suite
With the server running on `http://localhost:8000`:
```bash
python backend/app/tests/test_api_requirements.py
```

Expected output:
```text
--- Testing Requirement 1: No Cycles ---
PASS: Cycle successfully rejected with descriptive error, existing graph completely unchanged.

--- Testing Requirement 2: No Compounding ---
PASS: Schedule changes do not compound across converging diamond paths (+3 days, not +6 days).

--- Testing Requirement 3: Rollback on Regression ---
PASS: Moving completed task back to In Progress correctly causes downstream tasks to become Blocked.

--- Testing Requirement 4: Persistence ---
PASS: Board positions, column states, and order persist reliably with strict sequential indexing.

==========================================
ALL 4 REQUIREMENTS VERIFIED & PASSED! 🚀
==========================================
```

---

## 5. Architectural Reliability Summary

| Reliability Pillar | Implementation |
|:---|:---|
| **Mathematical Correctness** | Pure Python Kahn's algorithm and reverse topological DP for critical path calculation. |
| **Data Integrity** | Foreign key cascades, atomic transactions, automatic rollbacks on errors. |
| **Resilient AI Integration** | Human-in-the-loop review, server-side entity validation, and graceful degradation on API failures. |
| **Deterministic Behavior** | Core graph scheduling uses zero stochastic logic; all schedules and critical paths are mathematically reproducible. |

---

## 🔗 Related Documentation
- 📖 [Documentation Hub](README.md)
- 🏗️ [Architecture & Graph Theory](ARCHITECTURE.md)
- 📡 [REST API Documentation](API_DOCUMENTATION.md)
- 🛡️ [AI Tool Declaration](../AI_TOOL_DECLARATION.md)
