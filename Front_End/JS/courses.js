// ── Shared utilities ────────────────────────────────────────────────────────

function showNotification(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `notification notification-${type}`;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => {
        el.style.animation = 'slideOut .25s ease forwards';
        setTimeout(() => el.remove(), 260);
    }, 4000);
}

function toggleLoadingState(btn, loading) {
    btn.disabled = loading;
    btn._origText = btn._origText || btn.innerHTML;
    btn.innerHTML = loading ? '<span class="spinner"></span>' : btn._origText;
}

function badgeHtml(status) {
    return `<span class="badge badge-${status}">${status}</span>`;
}

// ── Course list ──────────────────────────────────────────────────────────────

let allCourses = [];

async function loadCourses(query = '') {
    const container = document.getElementById('courses-container');
    if (!container) return;
    container.innerHTML = '<div class="empty-state"><p>Loading…</p></div>';
    try {
        const data = await api.getCourses(query);
        allCourses = data.results || [];
        renderCourses(allCourses);
    } catch(e) {
        container.innerHTML = `<div class="empty-state"><p>Failed to load courses: ${e.message}</p></div>`;
    }
}

function renderCourses(courses) {
    const container = document.getElementById('courses-container');
    const statusFilter = document.getElementById('course-status-filter')?.value || 'all';
    const filtered = statusFilter === 'all' ? courses : courses.filter(c => c.status === statusFilter);

    if (!filtered.length) {
        container.innerHTML = '<div class="empty-state"><p>No courses found. Create one!</p></div>';
        return;
    }
    container.innerHTML = filtered.map(c => `
        <div class="course-card card">
            <div class="course-card-header">
                <h3>${c.title || 'Untitled'}</h3>
                ${badgeHtml(c.status || 'unknown')}
            </div>
            <div class="course-card-body">
                <p>${c.description || 'No description.'}</p>
                <p style="font-size:.8rem;color:var(--text-light);">
                    Level: ${c.level || '—'} &nbsp;|&nbsp; Duration: ${c.duration_months || '—'} months
                </p>
            </div>
            <div class="course-card-footer">
                <span style="font-size:.8rem;color:var(--text-light);">ID: ${c.course_id}</span>
                <div class="course-actions">
                    ${c.status === 'awaiting_approval'
                        ? `<button class="btn btn-sm btn-success" onclick="openApproveModal(${c.course_id})">Review</button>`
                        : ''}
                    ${c.status === 'completed'
                        ? `<button class="btn btn-sm btn-secondary" onclick="downloadCourse(${c.course_id})">⬇ Download</button>`
                        : ''}
                    ${['generating_outline','generating_full'].includes(c.status)
                        ? `<button class="btn btn-sm btn-secondary" onclick="openProgressModal(${c.course_id})">📡 Progress</button>`
                        : ''}
                </div>
            </div>
        </div>`).join('');
}

// ── Generate course modal ────────────────────────────────────────────────────

function openCreateModal() {
    document.getElementById('course-modal').classList.add('open');
    document.getElementById('course-form').reset();
    document.getElementById('modal-title').textContent = 'Create New Course';
    document.getElementById('gen-log-section').style.display = 'none';
    document.getElementById('gen-log').innerHTML = '';
}

function closeCreateModal() {
    document.getElementById('course-modal').classList.remove('open');
}

async function handleCourseFormSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('submit-course-btn');
    const title = document.getElementById('course-title').value.trim();
    const level = document.getElementById('course-level').value;
    const duration = parseInt(document.getElementById('course-duration').value) || 3;

    toggleLoadingState(btn, true);
    document.getElementById('gen-log-section').style.display = 'block';
    const logEl = document.getElementById('gen-log');
    logEl.innerHTML = '';

    function appendLog(msg, cls = 'log-info') {
        logEl.innerHTML += `<div class="${cls}">[${new Date().toLocaleTimeString()}] ${msg}</div>`;
        logEl.scrollTop = logEl.scrollHeight;
    }

    try {
        appendLog(`Starting generation for "${title}"…`);
        const res = await api.generateCourseTemplate(title, level, duration);
        appendLog(`Course created (ID: ${res.course_id}). Streaming progress…`);

        await new Promise((resolve) => {
            api.streamCourseEvents(
                res.course_id,
                (data) => appendLog(`[${data.agent || 'system'}] ${data.message}`, `log-${data.level || 'info'}`),
                (done) => {
                    appendLog(`Generation ${done.status}.`, done.status === 'completed' ? 'log-info' : 'log-error');
                    resolve();
                }
            );
        });

        showNotification('Course outline ready for review!', 'success');
        closeCreateModal();
        await loadCourses();
    } catch(err) {
        appendLog(`Error: ${err.message}`, 'log-error');
        showNotification(`Failed: ${err.message}`, 'error');
    } finally {
        toggleLoadingState(btn, false);
    }
}

// ── Approve modal ────────────────────────────────────────────────────────────

let _approveId = null;

async function openApproveModal(courseId) {
    _approveId = courseId;
    const modal = document.getElementById('approve-modal');
    modal.classList.add('open');
    document.getElementById('approve-content').innerHTML = '<p>Loading outline…</p>';
    document.getElementById('chapter-edits').value = '';

    try {
        const data = await api.getCourseReview(courseId);
        const tpl = data.template || {};
        const chapters = tpl.chapters || [];
        document.getElementById('approve-modal-title').textContent = `Review: ${tpl.title || 'Course'}`;
        document.getElementById('approve-content').innerHTML = `
            <p><strong>Level:</strong> ${tpl.level || '—'} &nbsp; <strong>Duration:</strong> ${tpl.duration_months || '—'} months</p>
            <p style="margin-top:.5rem;font-weight:500;">Chapters (${chapters.length}):</p>
            <ol style="margin:.5rem 0 0 1.25rem;font-size:.875rem;line-height:1.8;">
                ${chapters.map(ch => `<li>${ch}</li>`).join('')}
            </ol>`;
        document.getElementById('chapter-edits').value = chapters.join('\n');
    } catch(e) {
        document.getElementById('approve-content').innerHTML = `<p style="color:var(--danger)">Failed to load: ${e.message}</p>`;
    }
}

function closeApproveModal() {
    document.getElementById('approve-modal').classList.remove('open');
    _approveId = null;
}

async function submitApproval() {
    if (!_approveId) return;
    const btn = document.getElementById('approve-submit-btn');
    const edits = document.getElementById('chapter-edits').value.trim();
    const modifications = edits ? edits.split('\n').map(s => s.trim()).filter(Boolean) : null;

    toggleLoadingState(btn, true);
    try {
        await api.approveCourse(_approveId, modifications);
        showNotification('Approved! Full content generation started.', 'success');
        closeApproveModal();
        await loadCourses();
    } catch(e) {
        showNotification(`Approval failed: ${e.message}`, 'error');
    } finally {
        toggleLoadingState(btn, false);
    }
}

// ── Progress modal ───────────────────────────────────────────────────────────

function openProgressModal(courseId) {
    const modal = document.getElementById('progress-modal');
    modal.classList.add('open');
    const logEl = document.getElementById('progress-log');
    logEl.innerHTML = '';

    function appendLog(msg, cls = 'log-info') {
        logEl.innerHTML += `<div class="${cls}">[${new Date().toLocaleTimeString()}] ${msg}</div>`;
        logEl.scrollTop = logEl.scrollHeight;
    }

    appendLog(`Connecting to course ${courseId} stream…`);
    const es = api.streamCourseEvents(
        courseId,
        (data) => appendLog(`[${data.agent || 'system'}] ${data.message}`, `log-${data.level || 'info'}`),
        (done) => {
            appendLog(`Done — status: ${done.status}`, done.status === 'completed' ? 'log-info' : 'log-error');
            loadCourses();
        }
    );
    document.getElementById('progress-modal').dataset.es = 'open';
    document.getElementById('close-progress-btn').onclick = () => {
        es.close();
        modal.classList.remove('open');
    };
}

// ── Download ─────────────────────────────────────────────────────────────────

async function downloadCourse(courseId) {
    try {
        const { blob, filename } = await api.downloadCourse(courseId, 'markdown');
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename; a.click();
        URL.revokeObjectURL(url);
    } catch(e) {
        showNotification(`Download failed: ${e.message}`, 'error');
    }
}

// ── Courses dropdown (used by other pages) ───────────────────────────────────

async function loadCoursesDropdown() {
    try {
        const data = await api.getCourses('');
        const courses = data.results || [];
        document.querySelectorAll('select[id$="-course-select"], select[id$="-course-filter"]').forEach(sel => {
            while (sel.options.length > 1) sel.remove(1);
            courses.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.course_id;
                opt.textContent = c.title;
                sel.appendChild(opt);
            });
        });
    } catch(e) { /* non-critical */ }
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Wire up create button
    document.getElementById('create-course-btn')?.addEventListener('click', openCreateModal);
    document.getElementById('cancel-btn')?.addEventListener('click', closeCreateModal);
    document.getElementById('course-form')?.addEventListener('submit', handleCourseFormSubmit);

    // Approve modal
    document.getElementById('approve-cancel-btn')?.addEventListener('click', closeApproveModal);
    document.getElementById('approve-submit-btn')?.addEventListener('click', submitApproval);

    // Search & filter
    document.getElementById('course-search')?.addEventListener('input', (e) => {
        const q = e.target.value.trim();
        if (q.length === 0 || q.length >= 2) loadCourses(q);
    });
    document.getElementById('course-status-filter')?.addEventListener('change', () => renderCourses(allCourses));

    // Close modals on backdrop click
    document.querySelectorAll('.modal').forEach(m => {
        m.addEventListener('click', (e) => { if (e.target === m) m.classList.remove('open'); });
    });

    loadCourses();
});
