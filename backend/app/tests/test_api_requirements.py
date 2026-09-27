"""
End-to-end API test script for the 4 core requirements:
1. No Cycles
2. No Compounding
3. Rollback on Regression
4. Persistence
"""

import sys
import json
import urllib.request
import urllib.error
from datetime import date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"


def req(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"} if data else {}
    body = json.dumps(data).encode("utf-8") if data else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            res_body = response.read().decode("utf-8")
            return response.status, json.loads(res_body) if res_body else None
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(res_body)
        except Exception:
            return e.code, res_body


def test_1_no_cycles():
    print("\n--- Testing Requirement 1: No Cycles ---")
    status, initial_deps = req("GET", "/api/dependencies")
    assert status == 200, f"Expected 200, got {status}"
    initial_count = len(initial_deps)

    # In seed data: task-001 -> task-002 -> task-004 -> task-007
    # Attempting to add task-007 -> task-001 must be REJECTED with 409
    status, res = req("POST", "/api/dependencies", {
        "upstream_task_id": "task-007",
        "downstream_task_id": "task-001",
        "source": "manual"
    })
    assert status == 409, f"Expected 409 Conflict, got {status}: {res}"
    detail = res.get("detail", "") if isinstance(res, dict) else str(res)
    print(f"Cycle rejection detail: {detail}")
    assert "would create a circular relationship" in detail or "circular" in detail
    assert "rejected" in detail.lower() or "unchanged" in detail.lower()
    # Check that cycle sequence is shown
    assert "Integrate Auth with Frontend" in detail or "task-007" in detail

    # Verify invalid dependency was NOT persisted
    status, final_deps = req("GET", "/api/dependencies")
    assert len(final_deps) == initial_count, f"Dependency count changed! Expected {initial_count}, got {len(final_deps)}"
    assert not any(d["upstream_task_id"] == "task-007" and d["downstream_task_id"] == "task-001" for d in final_deps)
    print("PASS: Cycle successfully rejected with descriptive error, existing graph completely unchanged.")


def test_2_no_compounding():
    print("\n--- Testing Requirement 2: No Compounding ---")
    # In seed data:
    # task-004 (Auth API) -> task-007 (Auth Frontend) and task-008 (Integration Tests)
    # task-006 (Component Lib) -> task-007
    # task-005 (REST API) -> task-008
    # task-007 -> task-009 (Security Audit)
    # task-008 -> task-009
    # Diamond at task-009:
    # 4 -> 7 -> 9
    # 4 -> 8 -> 9
    # If task-004 is extended by 3 days, both paths (4->7->9 and 4->8->9) carry that change.
    # What-If on task-004:
    status, task_4 = req("GET", "/api/tasks/task-004")
    curr_end = date.fromisoformat(task_4["end_date"])
    new_end = str(curr_end + timedelta(days=3))

    status, whatif = req("POST", "/api/dag/what-if", {
        "task_id": "task-004",
        "new_end_date": new_end
    })
    assert status == 200, f"Expected 200, got {status}: {whatif}"
    shifts = {item["task_id"]: item["shift_days"] for item in whatif}
    print(f"What-If shifts from task-004 (+3d): {shifts}")

    assert shifts.get("task-007") == 3, f"Expected task-007 shift=3, got {shifts.get('task-007')}"
    assert shifts.get("task-008") == 3, f"Expected task-008 shift=3, got {shifts.get('task-008')}"
    # NO COMPOUNDING: task-009 must shift by 3, NOT 6!
    assert shifts.get("task-009") == 3, f"Expected task-009 shift=3, got {shifts.get('task-009')} (compounding bug!)"
    # task-010 must also shift by 3, NOT 6 or 9!
    assert shifts.get("task-010") == 3, f"Expected task-010 shift=3, got {shifts.get('task-010')}"

    print("PASS: Schedule changes do not compound across converging diamond paths (+3 days, not +6 days).")


def test_3_rollback_on_regression():
    print("\n--- Testing Requirement 3: Rollback on Regression ---")
    # task-002 ("Design Database Schema") is in 'done'.
    # task-004 depends on task-002.
    # task-005 depends on task-002.
    status, task_4_before = req("GET", "/api/tasks/task-004")
    print(f"Task 4 status before regression: {task_4_before['status']}")

    # Move completed task-002 back to 'in_progress'
    status, move_res = req("PATCH", "/api/tasks/task-002/move", {
        "column": "in_progress",
        "sort_order": 0
    })
    assert status == 200, f"Expected 200, got {status}: {move_res}"

    # Downstream tasks 4 and 5 must now become BLOCKED
    status, task_4_after = req("GET", "/api/tasks/task-004")
    status, task_5_after = req("GET", "/api/tasks/task-005")
    print(f"Task 4 status after regression: {task_4_after['status']} (blocked_by: {task_4_after['blocked_by']})")
    print(f"Task 5 status after regression: {task_5_after['status']} (blocked_by: {task_5_after['blocked_by']})")

    assert task_4_after["status"] == "blocked", f"Expected task-004 to be 'blocked', got {task_4_after['status']}"
    assert task_5_after["status"] == "blocked", f"Expected task-005 to be 'blocked', got {task_5_after['status']}"
    assert "Design Database Schema" in task_4_after["blocked_by"]

    # Check health metrics reflects the increase in blocked count
    status, health = req("GET", "/api/dag/health")
    print(f"Health metrics blocked count: {health['blocked_count']}")
    assert health["blocked_count"] >= 2

    # Move task-002 back to 'done'
    status, _ = req("PATCH", "/api/tasks/task-002/move", {
        "column": "done",
        "sort_order": 1
    })
    status, task_4_restored = req("GET", "/api/tasks/task-004")
    assert task_4_restored["status"] == "ready", f"Expected task-004 to be 'ready', got {task_4_restored['status']}"
    print("PASS: Moving completed task back to In Progress correctly causes downstream tasks to become Blocked.")


def test_4_persistence():
    print("\n--- Testing Requirement 4: Persistence ---")
    # Move task-008 to 'review' at position 1
    status, moved = req("PATCH", "/api/tasks/task-008/move", {
        "column": "review",
        "sort_order": 1
    })
    assert status == 200

    # Fetch all tasks from DB
    status, all_tasks = req("GET", "/api/tasks")
    task_8 = next(t for t in all_tasks if t["id"] == "task-008")
    assert task_8["column"] == "review", f"Expected 'review', got {task_8['column']}"
    assert task_8["sort_order"] == 1, f"Expected sort_order=1, got {task_8['sort_order']}"

    # Verify strictly ordered sequential sort orders in each column
    col_orders = {}
    for t in all_tasks:
        col = t["column"]
        col_orders.setdefault(col, []).append(t["sort_order"])

    for col, orders in col_orders.items():
        expected = list(range(len(orders)))
        assert orders == expected, f"Column {col} sort_orders not sequential: {orders} vs {expected}"

    # Move task-008 back to backlog
    req("PATCH", "/api/tasks/task-008/move", {
        "column": "backlog",
        "sort_order": 1
    })
    print("PASS: Board positions, column states, and order persist reliably with strict sequential indexing.")


if __name__ == "__main__":
    test_1_no_cycles()
    test_2_no_compounding()
    test_3_rollback_on_regression()
    test_4_persistence()
    print("\n==========================================")
    print("ALL 4 REQUIREMENTS VERIFIED & PASSED! 🚀")
    print("==========================================")
