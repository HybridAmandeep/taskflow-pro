/**
 * TaskFlow Pro — DAG Canvas Renderer
 * Draws the dependency graph on a <canvas> element.
 */

class DAGCanvas {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.nodes = [];
        this.edges = [];
        this.nodePositions = {};
        this.hoveredNode = null;

        this.updateTheme(document.documentElement.getAttribute('data-theme') || 'dark');

        this._setupResize();
        this._setupMouse();
    }

    updateTheme(theme) {
        if (theme === 'light') {
            this.colors = {
                backlog: '#4F46E5',
                in_progress: '#D97706',
                review: '#7C3AED',
                done: '#059669',
                edge: '#CBD5E1',
                edgeArrow: '#64748B',
                criticalEdge: '#D97706',
                text: '#0F172A',
                textMuted: '#64748B',
                nodeBg: '#FFFFFF',
                nodeBorder: '#CBD5E1',
                hoverBorder: '#4F46E5',
            };
        } else {
            this.colors = {
                backlog: '#6366F1',
                in_progress: '#F59E0B',
                review: '#A855F7',
                done: '#10B981',
                edge: '#334155',
                edgeArrow: '#64748B',
                criticalEdge: '#F59E0B',
                text: '#F8FAFC',
                textMuted: '#94A3B8',
                nodeBg: '#131D31',
                nodeBorder: '#334155',
                hoverBorder: '#6366F1',
            };
        }
        if (this.nodes && this.nodes.length) {
            this.render();
        }
    }

    _setupResize() {
        const resize = () => {
            const rect = this.canvas.parentElement.getBoundingClientRect();
            this.canvas.width = rect.width;
            this.canvas.height = rect.height;
            if (this.nodes.length) this.render();
        };
        window.addEventListener('resize', resize);
        resize();
    }

    _setupMouse() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            let found = null;
            for (const node of this.nodes) {
                const pos = this.nodePositions[node.id];
                if (!pos) continue;
                const dx = x - pos.x;
                const dy = y - pos.y;
                if (Math.abs(dx) < 80 && Math.abs(dy) < 25) {
                    found = node.id;
                    break;
                }
            }

            if (found !== this.hoveredNode) {
                this.hoveredNode = found;
                this.canvas.style.cursor = found ? 'pointer' : 'default';
                this.render();
            }
        });
    }

    setData(tasks, dependencies, criticalPathIds = []) {
        this.nodes = tasks;
        this.edges = dependencies;
        this.criticalPathSet = new Set(criticalPathIds);
        this._computeLayout();
        this.render();
    }

    _computeLayout() {
        // Group by column, then layout in layers
        const columns = { backlog: [], in_progress: [], review: [], done: [] };
        for (const node of this.nodes) {
            const col = node.column || 'backlog';
            if (columns[col]) columns[col].push(node);
        }

        const w = this.canvas.width;
        const h = this.canvas.height;
        const colNames = ['backlog', 'in_progress', 'review', 'done'];
        const colWidth = w / colNames.length;

        this.nodePositions = {};
        for (let ci = 0; ci < colNames.length; ci++) {
            const col = colNames[ci];
            const tasks = columns[col];
            const colX = colWidth * ci + colWidth / 2;

            for (let ti = 0; ti < tasks.length; ti++) {
                const ySpacing = Math.min(80, (h - 100) / (tasks.length + 1));
                const yStart = 60 + (h - 120 - ySpacing * tasks.length) / 2;
                this.nodePositions[tasks[ti].id] = {
                    x: colX,
                    y: yStart + ti * ySpacing + ySpacing / 2,
                };
            }
        }
    }

    render() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Draw column labels
        const colNames = ['Backlog', 'In Progress', 'Review', 'Done'];
        const colWidth = w / 4;
        ctx.font = '600 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        colNames.forEach((name, i) => {
            ctx.fillStyle = this.colors.textMuted;
            ctx.fillText(name.toUpperCase(), colWidth * i + colWidth / 2, 30);
        });

        // Draw edges
        for (const edge of this.edges) {
            const from = this.nodePositions[edge.upstream_task_id];
            const to = this.nodePositions[edge.downstream_task_id];
            if (!from || !to) continue;

            const isCritical =
                this.criticalPathSet.has(edge.upstream_task_id) &&
                this.criticalPathSet.has(edge.downstream_task_id);

            const isHighlighted =
                this.hoveredNode === edge.upstream_task_id ||
                this.hoveredNode === edge.downstream_task_id;

            ctx.beginPath();
            ctx.moveTo(from.x + 75, from.y);

            // Bezier curve for smooth edges
            const midX = (from.x + 75 + to.x - 75) / 2;
            ctx.bezierCurveTo(midX, from.y, midX, to.y, to.x - 75, to.y);

            ctx.strokeStyle = isCritical
                ? this.colors.criticalEdge
                : isHighlighted
                    ? this.colors.hoverBorder
                    : this.colors.edge;
            ctx.lineWidth = isCritical ? 2.5 : isHighlighted ? 2 : 1.5;
            ctx.stroke();

            // Arrowhead
            const angle = Math.atan2(to.y - from.y, to.x - 75 - from.x - 75);
            const ax = to.x - 75;
            const ay = to.y;
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(ax - 8 * Math.cos(angle - 0.4), ay - 8 * Math.sin(angle - 0.4));
            ctx.lineTo(ax - 8 * Math.cos(angle + 0.4), ay - 8 * Math.sin(angle + 0.4));
            ctx.closePath();
            ctx.fillStyle = isCritical ? this.colors.criticalEdge : this.colors.edgeArrow;
            ctx.fill();
        }

        // Draw nodes
        for (const node of this.nodes) {
            const pos = this.nodePositions[node.id];
            if (!pos) continue;

            const isHovered = this.hoveredNode === node.id;
            const isCritical = this.criticalPathSet.has(node.id);
            const nodeW = 150;
            const nodeH = 44;

            // Node background
            ctx.fillStyle = this.colors.nodeBg;
            ctx.strokeStyle = isCritical
                ? 'rgba(245, 158, 11, 0.5)'
                : isHovered
                    ? this.colors.hoverBorder
                    : this.colors.nodeBorder;
            ctx.lineWidth = isHovered || isCritical ? 2 : 1;

            this._roundRect(ctx, pos.x - nodeW / 2, pos.y - nodeH / 2, nodeW, nodeH, 8);
            ctx.fill();
            ctx.stroke();

            // Color accent bar on left
            const accentColor = this.colors[node.column] || this.colors.backlog;
            ctx.fillStyle = accentColor;
            ctx.fillRect(pos.x - nodeW / 2, pos.y - nodeH / 2 + 4, 3, nodeH - 8);

            // Title
            ctx.fillStyle = this.colors.text;
            ctx.font = '600 11px Inter, sans-serif';
            ctx.textAlign = 'center';
            const title = node.title.length > 18
                ? node.title.substring(0, 16) + '…'
                : node.title;
            ctx.fillText(title, pos.x + 2, pos.y - 2);

            // Status
            const status = node.status || 'ready';
            ctx.font = '500 9px Inter, sans-serif';
            ctx.fillStyle = status === 'blocked' ? '#f43f5e' : '#10b981';
            ctx.fillText(status.toUpperCase(), pos.x + 2, pos.y + 12);
        }
    }

    _roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }
}
