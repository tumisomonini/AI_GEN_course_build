/**
 * Session Manager - Unified state management for course workflow
 * Handles localStorage + backend sync, auto-resume, global state
 */

class SessionManager {
    constructor() {
        this.courseId = null;
        this.workflowStep = 1; // 1=create, 2=review, 3=final
        this.state = {}; // template data, etc
        this.liveLogger = new LiveLogger(); // ✅ Live logging integration
        this.init();
    }

    init() {
        // Load from localStorage first
        const saved = localStorage.getItem('course_workflow');
        if (saved) {
            const parsed = JSON.parse(saved);
            this.courseId = parsed.course_id;
            this.workflowStep = parsed.step || 1;
            this.state = parsed.state || {};
        }
        
        // Auto-init live logger if console available
        const consoles = document.querySelectorAll('#console-output, #agent-console');
        if (consoles.length) {
            this.liveLogger.init(consoles[0], this.courseId);
        }
        
        // Sync with backend session
        this.syncWithBackend().then(() => {
            this.save();
            this.dispatch('session_ready');
        });
    }

    async syncWithBackend() {
        try {
            const res = await fetch('/session/course');
            const data = await res.json();
            if (data.course_id) {
                this.courseId = data.course_id;
                // Fetch current workflow status
                const statusRes = await fetch(`/courses/${this.courseId}/status`);
                const status = await statusRes.json();
                this.workflowStep = this.mapStatusToStep(status.status);
            }
        } catch (e) {
            console.warn('Backend sync failed:', e);
        }
    }

    mapStatusToStep(status) {
        const map = {
            'pending': 1,
            'awaiting_approval': 2,
            'generating_full': 3,
            'completed': 3
        };
        return map[status] || 1;
    }

    save() {
        const toSave = {
            course_id: this.courseId,
            step: this.workflowStep,
            state: this.state,
            timestamp: Date.now()
        };
        localStorage.setItem('course_workflow', JSON.stringify(toSave));
    }

    async saveToBackend(courseId = null) {
        this.courseId = courseId || this.courseId;
        await fetch('/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `course_id=${this.courseId}`
        });
        this.save();
        if (this.liveLogger) {
            this.liveLogger.logSystem(`Session saved: ${this.courseId}`, 'info');
        }
    }

    clear() {
        localStorage.removeItem('course_workflow');
        this.courseId = null;
        this.workflowStep = 1;
        this.state = {};
        fetch('/session/clear', { method: 'POST' });
        this.dispatch('session_cleared');
    }

    updateState(key, value) {
        this.state[key] = value;
        this.save();
    }

    // Events
    dispatch(event) {
        window.dispatchEvent(new CustomEvent(`workflow:${event}`, { 
            detail: { manager: this } 
        }));
    }

    on(event, callback) {
        window.addEventListener(`workflow:${event}`, callback);
    }
}

// Global instance - exposes liveLogger
window.sessionManager = new SessionManager();
window.sessionManager.liveLogger = window.sessionManager.liveLogger; // ✅ Expose logger globally

