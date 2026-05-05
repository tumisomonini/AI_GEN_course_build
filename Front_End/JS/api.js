class ApiClient {
    constructor() {
        this.baseUrl = 'http://localhost:8000';
    }

    async _fetch(path, options = {}) {
        const url = `${this.baseUrl}${path}`;
        const config = {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            credentials: 'include',
            ...options
        };
        const response = await fetch(url, config);
        if (!response.ok) {
            const err = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(err.detail || err.message || `HTTP ${response.status}`);
        }
        return response.json();
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

    generateSyllabus(data) {
        return this._fetch('/syllabus/generate', { method: 'POST', body: JSON.stringify(data) });
    }

    scrapeSyllabus(title) {
        return this._fetch('/syllabus/scrape', { method: 'POST', body: JSON.stringify({ title }) });
    }
}

const api = new ApiClient();
