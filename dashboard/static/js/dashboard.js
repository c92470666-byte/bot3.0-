/**
 * PolyBot Dashboard - JavaScript principal
 * Funciones compartidas entre páginas
 */

// ==========================================
// API Helper
// ==========================================
class API {
    static async get(url) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (e) {
            console.error(`API GET ${url}:`, e);
            return null;
        }
    }

    static async post(url, data = {}) {
        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            return await resp.json();
        } catch (e) {
            console.error(`API POST ${url}:`, e);
            return null;
        }
    }
}

// ==========================================
// Format Helpers
// ==========================================
function formatCurrency(amount, decimals = 2) {
    if (amount === null || amount === undefined) return '-';
    const sign = amount >= 0 ? '' : '-';
    return `${sign}$${Math.abs(amount).toFixed(decimals)}`;
}

function formatPnL(amount, decimals = 2) {
    if (amount === null || amount === undefined) return '-';
    const sign = amount >= 0 ? '+' : '';
    return `${sign}$${amount.toFixed(decimals)}`;
}

function formatPercent(value, decimals = 2) {
    if (value === null || value === undefined) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(decimals)}%`;
}

function formatDate(isoString) {
    if (!isoString) return '-';
    const d = new Date(isoString);
    return d.toLocaleString('es', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatTime(isoString) {
    if (!isoString) return '-';
    return new Date(isoString).toLocaleTimeString('es');
}

// ==========================================
// Toast Notification System
// ==========================================
class Toast {
    static show(message, type = 'info', duration = 4000) {
        const colors = {
            success: 'bg-green-900 border-green-700 text-green-300',
            error: 'bg-red-900 border-red-700 text-red-300',
            info: 'bg-blue-900 border-blue-700 text-blue-300',
            warning: 'bg-yellow-900 border-yellow-700 text-yellow-300',
        };

        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-times-circle',
            info: 'fas fa-info-circle',
            warning: 'fas fa-exclamation-triangle',
        };

        const container = document.getElementById('toast-container') || (() => {
            const div = document.createElement('div');
            div.id = 'toast-container';
            div.className = 'fixed top-20 right-4 z-50 space-y-2';
            document.body.appendChild(div);
            return div;
        })();

        const toast = document.createElement('div');
        toast.className = `px-5 py-3 rounded-xl border shadow-2xl ${colors[type] || colors.info} transform translate-x-full transition-transform duration-300 flex items-center space-x-3`;
        toast.innerHTML = `
            <i class="${icons[type] || icons.info}"></i>
            <span class="text-sm">${message}</span>
        `;

        container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-full');
        });

        // Remove
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => {
                toast.remove();
                if (container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }, duration);
    }

    static success(msg) { Toast.show(msg, 'success'); }
    static error(msg) { Toast.show(msg, 'error'); }
    static info(msg) { Toast.show(msg, 'info'); }
    static warning(msg) { Toast.show(msg, 'warning'); }
}

// ==========================================
// Auto-refresh Manager
// ==========================================
class AutoRefresh {
    constructor(callback, intervalMs = 10000) {
        this.callback = callback;
        this.intervalMs = intervalMs;
        this._timer = null;
        this._active = false;
    }

    start() {
        if (this._active) return;
        this._active = true;
        this.callback();
        this._timer = setInterval(() => this.callback(), this.intervalMs);
    }

    stop() {
        this._active = false;
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }
    }

    setInterval(ms) {
        this.intervalMs = ms;
        if (this._active) {
            this.stop();
            this.start();
        }
    }
}

// ==========================================
// Visibility API - pause when tab hidden
// ==========================================
document.addEventListener('visibilitychange', () => {
    const event = new CustomEvent('tabVisibilityChange', {
        detail: { visible: !document.hidden }
    });
    document.dispatchEvent(event);
});
