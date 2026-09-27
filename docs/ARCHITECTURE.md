# Architecture & Technical Design — TaskFlow Pro

This document describes the architectural principles, algorithmic foundations, database design, and component interactions of **TaskFlow Pro**.

---

## 1. Architectural Philosophy

TaskFlow Pro is designed around a fundamental principle:
> **All graph scheduling and dependency constraints must be mathematically deterministic and provably correct.**

Artificial Intelligence (Google Gemini) serves strictly as an **advisory layer** for recommending logical prerequisites based on task descriptions. It never writes to the graph directly and cannot bypass graph invariants.

---

## 2. The 4 Core Architectural Requirements

TaskFlow Pro is built to guarantee four core invariants:

### Requirement 1: No Cycles (Zero Circular Dependencies)
- **Algorithm:** Kahn's Algorithm for Topological Sorting.
- **Enforcement:** Every proposed edge (manual or AI-recommended) is tentatively added to the graph. If topological sort fails to visit all nodes, a cycle exists.
- **Guarantee:** The cycle is rejected with an HTTP `409 Conflict` containing the exact cycle path (e.g. `A -> B -> C -> A`). The graph remains 100% unchanged.

### Requirement 2: No Compounding (Diamond Path Propagation)
- **Problem:** In a diamond graph ($A \rightarrow B \rightarrow D$ and $A \rightarrow C \rightarrow D$), shifting task $A$ by $+3$ days delivers a $+3$ day delay through branch $B$ and a $+3$ day delay through branch $C$. Naive summation shifts $D$ by $+6$ days (a critical bug in many workflow engines).
- **Algorithm:** Breadth-First Search (BFS) tracking `max_shift` at every visited node.
- **Guarantee:** Task $D$ shifts by $\max(3, 3) = +3$ days. Delay propagates along parallel paths without false compounding.

### Requirement 3: Rollback Cascading on Regression
- **Requirement:** If a finished task (e.g. *"Design Database Schema"*) is dragged backwards from `done` to `in_progress`, all downstream tasks that depend on it must immediately reflect a `blocked` status.
- **Enforcement:** Task readiness status (`ready` vs `blocked`) is computed dynamically on read based on the live states of upstream prerequisites.
- **Guarantee:** Moving a task backward instantly updates downstream statuses and live health metrics.

### Requirement 4: State Persistence & Strict Column Ordering
- **Requirement:** The board layout, card positions, and dependency graphs must persist across restarts.
- **Enforcement:** SQLite via `aiosqlite` and `SQLAlchemy 2.0`. Reordering cards re-indexes `sort_order` as a strict 0-indexed sequence (`0, 1, 2, ...`).

---

## 3. Algorithmic Specifications (`dag_engine.py`)

The DAG engine is implemented as a pure Python class (`DAGEngine`) with zero database or framework dependencies, making it 100% testable in isolation.

### 3.1 Cycle Detection
```python
def has_cycle(self) -> bool:
    in_degrees = {node: 0 for node in self.adj}
    for u in self.adj:
        for v in self.adj[u]:
            in_degrees[v] += 1
            
    queue = deque([n for n, deg in in_degrees.items() if deg == 0])
    visited_count = 0
    
    while queue:
        u = queue.popleft()
        visited_count += 1
        for v in self.adj[u]:
            in_degrees[v] -= 1
            if in_degrees[v] == 0:
                queue.append(v)
                
    return visited_count < len(self.adj)
```

### 3.2 Schedule Propagation & What-If Simulation
When task $T$ is shifted by $\Delta$ days:
1. Initialize `max_shift = {T: delta}`.
2. Traverse downstream successors in topological order.
3. For each edge $u \rightarrow v$:
   $$\text{projected\_start}(v) = \max(\text{current\_start}(v), \text{projected\_end}(u) + 1)$$
   $$\text{shift}(v) = \text{projected\_start}(v) - \text{current\_start}(v)$$
   $$\text{max\_shift}[v] = \max(\text{max\_shift}.get(v, 0), \text{shift}(v))$$
4. Return only affected downstream nodes and their net shifts.

### 3.3 Critical Path Analysis
- The critical path is the longest path through the project network.
- Computed using Dynamic Programming in reverse topological order:
  $$\text{dist}[u] = \text{duration}[u] + \max_{v \in \text{successors}(u)} (\text{dist}[v])$$
- The path with the maximum total duration determines the minimum completion time of the project.

---

## 4. Database Schema

```
+-------------------------------------------------------------+
|                         Task                                |
+-------------------------------------------------------------+
| id: String (Primary Key, e.g. "task-001")                   |
| title: String                                               |
| description: String                                         |
| column: String ("backlog", "in_progress", "review", "done") |
| sort_order: Integer                                         |
| duration_days: Integer                                      |
| start_date: Date                                            |
| end_date: Date                                              |
| created_at: DateTime                                        |
| updated_at: DateTime                                        |
+------------------------------+------------------------------+
                               |
                               | 1:N
                               v
+-------------------------------------------------------------+
|                      Dependency                             |
+-------------------------------------------------------------+
| id: String (Primary Key, e.g. "dep-001")                    |
| upstream_task_id: String (FK -> Task.id)                    |
| downstream_task_id: String (FK -> Task.id)                  |
| source: String ("manual" | "ai")                            |
| created_at: DateTime                                        |
+-------------------------------------------------------------+
```

---

## 5. AI Suggestion Architecture

```
User Clicks "AI Suggest Dependencies"
               |
               v
FastAPI reads Task + All Other Tasks from DB
               |
               v
Constructs Context-Grounded Prompt
               |
               v
Google GenAI Client (`gemini-3.8-flash`)
               |
               v
Parses JSON { suggestions: [ {upstream_task_id, confidence, reasoning} ] }
               |
               v
Filters: Valid IDs only? Not self? Not existing edge? Confidence >= 40%?
               |
               v
Returns Cleaned Suggestions to Frontend
               |
               v
User clicks "Accept" -> Passes Kahn's cycle check -> Saved to DB
```

---

## 6. Frontend Architecture

- **Zero Build Tools:** Pure native HTML5, modern CSS custom properties, and modular ES6 JavaScript.
- **Interactive HTML5 Canvas:** Renders live DAG nodes, dependency arrows, critical path highlights, and bezier curves with pan/zoom support.
- **Responsive Theme Engine:** Solid corporate color palettes supporting Dark and Light modes.

---

## 7. Related Documentation

- 📖 [Documentation Index](README.md)
- 📡 [REST API Documentation](API_DOCUMENTATION.md)
- 🚀 [Deployment Guide](DEPLOYMENT.md)
- 🤖 [Gemini AI Setup Guide](GEMINI_SETUP.md)
