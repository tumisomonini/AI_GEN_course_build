/**
 * Live Logger - Unified SSE + Console for ALL interfaces
 * Handles real-time agent logs, health updates, session resume
 * Usage: window.liveLogger.init('#console-output', courseId)
 */

class LiveLogger {
    constructor() {
        this.eventSource = null;
        this.courseId = null;
        this.consoleEl = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnects = 5;
        this.reconnectDelay = 2000;
    }

    init(consoleSelector, courseId = null) {
        this.courseId = courseId || window.sessionManager?.courseId;
        this.consoleEl = typeof consoleSelector === 'string' 
            ? document.querySelector(consoleSelector) 
            : consoleSelector;
        
        if (!this.consoleEl) {
            console.error('LiveLogger: No console element found');
            return;
        }

        this.renderWelcome();
        this.connect();
        
        // Auto-resume if session exists
        if (window.sessionManager?.courseId && !courseId) {
            this.showResumeAlert();
        }

        // Listen for session changes
        window.sessionManager?.on('session_ready', () => {
            if (window.sessionManager.courseId !== this.courseId) {
                this.courseId = window.sessionManager.courseId;
                this.reconnect();
            }
        });
    }

    connect() {
        if (!this.courseId) return;
        
        try {
            this.eventSource = new EventSource(`/courses/${this.courseId}/events`);
            this.eventSource.onmessage = (event) => this.handleMessage(event);
            this.eventSource.onerror = () => this.handleError();
            
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.logSystem('SSE Connected', 'info');
            this.updateHealthBadges();
        } catch (e) {
            this.handleError(e);
        }
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'log') {
                this.log(data.agent || 'System', data.message, data.level || 'info');
                this.updateStepper(data.status);
            } else if (data.type === 'health') {
                this.updateHealthBadges(data.health);
            } else if (data.type === 'done') {
                this.logSystem(`Workflow ${data.status}`, 'success');
                if (data.status === 'completed') {
                    this.showCompleteUI(data.course_id);
                }
            }
        } catch (e) {
            console.error('SSE parse error:', e, event.data);
        }
    }

    log(agent, message, level = 'info') {
        const div = document.createElement('div');
        div.className = `log-entry flex gap-2 ${this.getLevelClass(level)}`;
        
        const time = new Date().toLocaleTimeString([], { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        
        const agentColor = {
            'Scraper': 'text-blue-400',
            'Planner': 'text-purple-400', 
            'Author': 'text-emerald-400',
            'Reviewer': 'text-amber-400',
            'Assembler': 'text-pink-400',
            'System': 'text-slate-400'
        }[agent] || 'text-slate-400';

        div.innerHTML = `
            <span class="text-slate-600 shrink-0 text-xs">${time}</span>
            <span class="font-bold ${agentColor} shrink-0">[${agent}]</span>
            <span class="flex-1 break-words text-sm">${this.escapeHtml(message)}</span>
        `;
        
        this.consoleEl.appendChild(div);
        this.consoleEl.scrollTop = this.consoleEl.scrollHeight;
    }

    logSystem(message, level = 'info') {
        this.log('System', message, level);
    }

    getLevelClass(level) {
        const classes = {
            'error': 'text-red-400 border-l-4 border-red-400 pl-4',
            'warning': 'text-yellow-400 border-l-4 border-yellow-400 pl-4', 
            'success': 'text-emerald-400',
            'info': ''
        };
        return classes[level] || '';
    }

    handleError(err) {
        if (this.reconnectAttempts >= this.maxReconnects) {
            this.logSystem('Max reconnects reached. Check server.', 'error');
            return;
        }
        
        this.isConnected = false;
        this.reconnectAttempts++;
        
        this.logSystem(`SSE Error (attempt ${this.reconnectAttempts}/${this.maxReconnects}). Reconnecting...`, 'warning');
        
        setTimeout(() => this.reconnect(), this.reconnectDelay * this.reconnectAttempts);
    }

    reconnect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        this.connect();
    }

    updateStepper(status) {
        // Update workflow stepper based on status
        const stepMap = {
            'awaiting_approval': 2,
            'generating_full': 3,
            'completed': 4
        };
        
        const step = stepMap[status];
        if (step && window.stepper) {
            window.stepper.goToStep(step);
        }
    }

    updateHealthBadges(health = null) {
        const fetchHealth = async () => {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                this.setHealthBadge('health-pg', data.dbs?.postgres?.status || 'down');
                this.setHealthBadge('health-neo', data.dbs?.neo4j?.status || 'down');
                this.setHealthBadge('health-astra', data.dbs?.astra?.status || 'down');
            } catch (e) {
                console.error('Health check failed:', e);
            }
        };
        
        fetchHealth();
        setInterval(fetchHealth, 30000); // 30s health refresh
    }

    setHealthBadge(id, status) {
        const badge = document.getElementById(id);
        if (!badge) return;
        
        const dot = badge.querySelector('span') || document.createElement('span');
        dot.className = `w-2 h-2 rounded-full ${
            status === 'ready' || status >= 0 ? 'bg-emerald-500' : 'bg-red-500'
        }`;
        
        if (!badge.querySelector('span')) {
            badge.prepend(dot);
        }
        
        badge.dataset.status = status;
        badge.className = badge.className.replace(/\b(bg-(emerald|red|slate)-500|text-(white|red|slate)-500)\b/g, '');
        badge.classList.add(
            status === 'ready' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
        );
    }

    renderWelcome() {
        this.consoleEl.innerHTML = `
            <div class="text-slate-500 italic text-sm p-4 text-center">
                🔴 Live agent console ready<br>
                <small>Enter course ID or resume session to start streaming</small>
            </div>
        `;
    }

    showResumeAlert() {
        const alert = document.createElement('div');
        alert.id = 'resume-alert';
        alert.className = 'bg-blue-50 border border-blue-200 p-4 rounded-xl flex gap-3 mb-4';
        alert.innerHTML = `
            <i data-lucide="info" class="text-blue-600 w-5 h-5 shrink-0 mt-0.5"></i>
            <div>
                <p class="text-sm font-bold text-blue-900">Active session detected</p>
                <p class="text-xs text-blue-700 mb-2">Resuming course ID: ${this.courseId}</p>
                <button onclick="window.liveLogger.resume()" class="text-xs font-bold text-blue-600 underline hover:text-blue-800">Reconnect Stream</button>
            </div>
        `;
        lucide.createIcons();
        
        const container = this.consoleEl.parentElement;
        if (container && !document.getElementById('resume-alert')) {
            container.insertBefore(alert, this.consoleEl);
        }
    }

    resume() {
        if (this.courseId) {
            this.reconnect();
            const alert = document.getElementById('resume-alert');
            if (alert) alert.remove();
        }
    }

    showCompleteUI(courseId) {
        this.logSystem('✅ Course generation complete!', 'success');
        // Trigger download UI or next step
        const downloadBtn = document.querySelector('#download-md, [href*="/download"]');
        if (downloadBtn) downloadBtn.classList.remove('hidden');
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '<',
            '>': '>',
            '"': '"',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    clear() {
        this.consoleEl.innerHTML = '';
        this.renderWelcome();
    }

    destroy() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        this.isConnected = false;
    }
}

// Global instance & auto-init
if (typeof window !== 'undefined') {
    window.liveLogger = new LiveLogger();
    
    // Auto-init if console found
    document.addEventListener('DOMContentLoaded', () => {
        const consoles = document.querySelectorAll('#console-output, #agent-console');
        if (consoles.length && window.sessionManager?.courseId) {
            window.liveLogger.init(consoles[0], window.sessionManager.courseId);
        }
    });
}

