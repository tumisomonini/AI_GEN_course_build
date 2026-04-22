/**
 * Shared Utilities - Error handling, notifications, API helpers
 */

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-xl z-50 transition-all transform translate-x-full ${
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'success' ? 'bg-emerald-500 text-white' :
        type === 'warning' ? 'bg-amber-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Animate in
    requestAnimationFrame(() => notification.classList.remove('translate-x-full'));

    // Auto-remove
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// API Helper with retry
async function apiCall(endpoint, options = {}, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            const res = await fetch(endpoint, {
                ...options,
                headers: { ...options.headers, 'Content-Type': 'application/json' }
            });
            
            if (res.ok) return await res.json();
            
            // Auto-retry on specific errors
            if (res.status === 503 && i < retries - 1) {
                await new Promise(r => setTimeout(r, 1000 * (i + 1)));
                continue;
            }
            
            const error = await res.json().catch(() => ({ message: res.statusText }));
            throw new Error(error.message || `HTTP ${res.status}`);
        } catch (error) {
            if (i === retries - 1) {
                showNotification(`API Error: ${error.message}`, 'error');
                throw error;
            }
        }
    }
}

// SSE Streaming Helper
function startSSEStream(url, onMessage, onError) {
    const eventSource = new EventSource(url);
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
        } catch (e) {
            console.warn('SSE parse error:', e);
        }
    };
    
    eventSource.onerror = () => {
        onError?.();
        eventSource.close();
    };
    
    return () => eventSource.close();
}

// Mobile Menu Toggle
function toggleMobileMenu() {
    const drawer = document.getElementById('mobile-drawer');
    drawer.classList.toggle('translate-x-0');
}

// Health Check Badge Updater
async function updateHealthBadges() {
    try {
        const res = await fetch('/health');
        const data = await res.json();
        
        ['pg', 'neo', 'astra'].forEach(db => {
            const badge = document.getElementById(`health-${db}`);
            if (badge) {
                const status = data.dbs[db]?.status || 'down';
                badge.className = `health-badge ${status === 'ready' ? 'bg-emerald-500' : 'bg-red-500'}`;
            }
        });
    } catch (e) {
        console.warn('Health check failed');
    }
}

