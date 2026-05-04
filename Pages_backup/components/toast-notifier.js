/**
 * Toast Notifier - Stacking, dismissible notifications
 * Resolves error handling feedback
 */

class ToastNotifier {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            display: flex; flex-direction: column; gap: 12px; max-width: 400px;
            font-family: inherit;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            padding: 16px 20px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            transform: translateX(100%); opacity: 0; transition: all 0.3s ease;
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
            min-height: 60px; display: flex; align-items: center; gap: 12px;
            font-size: 14px; max-width: 400px; word-break: break-word;
        `;

        const colors = {
            error: '#ef4444', success: '#10b981', warning: ' #f59e0b', info: '#3b82f6'
        };
        const icon = { error: '🚫', success: '✅', warning: '⚠️', info: 'ℹ️' }[type];

        toast.innerHTML = `
            <span style="font-size: 18px; font-weight: bold;">${icon}</span>
            <div style="flex: 1; line-height: 1.4;">
                <strong>${type.toUpperCase()}</strong>
                <div style="font-weight: 500; margin-top: 2px;">${this.escapeHtml(message)}</div>
            </div>
            <button onclick="this.parentElement.remove()" style="
                background: none; border: none; color: inherit; font-size: 18px; 
                cursor: pointer; padding: 0; width: 24px; height: 24px; display: flex;
                align-items: center; justify-content: center; opacity: 0.7;
                &:hover { opacity: 1; }
            ">×</button>
        `;

        toast.style.background = `linear-gradient(135deg, ${colors[type]}20, ${colors[type]}10)`;
        toast.style.color = colors[type];
        toast.style.borderLeft = `4px solid ${colors[type]}`;

        // Animate in
        this.container.appendChild(toast);
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });

        // Auto-remove
        setTimeout(() => this.remove(toast), duration);

        return toast;
    }

    remove(toast) {
        toast.style.transform = 'translateX(100%)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global instance + API integration
window.toastNotifier = new ToastNotifier();

// Enhance utils.js apiCall() to use toasts
if (typeof apiCall === 'function') {
    const originalApiCall = apiCall;
    window.apiCall = async (endpoint, options = {}, retries = 3) => {
        try {
            return await originalApiCall(endpoint, options, retries);
        } catch (error) {
            window.toastNotifier.show(`API Error: ${error.message}`, 'error', 8000);
            throw error;
        }
    };
}

// Mobile: Auto-add touch-friendly classes
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input, button, select').forEach(el => {
        el.classList.add('min-h-[48px]', 'px-4', 'touch-manipulation');
    });
});

// Export for utils.js compatibility
window.showToast = (message, type) => window.toastNotifier.show(message, type);
