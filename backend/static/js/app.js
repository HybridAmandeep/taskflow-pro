/**
 * TaskFlow Pro — Main Application
 * Kanban board with drag-and-drop, modals, AI integration, and live state.
 */

// ── State ─────────────────────────────────────
let tasks = [];
let dependencies = [];
let criticalPathIds = [];
let currentEditTaskId = null;
let editDeps = [];  // Dependencies for the task being edited
let dagCanvas = null;
let whatIfData = [];

// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    setupTheme();
    dagCanvas = new DAGCanvas('dag-canvas');
    await refreshAll();
    setupTabs();
    setupDragAndDrop();
    setupModals();
    setupWhatIf();
});

// ── Data Loading ──────────────────────────────
async function refreshAll() {
    try {
        [tasks, dependencies] = await Promise.all([
            api.getTasks(),
            api.getDependencies(),
        ]);
        renderBoard();
        refreshHealth();
        refreshCriticalPath();
        refreshDAG();
    } catch (err) {
        showToast('Failed to load data: ' + err.message, 'error');
    }
}

async function refreshHealth() {
    try {
        const h = await api.getHealth();
        document.getElementById('val-blocked').textContent = h.blocked_count;
        document.getElementById('val-ready').textContent = h.ready_count;
        document.getElementById('val-done').textContent = h.done_count;
        document.getElementById('val-cp').textContent = h.critical_path_duration_days + 'd';
        document.getElementById('val-deps').textContent = h.total_dependencies;
        const bn = h.bottlenecks && h.bottlenecks[0];
        document.getElementById('val-bottleneck').textContent =
            bn ? bn.title.substring(0, 20) + (bn.title.length > 20 ? '…' : '') : '—';
    } catch (e) { /* ignore */ }
}

async function refreshCriticalPath() {
    try {
        const cp = await api.getCriticalPath();
        criticalPathIds = cp.path.map(n => n.task_id);
        renderCriticalPathView(cp);
    } catch (e) {
        criticalPathIds = [];
    }
}

async function refreshDAG() {
    if (dagCanvas) {
        dagCanvas.setData(tasks, dependencies, criticalPathIds);
    }
}

// ── Board Rendering ───────────────────────────
function renderBoard() {
    const columns = {
        backlog: [],
        in_progress: [],
        review: [],
        done: [],
    };

    for (const task of tasks) {
        const col = task.column || 'backlog';
        if (columns[col]) columns[col].push(task);
    }

    for (const [col, colTasks] of Object.entries(columns)) {
        const body = document.getElementById(`body-${col}`);
        const count = document.getElementById(`count-${col}`);

        colTasks.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

        count.textContent = colTasks.length;
        body.innerHTML = '';

        if (colTasks.length === 0) {
            body.innerHTML = '<div class="column-empty">Drop tasks here</div>';
            continue;
        }

        for (const task of colTasks) {
            body.appendChild(createTaskCard(task));
        }
    }
}

function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = `task-card status-${task.status}`;
    card.dataset.taskId = task.id;
    card.draggable = true;
    card.id = `card-${task.id}`;

    // Check if on critical path
    if (criticalPathIds.includes(task.id)) {
        card.classList.add('on-critical-path');
    }

    // Count dependencies for this task
    const depCount = dependencies.filter(
        d => d.downstream_task_id === task.id || d.upstream_task_id === task.id
    ).length;

    const dateStr = task.start_date
        ? `${formatDate(task.start_date)} → ${formatDate(task.end_date)}`
        : '';

    const statusIcon = task.status === 'blocked'
        ? '<span class="material-symbols-outlined icon-sm" style="font-size:12px;vertical-align:-2px">cancel</span>'
        : '<span class="material-symbols-outlined icon-sm" style="font-size:12px;vertical-align:-2px">check_circle</span>';

    card.innerHTML = `
        <div class="task-card-title">${escapeHtml(task.title)}</div>
        ${task.description ? `<div class="task-card-desc">${escapeHtml(task.description)}</div>` : ''}
        <div class="task-card-footer">
            <span class="task-status-badge ${task.status}">${statusIcon} ${task.status}</span>
            ${dateStr ? `<span class="task-date-badge">${dateStr}</span>` : ''}
            ${depCount > 0 ? `<span class="task-dep-count"><span class="material-symbols-outlined" style="font-size:12px;vertical-align:-2px">link</span> ${depCount}</span>` : ''}
        </div>
        ${task.status === 'blocked' && task.blocked_by && task.blocked_by.length > 0
            ? `<div class="blocked-tooltip"><span class="material-symbols-outlined icon-sm" style="font-size:13px;vertical-align:-3px;margin-right:4px">info</span>Blocked by: ${task.blocked_by.map(escapeHtml).join(', ')}</div>`
            : ''
        }
    `;

    // Click to edit
    card.addEventListener('click', (e) => {
        if (e.target.closest('.blocked-tooltip')) return;
        openEditModal(task);
    });

    return card;
}

// ── Drag and Drop ─────────────────────────────
function setupDragAndDrop() {
    const columns = document.querySelectorAll('.column-body');
    const dropIndicator = document.createElement('div');
    dropIndicator.className = 'drop-indicator';

    function getDropIndex(columnBody, mouseY) {
        const cards = [...columnBody.querySelectorAll('.task-card:not(.dragging)')];
        for (let i = 0; i < cards.length; i++) {
            const box = cards[i].getBoundingClientRect();
            if (mouseY < box.top + box.height / 2) {
                return { element: cards[i], index: i };
            }
        }
        return { element: null, index: cards.length };
    }

    document.addEventListener('dragstart', (e) => {
        const card = e.target.closest('.task-card');
        if (!card) return;
        card.classList.add('dragging');
        e.dataTransfer.setData('text/plain', card.dataset.taskId);
        e.dataTransfer.effectAllowed = 'move';
    });

    document.addEventListener('dragend', (e) => {
        const card = e.target.closest('.task-card');
        if (card) card.classList.remove('dragging');
        if (dropIndicator.parentNode) dropIndicator.remove();
        document.querySelectorAll('.kanban-column').forEach(col =>
            col.classList.remove('drag-over')
        );
    });

    columns.forEach(col => {
        col.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            col.closest('.kanban-column').classList.add('drag-over');

            const target = getDropIndex(col, e.clientY);
            if (target.element) {
                col.insertBefore(dropIndicator, target.element);
            } else {
                col.appendChild(dropIndicator);
            }
        });

        col.addEventListener('dragleave', (e) => {
            if (!col.contains(e.relatedTarget)) {
                col.closest('.kanban-column').classList.remove('drag-over');
                if (col.contains(dropIndicator)) dropIndicator.remove();
            }
        });

        col.addEventListener('drop', async (e) => {
            e.preventDefault();
            col.closest('.kanban-column').classList.remove('drag-over');
            const target = getDropIndex(col, e.clientY);
            const targetIndex = target.index;
            if (dropIndicator.parentNode) dropIndicator.remove();

            const taskId = e.dataTransfer.getData('text/plain');
            const newColumn = col.closest('.kanban-column').dataset.column;

            if (!taskId || !newColumn) return;

            const currentTask = tasks.find(t => t.id === taskId);
            const isRegression = (currentTask && currentTask.column === 'done' && newColumn !== 'done');

            try {
                await api.moveTask(taskId, newColumn, targetIndex);
                if (isRegression) {
                    showToast(`'${currentTask.title}' moved back to ${newColumn.replace('_', ' ')}. Downstream tasks are now Blocked.`, 'warning');
                } else {
                    showToast('Task position updated', 'success');
                }
                await refreshAll();
            } catch (err) {
                showToast('Failed to move task: ' + err.message, 'error');
            }
        });
    });
}

// ── Tab Switching ─────────────────────────────
function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const view = tab.dataset.view;
            document.querySelectorAll('.view-board, .view-dag, .view-critical')
                .forEach(v => v.classList.remove('active'));

            if (view === 'board') {
                document.getElementById('view-board').classList.add('active');
            } else if (view === 'dag') {
                document.getElementById('view-dag').classList.add('active');
                // Re-render DAG on tab switch to get proper canvas dimensions
                setTimeout(() => refreshDAG(), 50);
            } else if (view === 'critical') {
                document.getElementById('view-critical').classList.add('active');
            }
        });
    });
}

// ── Task Modal ────────────────────────────────
function setupModals() {
    const overlay = document.getElementById('modal-overlay');
    const closeBtn = document.getElementById('modal-close');
    const cancelBtn = document.getElementById('btn-modal-cancel');
    const saveBtn = document.getElementById('btn-modal-save');
    const deleteBtn = document.getElementById('btn-modal-delete');
    const newTaskBtn = document.getElementById('btn-new-task');
    const addDepBtn = document.getElementById('btn-add-dep');
    const aiSuggestBtn = document.getElementById('btn-ai-suggest');
    const depSelect = document.getElementById('dep-select');

    // Date synchronization
    const startInput = document.getElementById('input-start');
    const endInput = document.getElementById('input-end');
    const durationInput = document.getElementById('input-duration');

    function syncDatesFromStartOrDuration() {
        const sVal = startInput.value;
        const dur = parseInt(durationInput.value) || 1;
        if (sVal) {
            const d = new Date(sVal + 'T00:00:00');
            d.setDate(d.getDate() + dur - 1);
            endInput.value = d.toISOString().split('T')[0];
        }
    }

    function syncDurationFromEnd() {
        const sVal = startInput.value;
        const eVal = endInput.value;
        if (sVal && eVal) {
            const startD = new Date(sVal + 'T00:00:00');
            const endD = new Date(eVal + 'T00:00:00');
            const diffDays = Math.round((endD - startD) / (1000 * 60 * 60 * 24)) + 1;
            if (diffDays >= 1) {
                durationInput.value = diffDays;
            }
        }
    }

    startInput.addEventListener('change', syncDatesFromStartOrDuration);
    durationInput.addEventListener('input', syncDatesFromStartOrDuration);
    endInput.addEventListener('change', syncDurationFromEnd);
    if (depSelect) depSelect.addEventListener('change', hideDepError);

    newTaskBtn.addEventListener('click', () => openCreateModal());
    closeBtn.addEventListener('click', () => closeModal());
    cancelBtn.addEventListener('click', () => closeModal());
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    saveBtn.addEventListener('click', () => saveTask());
    deleteBtn.addEventListener('click', () => deleteCurrentTask());
    addDepBtn.addEventListener('click', () => addDependencyFromSelect());
    aiSuggestBtn.addEventListener('click', () => fetchAISuggestions());
}

function showDepError(msg) {
    const banner = document.getElementById('dep-error-banner');
    if (banner) {
        banner.textContent = '⚠️ ' + msg;
        banner.style.display = 'block';
    }
}

function hideDepError() {
    const banner = document.getElementById('dep-error-banner');
    if (banner) {
        banner.style.display = 'none';
        banner.textContent = '';
    }
}

function openCreateModal() {
    currentEditTaskId = null;
    editDeps = [];
    hideDepError();
    document.getElementById('modal-title').textContent = 'New Task';
    document.getElementById('input-title').value = '';
    document.getElementById('input-desc').value = '';
    document.getElementById('input-start').value = '';
    document.getElementById('input-end').value = '';
    document.getElementById('input-duration').value = '1';
    document.getElementById('btn-modal-delete').style.display = 'none';
    document.getElementById('ai-suggestions').style.display = 'none';
    renderDepsInModal();
    populateDepSelect();
    document.getElementById('modal-overlay').style.display = 'flex';
    document.getElementById('input-title').focus();
}

function openEditModal(task) {
    currentEditTaskId = task.id;
    hideDepError();
    editDeps = dependencies
        .filter(d => d.downstream_task_id === task.id)
        .map(d => ({
            id: d.id,
            upstream_task_id: d.upstream_task_id,
            upstream_title: d.upstream_title,
        }));

    document.getElementById('modal-title').textContent = 'Edit Task';
    document.getElementById('input-title').value = task.title;
    document.getElementById('input-desc').value = task.description || '';
    document.getElementById('input-start').value = task.start_date || '';
    document.getElementById('input-end').value = task.end_date || '';
    document.getElementById('input-duration').value = task.duration_days || 1;
    document.getElementById('btn-modal-delete').style.display = 'inline-flex';
    document.getElementById('ai-suggestions').style.display = 'none';
    renderDepsInModal();
    populateDepSelect();
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
    currentEditTaskId = null;
    editDeps = [];
    hideDepError();
}

function renderDepsInModal() {
    const container = document.getElementById('deps-list');
    if (editDeps.length === 0) {
        container.innerHTML = '<span class="deps-empty">No dependencies</span>';
        return;
    }

    container.innerHTML = editDeps.map(dep => `
        <span class="dep-chip" data-dep-id="${dep.id}" data-upstream-id="${dep.upstream_task_id}">
            ${escapeHtml(dep.upstream_title || dep.upstream_task_id)}
            <button class="dep-chip-remove" onclick="removeDep('${dep.id}', '${dep.upstream_task_id}')">&times;</button>
        </span>
    `).join('');
}

function populateDepSelect() {
    const select = document.getElementById('dep-select');
    const currentDeps = new Set(editDeps.map(d => d.upstream_task_id));

    select.innerHTML = '<option value="">Add prerequisite...</option>';
    for (const task of tasks) {
        if (task.id === currentEditTaskId) continue;
        if (currentDeps.has(task.id)) continue;
        select.innerHTML += `<option value="${task.id}">${escapeHtml(task.title)}</option>`;
    }
}

async function addDependencyFromSelect() {
    const select = document.getElementById('dep-select');
    const upstreamId = select.value;
    if (!upstreamId) return;

    hideDepError();

    if (!currentEditTaskId) {
        // Task not yet created — store locally
        const upTask = tasks.find(t => t.id === upstreamId);
        editDeps.push({
            id: 'pending-' + upstreamId,
            upstream_task_id: upstreamId,
            upstream_title: upTask ? upTask.title : upstreamId,
        });
        renderDepsInModal();
        populateDepSelect();
        return;
    }

    try {
        const dep = await api.createDependency(upstreamId, currentEditTaskId);
        editDeps.push({
            id: dep.id,
            upstream_task_id: dep.upstream_task_id,
            upstream_title: dep.upstream_title,
        });
        renderDepsInModal();
        populateDepSelect();
        hideDepError();
        showToast('Dependency added', 'success');

        // Refresh to update statuses
        [tasks, dependencies] = await Promise.all([api.getTasks(), api.getDependencies()]);
        renderBoard();
    } catch (err) {
        showToast(err.message, 'error');
        showDepError(err.message);
    }
}

async function removeDep(depId, upstreamId) {
    hideDepError();
    if (depId.startsWith('pending-')) {
        editDeps = editDeps.filter(d => d.upstream_task_id !== upstreamId);
        renderDepsInModal();
        populateDepSelect();
        return;
    }

    try {
        await api.deleteDependency(depId);
        editDeps = editDeps.filter(d => d.id !== depId);
        renderDepsInModal();
        populateDepSelect();
        showToast('Dependency removed', 'success');

        [tasks, dependencies] = await Promise.all([api.getTasks(), api.getDependencies()]);
        renderBoard();
    } catch (err) {
        showToast(err.message, 'error');
        showDepError(err.message);
    }
}

async function saveTask() {
    const title = document.getElementById('input-title').value.trim();
    if (!title) {
        showToast('Title is required', 'warning');
        return;
    }

    const data = {
        title,
        description: document.getElementById('input-desc').value.trim(),
        start_date: document.getElementById('input-start').value || null,
        end_date: document.getElementById('input-end').value || null,
        duration_days: parseInt(document.getElementById('input-duration').value) || 1,
    };

    try {
        if (currentEditTaskId) {
            await api.updateTask(currentEditTaskId, data);
            showToast('Task updated', 'success');
        } else {
            const created = await api.createTask({ ...data, column: 'backlog' });

            // Add any pending dependencies
            for (const dep of editDeps) {
                if (dep.id.startsWith('pending-')) {
                    try {
                        await api.createDependency(dep.upstream_task_id, created.id);
                    } catch (e) {
                        showToast(`Dependency error: ${e.message}`, 'warning');
                    }
                }
            }
            showToast('Task created', 'success');
        }

        closeModal();
        await refreshAll();
    } catch (err) {
        showToast('Save failed: ' + err.message, 'error');
    }
}

async function deleteCurrentTask() {
    if (!currentEditTaskId) return;
    if (!confirm('Delete this task? All its dependencies will also be removed.')) return;

    try {
        await api.deleteTask(currentEditTaskId);
        showToast('Task deleted', 'success');
        closeModal();
        await refreshAll();
    } catch (err) {
        showToast('Delete failed: ' + err.message, 'error');
    }
}

// ── AI Suggestions ────────────────────────────
async function fetchAISuggestions() {
    if (!currentEditTaskId) {
        showToast('Save the task first to get AI suggestions', 'info');
        return;
    }

    const btn = document.getElementById('btn-ai-suggest');
    btn.disabled = true;
    btn.textContent = '⏳ Analyzing...';

    try {
        const result = await api.suggestDependencies(currentEditTaskId);
        const container = document.getElementById('ai-suggestions');
        const list = document.getElementById('ai-list');
        const model = document.getElementById('ai-model');

        model.textContent = result.model_used || '';

        if (result.suggestions.length === 0) {
            list.innerHTML = '<div class="ai-suggestion-item"><span class="ai-suggestion-info"><span class="ai-suggestion-title">No suggestions</span><span class="ai-suggestion-reason">The AI couldn\'t find logical dependencies for this task.</span></span></div>';
        } else {
            list.innerHTML = result.suggestions.map(s => {
                const confClass = s.confidence >= 80 ? 'high' : s.confidence >= 60 ? 'medium' : 'low';
                return `
                    <div class="ai-suggestion-item" data-upstream-id="${s.upstream_task_id}">
                        <div class="ai-suggestion-info">
                            <div class="ai-suggestion-title">${escapeHtml(s.upstream_task_title)}</div>
                            <div class="ai-suggestion-reason">${escapeHtml(s.reasoning)}</div>
                        </div>
                        <div class="ai-confidence">
                            <span>${s.confidence}%</span>
                            <div class="ai-confidence-bar">
                                <div class="ai-confidence-fill ${confClass}" style="width:${s.confidence}%"></div>
                            </div>
                        </div>
                        <div class="ai-suggestion-actions">
                            <button class="ai-accept" onclick="acceptAISuggestion('${s.upstream_task_id}')" title="Accept">✓</button>
                            <button class="ai-reject" onclick="rejectAISuggestion(this)" title="Reject">✕</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        container.style.display = 'block';
    } catch (err) {
        showToast('AI suggestion failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '✨ AI Suggest Dependencies';
    }
}

async function acceptAISuggestion(upstreamId) {
    if (!currentEditTaskId) return;

    try {
        const dep = await api.createDependency(upstreamId, currentEditTaskId, 'ai_suggested');
        editDeps.push({
            id: dep.id,
            upstream_task_id: dep.upstream_task_id,
            upstream_title: dep.upstream_title,
        });
        renderDepsInModal();
        populateDepSelect();
        showToast('AI suggestion accepted ✓', 'success');

        // Remove from suggestions list
        const items = document.querySelectorAll('.ai-suggestion-item');
        items.forEach(item => {
            if (item.dataset.upstreamId === upstreamId) {
                item.style.opacity = '0.3';
                item.style.pointerEvents = 'none';
            }
        });

        [tasks, dependencies] = await Promise.all([api.getTasks(), api.getDependencies()]);
        renderBoard();
    } catch (err) {
        showToast(err.message, 'error');
        showDepError(err.message);
    }
}

function rejectAISuggestion(btn) {
    const item = btn.closest('.ai-suggestion-item');
    item.style.opacity = '0.2';
    item.style.pointerEvents = 'none';
}

// ── What-If Simulator ─────────────────────────
function setupWhatIf() {
    const btn = document.getElementById('btn-what-if');
    const overlay = document.getElementById('whatif-overlay');
    const closeBtn = document.getElementById('whatif-close');
    const cancelBtn = document.getElementById('btn-whatif-cancel');
    const runBtn = document.getElementById('btn-whatif-run');
    const applyBtn = document.getElementById('btn-whatif-apply');

    btn.addEventListener('click', () => {
        populateWhatIfSelect();
        document.getElementById('whatif-results').innerHTML =
            '<div class="whatif-empty">Select a task and adjust its end date to preview the cascade effect.</div>';
        applyBtn.style.display = 'none';
        overlay.style.display = 'flex';
    });

    closeBtn.addEventListener('click', () => overlay.style.display = 'none');
    cancelBtn.addEventListener('click', () => overlay.style.display = 'none');
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.style.display = 'none';
    });

    runBtn.addEventListener('click', runWhatIf);
    applyBtn.addEventListener('click', applyWhatIf);
}

function populateWhatIfSelect() {
    const select = document.getElementById('whatif-task');
    select.innerHTML = '<option value="">Choose a task...</option>';
    for (const task of tasks) {
        if (task.end_date) {
            select.innerHTML += `<option value="${task.id}" data-end="${task.end_date}">${escapeHtml(task.title)}</option>`;
        }
    }

    select.addEventListener('change', () => {
        const opt = select.options[select.selectedIndex];
        if (opt.dataset.end) {
            document.getElementById('whatif-end').value = opt.dataset.end;
        }
    });
}

async function runWhatIf() {
    const taskId = document.getElementById('whatif-task').value;
    const newEnd = document.getElementById('whatif-end').value;
    if (!taskId || !newEnd) {
        showToast('Select a task and set a new end date', 'warning');
        return;
    }

    try {
        whatIfData = await api.whatIf(taskId, newEnd);
        const container = document.getElementById('whatif-results');

        if (whatIfData.length === 0) {
            container.innerHTML = '<div class="whatif-empty">No downstream tasks would be affected by this change.</div>';
            document.getElementById('btn-whatif-apply').style.display = 'none';
            return;
        }

        container.innerHTML = whatIfData.map(item => {
            const shiftClass = item.shift_days > 0 ? 'positive' : 'negative';
            const shiftSign = item.shift_days > 0 ? '+' : '';
            return `
                <div class="whatif-item shift-${shiftClass}">
                    <span class="whatif-task-name">${escapeHtml(item.title)}</span>
                    <div class="whatif-dates">
                        <span>${formatDate(item.old_end)}</span>
                        <span class="whatif-arrow">→</span>
                        <span>${formatDate(item.new_end)}</span>
                    </div>
                    <span class="whatif-shift ${shiftClass}">${shiftSign}${item.shift_days}d</span>
                </div>
            `;
        }).join('');

        document.getElementById('btn-whatif-apply').style.display = 'inline-flex';
    } catch (err) {
        showToast('Simulation failed: ' + err.message, 'error');
    }
}

async function applyWhatIf() {
    const taskId = document.getElementById('whatif-task').value;
    const newEnd = document.getElementById('whatif-end').value;
    if (!taskId || !newEnd) return;

    try {
        // Apply the date change (propagation happens server-side)
        await api.updateTask(taskId, { end_date: newEnd });
        showToast('Schedule change applied with propagation', 'success');
        document.getElementById('whatif-overlay').style.display = 'none';
        await refreshAll();
    } catch (err) {
        showToast('Apply failed: ' + err.message, 'error');
    }
}

// ── Critical Path View ────────────────────────
function renderCriticalPathView(cp) {
    const container = document.getElementById('critical-path-container');

    if (!cp.path || cp.path.length === 0) {
        container.innerHTML = '<div class="cp-empty">No critical path found. Add dependencies to see the longest chain.</div>';
        return;
    }

    let html = '<div class="cp-chain">';
    cp.path.forEach((node, i) => {
        html += `
            <div class="cp-node">
                <div class="cp-node-title">${escapeHtml(node.title)}</div>
                <div class="cp-node-duration">${node.duration_days} day${node.duration_days !== 1 ? 's' : ''}</div>
                <div class="cp-node-status">${node.column.replace('_', ' ')}</div>
            </div>
        `;
        if (i < cp.path.length - 1) {
            html += '<div class="cp-arrow">→</div>';
        }
    });
    html += '</div>';
    html += `<div class="cp-total">Total Critical Path Duration: <strong>${cp.total_duration_days} days</strong></div>`;

    container.innerHTML = html;
}

// ── Toast Notifications ───────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-msg">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Utilities ─────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ── Theme Management ──────────────────────────
function setupTheme() {
    const toggleBtn = document.getElementById('btn-theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('taskflow_theme', theme);
        if (theme === 'light') {
            if (themeIcon) themeIcon.textContent = 'dark_mode';
            if (themeText) themeText.textContent = 'Dark';
            if (toggleBtn) {
                toggleBtn.title = 'Switch to Dark Mode';
                toggleBtn.setAttribute('aria-label', 'Switch to Dark Mode');
            }
        } else {
            if (themeIcon) themeIcon.textContent = 'light_mode';
            if (themeText) themeText.textContent = 'Light';
            if (toggleBtn) {
                toggleBtn.title = 'Switch to Light Mode';
                toggleBtn.setAttribute('aria-label', 'Switch to Light Mode');
            }
        }
        if (dagCanvas && typeof dagCanvas.updateTheme === 'function') {
            dagCanvas.updateTheme(theme);
        }
    }

    const saved = localStorage.getItem('taskflow_theme');
    const systemPrefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    const initialTheme = saved || document.documentElement.getAttribute('data-theme') || (systemPrefersLight ? 'light' : 'dark');
    applyTheme(initialTheme);

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'light' ? 'dark' : 'light';
            applyTheme(next);
        });
    }

    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('taskflow_theme')) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
}
