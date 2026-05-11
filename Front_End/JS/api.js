class ApiClient {
    constructor() {
        // Automatically use current origin if hosted on the same server,
        // otherwise fallback to localhost:8000 for cross-origin dev (e.g. port 3000)
        this.baseUrl = window.location.port === '3000' ? 'http://localhost:8000' : '';
    }

    async _fetch(path, options = {}) {
        const url = `${this.baseUrl}${path}`;
        const config = {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            credentials: 'include',
            ...options
        };

        const response = await fetch(url, config);

        // Try to parse JSON error payloads even if the backend returns non-JSON.
        if (!response.ok) {
            let payload;
            try {
                payload = await response.json();
            } catch {
                payload = { detail: response.statusText };
            }
            const detail = payload?.detail || payload?.message || payload?.error || response.statusText;
            const status = response.status;
            const err = new Error(detail);
            err.status = status;
            err.payload = payload;
            throw err;
        }

        // Some endpoints could be non-json in the future.
        try {
            return await response.json();
        } catch {
            return null;
        }
    }


    getHealth() { return this._fetch('/health'); }

    getCourses(query = '') {
        const params = query ? `?q=${encodeURIComponent(query)}` : '';
        return this._fetch(`/courses/search-courses${params}`);
    }

    getCourseReview(courseId) { return this._fetch(`/courses/${courseId}/course-review`); }
    getCourseStatus(courseId) { return this._fetch(`/courses/${courseId}/status`); }

    generateCourseTemplate(title, level = 'beginner', duration_months = 3) {
        return this._fetch('/courses/generate/course-template', {
            method: 'POST',
            body: JSON.stringify({ title, level, duration_months })
        });
    }

    approveCourse(courseId, modifications = null) {
        return this._fetch(`/courses/${courseId}/approve-full`, {
            method: 'POST',
            body: JSON.stringify(modifications || [])
        });
    }

    streamCourseTemplate(title, level = 'beginner', duration_months = 3, onMessage, onDone) {
        const params = new URLSearchParams({ title, level, duration_months });
        const es = new EventSource(`${this.baseUrl}/courses/generate/course-template-stream?${params.toString()}`);
        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'done') {
                    onDone && onDone(data);
                    es.close();
                } else {
                    onMessage && onMessage(data);
                }
            } catch (e) {
                console.error('SSE parse error', e);
            }
        };
        es.onerror = () => { console.error('Template stream error'); es.close(); };
        return es;
    }

    async downloadCourse(courseId, format = 'markdown') {
        const response = await fetch(`${this.baseUrl}/courses/${courseId}/download?format=${format}`);
        const blob = await response.blob();
        return { blob, filename: `course_${courseId}.${format === 'json' ? 'json' : 'md'}` };
    }

    streamCourseEvents(courseId, onMessage, onDone) {
        const es = new EventSource(`${this.baseUrl}/courses/${courseId}/events`);
        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'done') { onDone && onDone(data); es.close(); }
                else onMessage(data);
            } catch(e) { console.error('SSE parse error', e); }
        };
        es.onerror = () => { console.error('SSE error'); es.close(); };
        return es;
    }

    getGenerationContent(courseId) {
        return this._fetch(`/courses/${courseId}/generation-content`);
    }

    generateSyllabus(data) {
        return this._fetch('/syllabus/generate', { method: 'POST', body: JSON.stringify(data) });
    }


    scrapeSyllabus(title) {
        return this._fetch('/syllabus/scrape', { method: 'POST', body: JSON.stringify({ title }) });
    }
}

// ── Course CRUD compatibility (used by Front_End/JS/courses.js) ─────────────
// These endpoints must exist on the backend.
// If the backend implements different routes, update paths here.

ApiClient.prototype.getCourse = function(courseId) {
    return this._fetch(`/courses/${courseId}`);
};

ApiClient.prototype.createCourse = function(courseData) {
    return this._fetch('/courses', {
        method: 'POST',
        body: JSON.stringify(courseData)
    });
};

ApiClient.prototype.updateCourse = function(courseId, courseData) {
    return this._fetch(`/courses/${courseId}`, {
        method: 'PUT',
        body: JSON.stringify(courseData)
    });
};

ApiClient.prototype.deleteCourse = function(courseId) {
    return this._fetch(`/courses/${courseId}`, {
        method: 'DELETE'
    });
};

const api = new ApiClient();
