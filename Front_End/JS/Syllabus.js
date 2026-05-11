// ── Shared utilities (re-declared if loaded standalone) ──────────────────────
if (typeof showNotification === 'undefined') {
    window.showNotification = function(message, type = 'info') {
        const el = document.createElement('div');
        el.className = `notification notification-${type}`;
        el.textContent = message;
        document.body.appendChild(el);
        setTimeout(() => {
            el.style.animation = 'slideOut .25s ease forwards';
            setTimeout(() => el.remove(), 260);
        }, 4000);
    };
}
if (typeof toggleLoadingState === 'undefined') {
    window.toggleLoadingState = function(btn, loading) {
        btn.disabled = loading;
        btn._origText = btn._origText || btn.innerHTML;
        btn.innerHTML = loading ? '<span class="spinner"></span>' : btn._origText;
    };
}

// ── Syllabus page ─────────────────────────────────────────────────────────────

let currentCourseId = null;
let currentRunId = null;
let templateStream = null;
let contentPollTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('syllabus-form')?.addEventListener('submit', handleSyllabusFormSubmit);
    document.getElementById('approve-btn')?.addEventListener('click', handleApprove);
    document.getElementById('edit-btn')?.addEventListener('click', handleEdit);
    document.getElementById('export-btn')?.addEventListener('click', handleExport);
    document.getElementById('clear-console')?.addEventListener('click', clearConsole);
});


async function handleScrape() {
    const title = document.getElementById('syllabus-title').value.trim();
    if (!title) { showNotification('Enter a course title first.', 'warning'); return; }
    const btn = document.getElementById('scrape-btn');
    toggleLoadingState(btn, true);
    logConsole('Scraper', `Starting syllabus fetch for '${title}'...`, 'info');
    try {
        const res = await api.scrapeSyllabus(title);
        logConsole('Scraper', `Scrape completed: ${res.syllabi_found} sources found, ${res.total_chunks_stored} chunks stored.`, 'success');
        showNotification(`Scraped ${res.syllabi_found} sources (${res.total_chunks_stored} chunks stored).`, 'success');
    } catch(e) {
        logConsole('Scraper', `Scrape failed: ${e.message}`, 'error');
        showNotification(`Scrape failed: ${e.message}`, 'error');
    } finally {
        toggleLoadingState(btn, false);
    }
}

async function handleSyllabusFormSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('generate-btn');
    const progressWrap = document.getElementById('progress-wrap');
    const progressBar = document.getElementById('progress-bar');

    toggleLoadingState(btn, true);
    progressWrap.style.display = 'block';
    progressBar.style.width = '10%';

    const title = document.getElementById('syllabus-title').value.trim();
    const level = document.getElementById('syllabus-level').value || 'beginner';
    const duration_months = parseInt(document.getElementById('duration-months').value, 10) || 3;

    if (!title) {
        showNotification('Enter a course title first.', 'warning');
        toggleLoadingState(btn, false);
        progressWrap.style.display = 'none';
        return;
    }

    try {
        progressBar.style.width = '30%';
        logConsole('Workflow', `Starting one-shot outline generation for '${title}'...`, 'info');
        currentCourseId = null;
        currentRunId = null;

        document.getElementById('syllabus-results').style.display = 'block';
        document.getElementById('syllabus-results').scrollIntoView({ behavior: 'smooth' });
        showNotification('Generating syllabus outline…', 'success');

        // Syllabus endpoint returns once generation is done (no SSE).
        const res = await api.generateSyllabus({
            title,
            topics: [],
            level,
            duration_months
        });

        displaySyllabusResults(res, title);


    } catch(e) {
        logConsole('Workflow', `Generation failed: ${e.message}`, 'error');
        showNotification(`Generation failed: ${e.message}`, 'error');
    } finally {
        toggleLoadingState(btn, false);
        setTimeout(() => { progressBar.style.width = '100%'; }, 500);
    }
}

// Legacy course-review loader retained for other pages; syllabus page does not use it now.
async function loadCourseReview(courseId) {
    try {
        const res = await api.getCourseReview(courseId);
        const template = res.template || {};
        displayTemplateResults(template);
    } catch (e) {
        logConsole('System', `Unable to load outline summary: ${e.message}`, 'error');
    }
}


// Polling logic removed: syllabus page now uses POST /syllabus/generate (single response).
async function pollGenerationContent() {
    return;
}



function handleTemplateMessage(data) {
    if (data.type === 'init') {
        currentCourseId = data.course_id;
        currentRunId = data.run_id;
        logConsole('System', `Course created: ${currentCourseId}`, 'success');
        return;
    }
    if (data.type === 'log') {
        logConsole(data.agent || 'Agent', data.message, data.level || 'info');
    }
}

async function handleTemplateDone(data) {
    const status = data.status;
    logConsole('System', `Outline generation finished with status: ${status}`, status === 'failed' ? 'error' : 'success');

    // Stop polling as soon as SSE says we're done.
    if (contentPollTimer) {
        clearInterval(contentPollTimer);
        contentPollTimer = null;
    }

    if (currentCourseId) {
        // Final sync to ensure template+chapters are fully populated.
        await loadCourseReview(currentCourseId);
    }
    if (status === 'awaiting_approval') {
        showNotification('Outline generated. Review and approve to start full course generation.', 'success');
    } else if (status === 'completed') {
        showNotification('Outline completed and ready.', 'success');
    } else {
        showNotification(`Generation finished with status: ${status}`, status === 'failed' ? 'error' : 'info');
    }
}


function logConsole(agent, message, level = 'info') {
    const output = document.getElementById('console-output');
    if (!output) return;
    const entry = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString([], {hour12: false, hour: '2-digit', minute: '2-digit'});
    const color = level === 'error' ? '#f87171' : level === 'success' ? '#34d399' : '#93c5fd';
    entry.style.display = 'flex';
    entry.style.gap = '0.5rem';
    entry.style.alignItems = 'flex-start';
    entry.innerHTML = `
        <span style="color:#6b7280; min-width:64px;">${timestamp}</span>
        <span style="color:${color}; font-weight:600;">[${agent}]</span>
        <span style="color:#e5e7eb; flex:1;">${message}</span>
    `;
    output.appendChild(entry);
    output.scrollTop = output.scrollHeight;
}

function clearConsole() {
    const output = document.getElementById('console-output');
    if (output) {
        output.innerHTML = '<div style="color:#9ca3af;">Ready for course generation...</div>';
    }
}

function displaySyllabusResults(data, title) {
    document.getElementById('results-title').textContent = `Syllabus: ${title || data.title || 'Course'}`;
    const content = document.getElementById('syllabus-content');
    const syllabus = data.syllabus || [];
    const chapters = data.chapters || [];

    if (!syllabus.length) {
        content.innerHTML = '<p>No syllabus returned. Try again.</p>';
        return;
    }

    content.innerHTML = `
        <section class="syllabus-section">
            <h3>Topics</h3>
            <ol style="margin:0;padding-left:1.25rem;">
                ${syllabus.map(topic => `
                    <li class="syllabus-topic"><strong>${topic}</strong></li>
                `).join('')}
            </ol>
        </section>
        <section class="chapters-section">
            <h3>Chapters</h3>
            <ol style="margin:0;padding-left:1.25rem;">
                ${chapters.map(chapter => `
                    <li class="chapter-item">${chapter}</li>
                `).join('')}
            </ol>
        </section>
    `;

    // Logs
    const logs = data.logs || [];
    if (logs.length) {
        const logsSection = document.getElementById('logs-section');
        const logsContainer = document.getElementById('logs-container');
        logsSection.style.display = 'block';
        logsContainer.innerHTML = logs.map(l =>
            `<div class="log-${l.level || 'info'}">[${l.agent || 'system'}] ${l.message}</div>`
        ).join('');
    }
}

function displayTemplateResults(template) {
    const safeTemplate = template || {};

    const titleEl = document.getElementById('results-title');
    if (titleEl) titleEl.textContent = `Outline: ${(safeTemplate && safeTemplate.title) || 'Course'} (Review required)`;
    const content = document.getElementById('syllabus-content');

    // Expected schema (from older UI/backends):
    // - chapters: [{title, content?}, ...] OR ["Topic", ...]
    // - learning_objectives: ["...", ...]
    // - prerequisites: ["...", ...]
    const chapters = safeTemplate.chapters || [];
    const objectives = safeTemplate.learning_objectives || [];
    const prerequisites = safeTemplate.prerequisites || [];

    // Fallbacks for schema mismatches.
    // Some backend endpoints may return { syllabus: [...], topics: [...], ... }
    const fallbackTopics = safeTemplate.syllabus || safeTemplate.topics || [];

    const looksLikeExpected = Array.isArray(chapters) && (objectives.length || prerequisites.length || chapters.length);

    if (!looksLikeExpected) {
        // Render *something* and log the raw payload for contract debugging.
        console.warn('displayTemplateResults schema mismatch. Raw template:', safeTemplate);
        content.innerHTML = `
            <section class="syllabus-section">
                <h3>Outline (raw)</h3>
                <p style="color:#9ca3af;">Backend response schema didn’t match the expected template contract. Showing best-effort content.</p>
                <pre style="white-space:pre-wrap;word-break:break-word;background:#0b1220;border:1px solid #1f2937;border-radius:0.75rem;padding:0.75rem;color:#e5e7eb;">${JSON.stringify(safeTemplate, null, 2)}</pre>
            </section>
        `;
        return;
    }

    content.innerHTML = `
        <section class="syllabus-section">
            <h3>Objectives</h3>
            <ul>${(Array.isArray(objectives) ? objectives : []).map(obj => `<li>${obj}</li>`).join('')}</ul>
        </section>
        <section class="syllabus-section">
            <h3>Prerequisites</h3>
            <ul>${(Array.isArray(prerequisites) ? prerequisites : []).map(pre => `<li>${pre}</li>`).join('')}</ul>
        </section>
        <section class="chapters-section">
            <h3>Chapters</h3>
            <ol style="margin:0;padding-left:1.25rem;">${(Array.isArray(chapters) ? chapters : []).map(chapter => {
                if (typeof chapter === 'string') return `<li class="chapter-item">${chapter}</li>`;
                if (chapter && typeof chapter === 'object') return `<li class="chapter-item">${chapter.title || chapter.name || '[untitled]'}</li>`;
                return `<li class="chapter-item">[invalid]</li>`;
            }).join('') || (Array.isArray(fallbackTopics) && fallbackTopics.length ? fallbackTopics.map(t => `<li class="chapter-item">${typeof t === 'string' ? t : (t.title || t.name || '[untitled]')}</li>`).join('') : '')}</ol>
        </section>
    `;
}


function handleEdit() {
    document.getElementById('syllabus-results').style.display = 'none';
    document.getElementById('syllabus-form').scrollIntoView({ behavior: 'smooth' });
}

async function handleApprove() {
    if (currentCourseId) {
        try {
            await api.approveCourse(currentCourseId);
            showNotification('Approved! Full course generation started.', 'success');
            setTimeout(() => { window.location.href = 'approvals.html'; }, 1200);
        } catch (e) {
            showNotification(`Approval failed: ${e.message}`, 'error');
        }
    } else {
        showNotification('No generated course to approve yet.', 'warning');
        setTimeout(() => { window.location.href = 'approvals.html'; }, 1200);
    }
}

async function handleExport() {
    showNotification('Redirecting to exports…', 'info');
    setTimeout(() => { window.location.href = 'exports.html'; }, 800);
}
