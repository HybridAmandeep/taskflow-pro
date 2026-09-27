"""
Comprehensive unit tests for the DAG Engine.
Tests cycle detection, schedule propagation, no-compounding,
blocked/ready, rollback cascading, and critical path.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from datetime import date
from app.dag_engine import DAGEngine


def make_engine_with_data(tasks_dict, edges):
    """Helper to create a DAGEngine with task data and edges."""
    engine = DAGEngine()
    for tid, data in tasks_dict.items():
        engine.add_node(tid, data)
    for u, d in edges:
        result = engine.add_edge(u, d)
        assert result, f"Failed to add edge {u} -> {d}"
    return engine


# ── Cycle Detection ─────────────────────────────────────

def test_self_loop_rejected():
    """A -> A should be rejected."""
    engine = DAGEngine()
    engine.add_node("A")
    assert engine.add_edge("A", "A") == False
    print("  PASS: Self-loop A->A rejected")


def test_simple_cycle_rejected():
    """A -> B -> A should be rejected."""
    engine = DAGEngine()
    engine.add_node("A")
    engine.add_node("B")
    assert engine.add_edge("A", "B") == True
    assert engine.add_edge("B", "A") == False
    print("  PASS: Simple cycle A->B->A rejected")


def test_transitive_cycle_rejected():
    """A -> B -> C -> A should be rejected."""
    engine = DAGEngine()
    for n in ["A", "B", "C"]:
        engine.add_node(n)
    assert engine.add_edge("A", "B") == True
    assert engine.add_edge("B", "C") == True
    assert engine.add_edge("C", "A") == False
    print("  PASS: Transitive cycle A->B->C->A rejected")


def test_valid_dag_accepted():
    """Non-cyclic graph should be accepted."""
    engine = DAGEngine()
    for n in ["A", "B", "C", "D"]:
        engine.add_node(n)
    assert engine.add_edge("A", "B") == True
    assert engine.add_edge("A", "C") == True
    assert engine.add_edge("B", "D") == True
    assert engine.add_edge("C", "D") == True
    print("  PASS: Valid diamond DAG accepted")


def test_would_create_cycle_check():
    """would_create_cycle should check without modifying the graph."""
    engine = DAGEngine()
    for n in ["A", "B", "C"]:
        engine.add_node(n)
    engine.add_edge("A", "B")
    engine.add_edge("B", "C")

    # This would create a cycle
    assert engine.would_create_cycle("C", "A") == True
    # Graph should be unchanged
    assert "A" not in engine.adjacency.get("C", set())
    print("  PASS: would_create_cycle check doesn't modify graph")


# ── Schedule Propagation (No Compounding) ───────────────

def test_linear_propagation():
    """A -> B -> C, shift A by 3 days -> B and C shift by 3."""
    tasks = {
        "A": {"column": "done", "duration_days": 2},
        "B": {"column": "backlog", "duration_days": 3},
        "C": {"column": "backlog", "duration_days": 1},
    }
    engine = make_engine_with_data(tasks, [("A", "B"), ("B", "C")])
    affected = engine.propagate_schedule_change("A", 3)

    assert affected["B"] == 3
    assert affected["C"] == 3
    print("  PASS: Linear propagation A->B->C, +3 days")


def test_diamond_no_compounding():
    """
    A -> B -> D
    A -> C -> D
    Shifting A by 3 should shift D by 3, NOT 6.
    """
    tasks = {
        "A": {"column": "done", "duration_days": 2},
        "B": {"column": "backlog", "duration_days": 3},
        "C": {"column": "backlog", "duration_days": 2},
        "D": {"column": "backlog", "duration_days": 1},
    }
    engine = make_engine_with_data(
        tasks, [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    )
    affected = engine.propagate_schedule_change("A", 3)

    assert affected["D"] == 3, f"Expected D to shift by 3, got {affected.get('D')}"
    print("  PASS: Diamond dependency - D shifts by 3, NOT 6 (no compounding)")


def test_complex_convergence():
    """
    A -> B -> D -> E
    A -> C -> D -> E
    Shift A by 5. All downstream should shift by exactly 5.
    """
    tasks = {n: {"column": "backlog", "duration_days": 1} for n in "ABCDE"}
    engine = make_engine_with_data(
        tasks, [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")]
    )
    affected = engine.propagate_schedule_change("A", 5)

    assert affected["B"] == 5
    assert affected["C"] == 5
    assert affected["D"] == 5  # NOT 10
    assert affected["E"] == 5  # NOT 15
    print("  PASS: Complex convergence - no compounding through multiple levels")


def test_zero_shift():
    """Zero shift should return empty affected dict."""
    engine = DAGEngine()
    engine.add_node("A")
    engine.add_node("B")
    engine.add_edge("A", "B")
    affected = engine.propagate_schedule_change("A", 0)
    assert affected == {}
    print("  PASS: Zero shift returns empty")


# ── Blocked / Ready Status ─────────────────────────────

def test_no_deps_is_ready():
    """A task with no upstream dependencies should be ready."""
    engine = DAGEngine()
    engine.add_node("A", {"column": "backlog"})
    assert engine.compute_status("A") == "ready"
    print("  PASS: No deps = ready")


def test_all_done_upstream_is_ready():
    """A task is ready when all upstream tasks are done."""
    tasks = {
        "A": {"column": "done"},
        "B": {"column": "done"},
        "C": {"column": "backlog"},
    }
    engine = make_engine_with_data(tasks, [("A", "C"), ("B", "C")])
    assert engine.compute_status("C") == "ready"
    print("  PASS: All upstream done = ready")


def test_partial_upstream_is_blocked():
    """A task is blocked when any upstream task is not done."""
    tasks = {
        "A": {"column": "done"},
        "B": {"column": "in_progress"},
        "C": {"column": "backlog"},
    }
    engine = make_engine_with_data(tasks, [("A", "C"), ("B", "C")])
    assert engine.compute_status("C") == "blocked"
    print("  PASS: Partial upstream not done = blocked")


# ── Rollback Cascading ──────────────────────────────────

def test_rollback_finds_all_descendants():
    """Moving a task back should mark all downstream as potentially affected."""
    engine = DAGEngine()
    for n in ["A", "B", "C", "D"]:
        engine.add_node(n, {"column": "done"})
    engine.add_edge("A", "B")
    engine.add_edge("B", "C")
    engine.add_edge("B", "D")

    affected = engine.get_affected_by_rollback("A")
    assert affected == {"B", "C", "D"}
    print("  PASS: Rollback cascading finds all descendants")


def test_rollback_with_diamond():
    """Rollback in diamond should find all downstream (no duplicates)."""
    engine = DAGEngine()
    for n in ["A", "B", "C", "D"]:
        engine.add_node(n)
    engine.add_edge("A", "B")
    engine.add_edge("A", "C")
    engine.add_edge("B", "D")
    engine.add_edge("C", "D")

    affected = engine.get_affected_by_rollback("A")
    assert affected == {"B", "C", "D"}
    print("  PASS: Diamond rollback - no duplicates, all descendants found")


# ── Critical Path ───────────────────────────────────────

def test_critical_path_linear():
    """Linear chain: critical path is the entire chain."""
    tasks = {
        "A": {"duration_days": 3},
        "B": {"duration_days": 5},
        "C": {"duration_days": 2},
    }
    engine = make_engine_with_data(tasks, [("A", "B"), ("B", "C")])
    path, duration = engine.compute_critical_path()

    assert path == ["A", "B", "C"]
    assert duration == 10  # 3 + 5 + 2
    print("  PASS: Critical path for linear chain = A->B->C, 10 days")


def test_critical_path_picks_longest():
    """When branches exist, critical path follows the longest."""
    tasks = {
        "A": {"duration_days": 1},
        "B": {"duration_days": 10},  # Long branch
        "C": {"duration_days": 2},   # Short branch
        "D": {"duration_days": 1},
    }
    engine = make_engine_with_data(
        tasks, [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    )
    path, duration = engine.compute_critical_path()

    assert "B" in path  # Should go through the longer branch
    assert "A" in path
    assert "D" in path
    print(f"  PASS: Critical path picks longest branch, duration={duration}")


def test_critical_path_empty_graph():
    """Empty graph returns empty path."""
    engine = DAGEngine()
    path, duration = engine.compute_critical_path()
    assert path == []
    assert duration == 0
    print("  PASS: Empty graph = empty critical path")


# ── Topological Sort ────────────────────────────────────

def test_topological_sort_order():
    """Topological sort respects dependency order."""
    engine = DAGEngine()
    for n in ["A", "B", "C"]:
        engine.add_node(n)
    engine.add_edge("A", "B")
    engine.add_edge("B", "C")

    order = engine.topological_sort()
    assert order.index("A") < order.index("B") < order.index("C")
    print("  PASS: Topological sort respects order")


# ── Node Removal ────────────────────────────────────────

def test_remove_node_cleans_edges():
    """Removing a node should remove all associated edges."""
    engine = DAGEngine()
    for n in ["A", "B", "C"]:
        engine.add_node(n)
    engine.add_edge("A", "B")
    engine.add_edge("B", "C")

    engine.remove_node("B")
    assert "B" not in engine.nodes
    assert "B" not in engine.adjacency.get("A", set())
    assert "B" not in engine.reverse_adj.get("C", set())
    print("  PASS: Node removal cleans all edges")


# ── Additional Cycle, Compounding & Rollback Tests ─────────

def test_get_cycle_path_details():
    """Verify get_cycle_path returns the exact cycle sequence A -> B -> C -> A."""
    engine = DAGEngine()
    for n in ["A", "B", "C"]:
        engine.add_node(n)
    engine.add_edge("A", "B")
    engine.add_edge("B", "C")

    # Adding C -> A would create cycle
    cycle_path = engine.get_cycle_path("C", "A")
    assert cycle_path == ["C", "A", "B", "C"], f"Expected ['C', 'A', 'B', 'C'], got {cycle_path}"
    # Graph remains valid and unchanged
    assert engine.would_create_cycle("C", "A") == True
    assert "A" not in engine.adjacency.get("C", set())
    print("  PASS: get_cycle_path returns exact cycle sequence C->A->B->C")


def test_negative_shift_no_compounding():
    """Diamond dependency with negative shift (shortened) propagates correctly without compounding."""
    tasks = {
        "A": {"column": "done", "duration_days": 5},
        "B": {"column": "backlog", "duration_days": 3},
        "C": {"column": "backlog", "duration_days": 2},
        "D": {"column": "backlog", "duration_days": 1},
    }
    engine = make_engine_with_data(
        tasks, [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    )
    affected = engine.propagate_schedule_change("A", -2)

    assert affected["B"] == -2
    assert affected["C"] == -2
    assert affected["D"] == -2, f"Expected D to shift by -2, got {affected.get('D')}"
    print("  PASS: Negative shift in diamond DAG propagates -2 days to D (no compounding)")


def test_transitive_rollback_status():
    """Moving upstream completed task back to In Progress transitively blocks all downstream tasks."""
    tasks = {
        "A": {"column": "done"},
        "B": {"column": "done"},
        "C": {"column": "backlog"},
    }
    engine = make_engine_with_data(tasks, [("A", "B"), ("B", "C")])

    # Initially all upstream satisfied
    assert engine.compute_status("B") == "ready"
    assert engine.compute_status("C") == "ready"

    # Regression: Task A moves from Done to In Progress
    engine.task_data["A"]["column"] = "in_progress"

    # Both B and C must now become blocked
    assert engine.compute_status("B") == "blocked", "Task B should be blocked because A is in progress"
    assert engine.compute_status("C") == "blocked", "Task C should be blocked because B's prerequisites are not satisfied"
    print("  PASS: Upstream regression causes both direct and transitive downstream tasks to become Blocked")


# ── Run All Tests ───────────────────────────────────────

if __name__ == "__main__":
    print("\n=== DAG Engine Unit Tests ===\n")

    print("[Cycle Detection]")
    test_self_loop_rejected()
    test_simple_cycle_rejected()
    test_transitive_cycle_rejected()
    test_valid_dag_accepted()
    test_would_create_cycle_check()
    test_get_cycle_path_details()

    print("\n[Schedule Propagation]")
    test_linear_propagation()
    test_diamond_no_compounding()
    test_complex_convergence()
    test_zero_shift()
    test_negative_shift_no_compounding()

    print("\n[Blocked / Ready Status]")
    test_no_deps_is_ready()
    test_all_done_upstream_is_ready()
    test_partial_upstream_is_blocked()

    print("\n[Rollback Cascading]")
    test_rollback_finds_all_descendants()
    test_rollback_with_diamond()
    test_transitive_rollback_status()

    print("\n[Critical Path]")
    test_critical_path_linear()
    test_critical_path_picks_longest()
    test_critical_path_empty_graph()

    print("\n[Topological Sort]")
    test_topological_sort_order()

    print("\n[Node Removal]")
    test_remove_node_cleans_edges()

    print("\n=== ALL 20 TESTS PASSED ===\n")
