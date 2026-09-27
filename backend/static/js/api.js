/**
 * TaskFlow Pro — API Client
 * All backend communication goes through this module.
 */

const API_BASE = '';  // Same origin

async function handleResponse(res) {
    if (!res.ok) {
        const text = await res.text();
        let message = text;
        try {
            const data = JSON.parse(text);
            if (data && data.detail) {
                message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
            }
        } catch (_) {}
        throw new Error(message);
    }
    if (res.status === 204) return null;
    return res.json();
}

const api = {
    // ── Tasks ──────────────────────────────────
    async getTasks() {
        const res = await fetch(`${API_BASE}/api/tasks`);
        return handleResponse(res);
    },

    async createTask(data) {
        const res = await fetch(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return handleResponse(res);
    },

    async updateTask(taskId, data) {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return handleResponse(res);
    },

    async moveTask(taskId, column, sortOrder = 0) {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}/move`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ column, sort_order: sortOrder }),
        });
        return handleResponse(res);
    },

    async deleteTask(taskId) {
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'DELETE',
        });
        return handleResponse(res);
    },

    // ── Dependencies ───────────────────────────
    async getDependencies() {
        const res = await fetch(`${API_BASE}/api/dependencies`);
        return handleResponse(res);
    },

    async createDependency(upstreamId, downstreamId, source = 'manual') {
        const res = await fetch(`${API_BASE}/api/dependencies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                upstream_task_id: upstreamId,
                downstream_task_id: downstreamId,
                source,
            }),
        });
        return handleResponse(res);
    },

    async deleteDependency(depId) {
        const res = await fetch(`${API_BASE}/api/dependencies/${depId}`, {
            method: 'DELETE',
        });
        return handleResponse(res);
    },

    // ── DAG Analysis ───────────────────────────
    async getCriticalPath() {
        const res = await fetch(`${API_BASE}/api/dag/critical-path`);
        return handleResponse(res);
    },

    async getHealth() {
        const res = await fetch(`${API_BASE}/api/dag/health`);
        return handleResponse(res);
    },

    async whatIf(taskId, newEndDate) {
        const res = await fetch(`${API_BASE}/api/dag/what-if`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: taskId,
                new_end_date: newEndDate,
            }),
        });
        return handleResponse(res);
    },

    // ── AI ──────────────────────────────────────
    async suggestDependencies(taskId) {
        const res = await fetch(`${API_BASE}/api/ai/suggest-dependencies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId }),
        });
        return handleResponse(res);
    },
};
