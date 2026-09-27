from __future__ import annotations
from datetime import date, timedelta
from collections import defaultdict, deque
from typing import Optional


class DAGEngine:
    """
    Pure-logic DAG engine. Operates on in-memory adjacency lists.
    No database imports — fully testable in isolation.
    """

    def __init__(self):
        # adjacency: upstream_id -> set of downstream_ids
        self.adjacency: dict[str, set[str]] = defaultdict(set)
        # reverse adjacency: downstream_id -> set of upstream_ids
        self.reverse_adj: dict[str, set[str]] = defaultdict(set)
        # all known node ids
        self.nodes: set[str] = set()
        # task metadata: id -> {column, start_date, end_date, duration_days, title}
        self.task_data: dict[str, dict] = {}

    # ── Graph Construction ──────────────────────────────────────────

    def add_node(self, task_id: str, data: dict | None = None):
        self.nodes.add(task_id)
        if data:
            self.task_data[task_id] = data

    def remove_node(self, task_id: str):
        # Remove all edges involving this node
        for downstream in list(self.adjacency.get(task_id, [])):
            self.reverse_adj[downstream].discard(task_id)
        for upstream in list(self.reverse_adj.get(task_id, [])):
            self.adjacency[upstream].discard(task_id)
        self.adjacency.pop(task_id, None)
        self.reverse_adj.pop(task_id, None)
        self.nodes.discard(task_id)
        self.task_data.pop(task_id, None)

    def add_edge(self, upstream_id: str, downstream_id: str) -> bool:
        """
        Add a dependency edge. Returns True if successful.
        Returns False if the edge would create a cycle.
        """
        if upstream_id == downstream_id:
            return False  # Self-loop

        # Temporarily add the edge
        self.adjacency[upstream_id].add(downstream_id)
        self.reverse_adj[downstream_id].add(upstream_id)
        self.nodes.add(upstream_id)
        self.nodes.add(downstream_id)

        # Check for cycle
        if self._has_cycle():
            # Rollback
            self.adjacency[upstream_id].discard(downstream_id)
            self.reverse_adj[downstream_id].discard(upstream_id)
            return False

        return True

    def remove_edge(self, upstream_id: str, downstream_id: str):
        self.adjacency[upstream_id].discard(downstream_id)
        self.reverse_adj[downstream_id].discard(upstream_id)

    # ── Cycle Detection & Path Finding ─────────────────────────────

    def find_path(self, start_id: str, end_id: str) -> list[str] | None:
        """Find a directed path from start_id to end_id using BFS. Returns list of node IDs or None."""
        if start_id == end_id:
            return [start_id]
        queue = deque([[start_id]])
        visited = {start_id}
        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor in self.adjacency.get(node, []):
                if neighbor == end_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def get_cycle_path(self, upstream_id: str, downstream_id: str) -> list[str] | None:
        """
        If adding upstream_id -> downstream_id would create a cycle,
        return the cycle path [upstream_id, downstream_id, ..., upstream_id].
        Returns None if no cycle would be created.
        """
        if upstream_id == downstream_id:
            return [upstream_id, upstream_id]
        # Adding upstream_id -> downstream_id creates a cycle iff downstream_id can reach upstream_id
        path_from_down_to_up = self.find_path(downstream_id, upstream_id)
        if path_from_down_to_up:
            return [upstream_id] + path_from_down_to_up
        return None

    def _has_cycle(self) -> bool:
        """Detect cycle using Kahn's topological sort. O(V + E)."""
        in_degree: dict[str, int] = defaultdict(int)
        for node in self.nodes:
            in_degree.setdefault(node, 0)
        for src in self.adjacency:
            for dst in self.adjacency[src]:
                in_degree[dst] += 1

        queue = deque(n for n in self.nodes if in_degree[n] == 0)
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in self.adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count != len(self.nodes)

    def would_create_cycle(self, upstream_id: str, downstream_id: str) -> bool:
        """Check if adding an edge would create a cycle WITHOUT modifying the graph."""
        return self.get_cycle_path(upstream_id, downstream_id) is not None

    # ── Topological Sort ────────────────────────────────────────────

    def topological_sort(self) -> list[str]:
        """Return nodes in topological order. Raises ValueError on cycle."""
        in_degree: dict[str, int] = defaultdict(int)
        for node in self.nodes:
            in_degree.setdefault(node, 0)
        for src in self.adjacency:
            for dst in self.adjacency[src]:
                in_degree[dst] += 1

        queue = deque(n for n in self.nodes if in_degree[n] == 0)
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self.adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise ValueError("Graph contains a cycle — topological sort not possible.")
        return result

    # ── Schedule Propagation (No Compounding) ───────────────────────

    def propagate_schedule_change(
        self, changed_task_id: str, delta_days: int
    ) -> dict[str, int]:
        """
        Propagate a schedule shift downstream without compounding.
        When multiple dependency paths converge on the same downstream task
        (e.g., A -> B -> D and A -> C -> D), the change from Task A must not
        be counted more than once. The downstream task reflects the actual
        schedule impact, not accumulating the same upstream delay once for
        every path through the DAG.

        Processes nodes in topological order.

        Returns: dict of {task_id: shift_days} for all affected tasks.
        """
        if delta_days == 0:
            return {}

        # 1. Collect all reachable downstream descendants via BFS
        descendants: set[str] = set()
        queue = deque(self.adjacency.get(changed_task_id, []))
        while queue:
            node = queue.popleft()
            if node not in descendants:
                descendants.add(node)
                for downstream in self.adjacency.get(node, []):
                    if downstream not in descendants:
                        queue.append(downstream)

        if not descendants:
            return {}

        # 2. Sort descendants in topological order
        try:
            topo = self.topological_sort()
            sorted_descendants = [n for n in topo if n in descendants]
        except ValueError:
            # Fallback if graph state is inconsistent
            sorted_descendants = list(descendants)

        # 3. Propagate shifts in topological order
        node_shift: dict[str, int] = {}
        for node in sorted_descendants:
            incoming_shifts = []
            for parent in self.reverse_adj.get(node, []):
                if parent == changed_task_id:
                    incoming_shifts.append(delta_days)
                elif parent in node_shift:
                    incoming_shifts.append(node_shift[parent])

            if incoming_shifts:
                # Downstream task reflects the max schedule impact from upstream paths,
                # ensuring multiple converging paths from the same change do not compound.
                if delta_days >= 0:
                    node_shift[node] = max(incoming_shifts)
                else:
                    node_shift[node] = min(incoming_shifts)
            else:
                node_shift[node] = delta_days

        return node_shift

    # ── Blocked / Ready Status ──────────────────────────────────────

    def compute_status(self, task_id: str, memo: dict[str, str] | None = None) -> str:
        """
        A task is READY if it has no upstream deps, or ALL upstream
        tasks are in the 'done' column and their prerequisites are satisfied.
        Otherwise it's BLOCKED.
        Supports memoization for fast O(V + E) evaluation.
        """
        if memo is None:
            memo = {}
        if task_id in memo:
            return memo[task_id]

        upstreams = self.reverse_adj.get(task_id, set())
        if not upstreams:
            memo[task_id] = "ready"
            return "ready"

        for upstream_id in upstreams:
            upstream_data = self.task_data.get(upstream_id, {})
            # If any upstream task is not in Done column, this task is Blocked
            if upstream_data.get("column") != "done":
                memo[task_id] = "blocked"
                return "blocked"
            # If an upstream task is marked Done, but its own prerequisites became unsatisfied
            # (i.e. it is transitively blocked), it cannot satisfy downstream tasks
            if self.compute_status(upstream_id, memo) == "blocked":
                memo[task_id] = "blocked"
                return "blocked"

        memo[task_id] = "ready"
        return "ready"

    def compute_all_statuses(self) -> dict[str, str]:
        """Compute blocked/ready for every task in the graph."""
        memo: dict[str, str] = {}
        return {task_id: self.compute_status(task_id, memo) for task_id in self.nodes}

    # ── Rollback Cascading ──────────────────────────────────────────

    def get_affected_by_rollback(self, task_id: str) -> set[str]:
        """
        When a task moves from Done back to an earlier column (e.g., In Progress),
        find all downstream tasks that should become Blocked because their
        prerequisites are no longer satisfied.
        Uses BFS through all descendants.
        """
        affected = set()
        queue = deque(self.adjacency.get(task_id, []))
        while queue:
            node = queue.popleft()
            if node in affected:
                continue
            affected.add(node)
            for downstream in self.adjacency.get(node, []):
                if downstream not in affected:
                    queue.append(downstream)
        return affected

    # ── Critical Path ───────────────────────────────────────────────

    def compute_critical_path(self) -> tuple[list[str], int]:
        """
        Find the longest path through the DAG (critical path).
        Uses DP in reverse topological order.

        Returns: (list of task IDs on critical path, total duration in days)
        """
        try:
            topo_order = self.topological_sort()
        except ValueError:
            return [], 0

        if not topo_order:
            return [], 0

        # dist[node] = longest path starting from node
        dist: dict[str, int] = {}
        next_on_path: dict[str, str | None] = {}

        # Process in reverse topological order
        for node in reversed(topo_order):
            duration = self.task_data.get(node, {}).get("duration_days", 1)
            best_downstream = 0
            best_next = None

            for downstream in self.adjacency.get(node, []):
                if dist.get(downstream, 0) > best_downstream:
                    best_downstream = dist[downstream]
                    best_next = downstream

            dist[node] = duration + best_downstream
            next_on_path[node] = best_next

        # Find the starting node with the longest path
        if not dist:
            return [], 0

        start = max(dist, key=lambda n: dist[n])
        path = []
        current: str | None = start
        while current is not None:
            path.append(current)
            current = next_on_path.get(current)

        return path, dist[start]

    # ── What-If Simulation ──────────────────────────────────────────

    def simulate_date_change(
        self, task_id: str, new_start: date, new_end: date
    ) -> list[dict]:
        """
        Simulate a date change without modifying actual data.
        Returns a list of {task_id, old_start, old_end, new_start, new_end, shift_days}.
        """
        current_data = self.task_data.get(task_id, {})
        old_end = current_data.get("end_date")
        if not old_end or not new_end:
            return []

        if isinstance(old_end, str):
            old_end = date.fromisoformat(old_end)
        if isinstance(new_end, str):
            new_end = date.fromisoformat(new_end)

        delta_days = (new_end - old_end).days
        if delta_days == 0:
            return []

        affected = self.propagate_schedule_change(task_id, delta_days)
        results = []

        for tid, shift in affected.items():
            td = self.task_data.get(tid, {})
            t_start = td.get("start_date")
            t_end = td.get("end_date")

            if isinstance(t_start, str):
                t_start = date.fromisoformat(t_start)
            if isinstance(t_end, str):
                t_end = date.fromisoformat(t_end)

            new_t_start = t_start + timedelta(days=shift) if t_start else None
            new_t_end = t_end + timedelta(days=shift) if t_end else None

            results.append({
                "task_id": tid,
                "title": td.get("title", ""),
                "old_start": str(t_start) if t_start else None,
                "old_end": str(t_end) if t_end else None,
                "new_start": str(new_t_start) if new_t_start else None,
                "new_end": str(new_t_end) if new_t_end else None,
                "shift_days": shift,
            })

        return results

    # ── Bottleneck Detection ────────────────────────────────────────

    def find_bottlenecks(self, top_n: int = 3) -> list[dict]:
        """
        Find tasks that block the most downstream work.
        Returns top N bottleneck tasks sorted by downstream count.
        """
        downstream_counts: dict[str, int] = {}

        for node in self.nodes:
            # Count all reachable downstream nodes via BFS
            visited = set()
            queue = deque(self.adjacency.get(node, []))
            while queue:
                n = queue.popleft()
                if n in visited:
                    continue
                visited.add(n)
                for d in self.adjacency.get(n, []):
                    if d not in visited:
                        queue.append(d)
            downstream_counts[node] = len(visited)

        sorted_tasks = sorted(
            downstream_counts.items(), key=lambda x: x[1], reverse=True
        )
        results = []
        for task_id, count in sorted_tasks[:top_n]:
            if count > 0:
                td = self.task_data.get(task_id, {})
                results.append({
                    "task_id": task_id,
                    "title": td.get("title", ""),
                    "downstream_count": count,
                    "column": td.get("column", ""),
                })
        return results

    # ── Health Metrics ──────────────────────────────────────────────

    def get_health_metrics(self) -> dict:
        """Dependency health dashboard metrics."""
        statuses = self.compute_all_statuses()
        blocked = sum(1 for s in statuses.values() if s == "blocked")
        ready = sum(1 for s in statuses.values() if s == "ready")
        critical_path, cp_duration = self.compute_critical_path()

        # Average chain depth
        depths = []
        for node in self.nodes:
            depth = 0
            current = {node}
            visited = set()
            while current:
                next_level = set()
                for n in current:
                    if n in visited:
                        continue
                    visited.add(n)
                    next_level.update(self.reverse_adj.get(n, set()))
                current = next_level - visited
                if current:
                    depth += 1
            depths.append(depth)

        avg_depth = sum(depths) / len(depths) if depths else 0

        return {
            "total_tasks": len(self.nodes),
            "blocked_count": blocked,
            "ready_count": ready,
            "done_count": sum(
                1 for n in self.nodes
                if self.task_data.get(n, {}).get("column") == "done"
            ),
            "critical_path_length": len(critical_path),
            "critical_path_duration_days": cp_duration,
            "average_chain_depth": round(avg_depth, 1),
            "total_dependencies": sum(len(v) for v in self.adjacency.values()),
            "bottlenecks": self.find_bottlenecks(3),
        }
