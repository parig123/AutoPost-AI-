// ═══════════════════════════════════════════
// AutoPost AI – Dashboard Logic
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initDashboard();
    document.getElementById('t-refresh-btn')?.addEventListener('click', () => fetchTrends(true));
});

// ── Live clock ──────────────────────────────
function initClock() {
    const el = document.getElementById('t-clock');
    function tick() {
        if (!el) return;
        const now = new Date();
        el.textContent = now.toLocaleTimeString('en-IN', { hour12: true }) +
                         ' · ' + now.toLocaleDateString('en-IN', { weekday:'short', day:'2-digit', month:'short', year:'numeric' });
    }
    tick();
    setInterval(tick, 1000);
}

// ── Bootstrap all data ───────────────────────
async function initDashboard() {
    try {
        await Promise.all([fetchUser(), fetchStats(), fetchActivity(), fetchTrends(false)]);
    } catch (e) {
        console.error('Dashboard init error:', e);
    }
}

// ── User greeting ─────────────────────────────
async function fetchUser() {
    try {
        const data = await API.getCurrentUser();
        if (data && data.active_account) {
            const name = data.active_account.name.split(' ')[0];
            const el = document.getElementById('t-username');
            if (el) el.textContent = name;
        }
    } catch (_) {}
}

// ── Stats ─────────────────────────────────────
async function fetchStats() {
    try {
        const s = await API.getStats();
        if (!s) return;

        setText('t-scheduled', s.scheduled ?? 0);
        setText('t-pending',   s.pending_approval ?? 0);
        setText('t-published', s.published_30d ?? 0);

        const rate = s.success_rate ?? 0;
        const rateEl = document.getElementById('t-rate');
        if (rateEl) {
            rateEl.textContent = rate + '%';
            rateEl.className = 'text-3xl font-bold mt-2 ' +
                (rate >= 80 ? 'text-emerald-500' : rate >= 50 ? 'text-amber-500' : 'text-rose-500');
        }

        // Animate bars after paint
        const max = Math.max(s.scheduled, s.pending_approval, s.published_30d, 1);
        setTimeout(() => {
            setBar('t-bar-sched', (s.scheduled          / max) * 100);
            setBar('t-bar-pend',  (s.pending_approval   / max) * 100);
            setBar('t-bar-pub',   (s.published_30d      / max) * 100);
            setBar('t-bar-rate',  rate);
        }, 120);

    } catch (e) { console.error('fetchStats:', e); }
}

// ── Activity (recent posts) ────────────────────
async function fetchActivity() {
    const container = document.getElementById('t-topics-list');
    if (!container) return;

    try {
        const items = await API.getRecentActivity();

        if (!items || items.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center py-12 text-center px-6">
                    <div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mb-4">
                        <i class="fa-solid fa-ghost text-2xl text-slate-400"></i>
                    </div>
                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400">No posts yet.</p>
                    <a href="/create" class="mt-3 text-xs text-primary font-semibold hover:underline">Create your first post →</a>
                </div>`;
            return;
        }

        container.innerHTML = items.map(item => {
            const cfg = statusConfig(item.status);
            const rel = relativeTime(new Date(item.updated_at));
            const topic = (item.topic || 'Untitled Post').substring(0, 55);

            const failBtns = item.status === 'Failed' ? `
                <button onclick="retryPost(${item.id}, this)"
                    class="flex-shrink-0 text-xs font-semibold text-emerald-600 hover:text-emerald-700 transition-colors px-2.5 py-1 rounded-lg border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-50 dark:hover:bg-emerald-900/20">
                    <i class="fa-solid fa-rotate-right mr-1"></i>Retry
                </button>
                ${item.error_message ? `
                <button onclick="showError(${JSON.stringify(item.error_message || '')})"
                    class="flex-shrink-0 text-xs font-semibold text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700">
                    <i class="fa-solid fa-circle-info mr-1"></i>Error
                </button>` : ''}
            ` : '';

            return `
            <div class="topic-row flex items-center gap-4 px-6 py-3.5">
                <div class="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm" style="background:${cfg.bg}">
                    <i class="${cfg.icon}" style="color:${cfg.color}"></i>
                </div>
                <span class="flex-1 text-sm font-medium text-slate-700 dark:text-slate-200 truncate" title="${item.topic || ''}">${topic}</span>
                <span class="flex-shrink-0 text-xs font-semibold uppercase tracking-wide" style="color:${cfg.color}">${item.status}</span>
                <span class="flex-shrink-0 text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">· ${rel}</span>
                ${failBtns}
            </div>`;
        }).join('');

    } catch (e) {
        container.innerHTML = `<div class="px-6 py-6 text-sm text-rose-500">Failed to load activity.</div>`;
    }
}

// ── AI/ML Trends ──────────────────────────────
async function fetchTrends(forceRefresh = false) {
    const grid = document.getElementById('t-trends-grid');
    if (!grid) return;

    // Skeleton
    grid.innerHTML = Array(4).fill(
        `<div class="skel rounded-xl" style="height:96px;"></div>`
    ).join('');

    try {
        let trends;
        if (forceRefresh) {
            const res = await fetch('/api/analytics/trends/refresh', { method: 'POST' });
            if (!res.ok) throw new Error('refresh failed');
            trends = await res.json();
        } else {
            const res = await fetch('/api/analytics/trends');
            if (res.status === 401) {
                grid.innerHTML = `<div class="col-span-2 text-sm text-slate-400 py-8 text-center">Log in to see trends.</div>`;
                return;
            }
            trends = await res.json();
        }

        if (!trends || trends.length === 0) throw new Error('empty');

        const tagColors = {
            LLM:        '#8b5cf6', OpenAI:  '#10a37f', Google:  '#4285f4',
            Meta:       '#0082fb', Market:  '#f59e0b', Research:'#6366f1',
            Hardware:   '#ef4444', 'Open Source':'#3fb950', Startup:'#ec4899',
            Enterprise: '#0a66c2',
        };

        grid.innerHTML = trends.map(t => {
            const tagColor = tagColors[t.tag] || '#64748b';
            return `
            <div class="trend-card bg-slate-50 dark:bg-slate-700/50 border border-slate-100 dark:border-slate-700 rounded-xl p-4">
                <div class="flex items-start justify-between gap-2 mb-2">
                    <span class="text-2xl leading-none">${t.emoji || '📡'}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                          style="background:${tagColor}22; color:${tagColor}">
                        ${t.tag || 'AI'}
                    </span>
                </div>
                <p class="text-sm font-semibold text-slate-800 dark:text-slate-100 leading-snug mb-1">${t.title || ''}</p>
                <p class="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">${t.description || ''}</p>
            </div>`;
        }).join('');

    } catch (e) {
        grid.innerHTML = `
            <div class="col-span-2 text-center py-6">
                <p class="text-sm text-slate-400 mb-3">Could not load trends.</p>
                <button onclick="fetchTrends(false)"
                    class="text-xs font-semibold text-primary hover:underline">
                    Try again →
                </button>
            </div>`;
    }
}

// ── Retry failed post ─────────────────────────
window.retryPost = async function(id, btn) {
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>Posting…';
    btn.disabled = true;
    try {
        const res = await fetch(`/api/posts/${id}/publish`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            if (typeof showToast === 'function') showToast('Post published successfully!', 'success');
            await Promise.all([fetchActivity(), fetchStats()]);
        } else {
            if (typeof showToast === 'function') showToast(data.error || 'Publish failed', 'error');
            btn.innerHTML = orig; btn.disabled = false;
        }
    } catch (_) {
        if (typeof showToast === 'function') showToast('Network error', 'error');
        btn.innerHTML = orig; btn.disabled = false;
    }
};

// ── Error modal ────────────────────────────────
window.showError = function(msg) {
    document.getElementById('t-error-text').textContent = msg || 'No error details available.';
    document.getElementById('t-error-modal').classList.remove('hidden');
};

// ── Helpers ───────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function setBar(id, pct) {
    const el = document.getElementById(id);
    if (el) el.style.width = Math.min(Math.max(pct, 0), 100) + '%';
}

function relativeTime(date) {
    const diff = Math.floor((Date.now() - date) / 1000);
    if (diff < 60)     return 'just now';
    if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return date.toLocaleDateString();
}

function statusConfig(status) {
    const map = {
        'Published':        { icon: 'fa-solid fa-check',               color: '#10b981', bg: '#f0fdf4' },
        'Scheduled':        { icon: 'fa-solid fa-calendar-days',       color: '#0a66c2', bg: '#eff6ff' },
        'Pending Approval': { icon: 'fa-solid fa-hourglass-half',      color: '#f59e0b', bg: '#fffbeb' },
        'Failed':           { icon: 'fa-solid fa-triangle-exclamation',color: '#ef4444', bg: '#fff1f2' },
        'Draft':            { icon: 'fa-solid fa-file-pen',            color: '#94a3b8', bg: '#f8fafc' },
    };
    return map[status] || map['Draft'];
}

window.getRelativeTime = relativeTime;
