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

// ── State ─────────────────────────────────────────────────────────────────────
let _currentApprovalId = null;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('approval-status-filter')?.addEventListener('change', loadApprovals);
    document.getElementById('approval-cancel-btn')?.addEventListener('click', closeApprovalModal);
    document.getElementById('approval-submit-btn')?.addEventListener('click', handleApprovalSubmit);
    document.getElementById('reject-btn')?.addEventListener('click', handleReject);

    document.querySelectorAll('.modal').forEach(m => {
        m.addEventListener('click', (e) => { if (e.target === m) m.classList.remove('open'); });
    });

    loadApprovals();
});

// ── Load approvals (courses awaiting approval) ────────────────────────────────
async function loadApprovals() {
    const container = document.getElementById('approvals-container');
    container.innerHTML = '<div class="empty-state"><p>Loading…</p></div>';

    const statusFilter = document.getElementById('approval-status-filter')?.value || 'all';

    try {
        const data = await api.getCourses('');
        let courses = data.results || [];

        if (statusFilter !== 'all') {
            courses = courses.filter(c => c.status === statusFilter);
        } else {
            // Default: show courses that need action
            courses = courses.filter(c =>
                ['awaiting_approval', 'completed', 'failed', 'generating_full', 'generating_outline'].includes(c.status)
            );
        }

        if (!courses.length) {
            container.innerHTML = '<div class="empty-state"><p>No courses to review.</p></div>';
            return;
        }

        container.innerHTML = '';
        courses.forEach(c => container.appendChild(createApprovalCard(c)));
    } catch(e) {
        container.innerHTML = `<div class="empty-state"><p>Failed to load: ${e.message}</p></div>`;
    }
}

function createApprovalCard(course) {
    const card = document.createElement('div');
    card.className = 'approval-card';
    card.innerHTML = `
        <div class="approval-info">
            <h3>${course.title || 'Untitled'}</h3>
            <div class="approval-meta">
                <span>ID: ${course.course_id}</span>
                <span>Level: ${course.level || '—'}</span>
                <span>Duration: ${course.duration_months || '—'} months</span>
            </div>
        </div>
        <div class="approval-actions">
            <span class="badge badge-${course.status}">${course.status}</span>
            ${course.status === 'awaiting_approval'
                ? `<button class="btn btn-sm btn-primary review-btn">Review</button>`
                : course.status === 'completed'
                    ? `<button class="btn btn-sm btn-secondary download-btn">⬇ Download</button>`
                    : ''}
        </div>`;

    card.querySelector('.review-btn')?.addEventListener('click', () => openApprovalModal(course.course_id));
    card.querySelector('.download-btn')?.addEventListener('click', () => downloadCourse(course.course_id));
    return card;
}

// ── Approval modal ────────────────────────────────────────────────────────────
async function openApprovalModal(courseId) {
    _currentApprovalId = courseId;
    const modal = document.getElementById('approval-modal');
    modal.classList.add('open');
    document.getElementById('approval-content').innerHTML = '<p>Loading outline…</p>';
    document.getElementById('approval-comments').value = '';

    try {
        const data = await api.getCourseReview(courseId);
        const tpl = data.template || {};
        const chapters = tpl.chapters || [];
        document.getElementById('approval-modal-title').textContent = `Review: ${tpl.title || 'Course'}`;
        document.getElementById('approval-content').innerHTML = `
            <p><strong>Level:</strong> ${tpl.level || '—'} &nbsp; <strong>Duration:</strong> ${tpl.duration_months || '—'} months</p>
            ${tpl.learning_objectives?.length ? `<p style="margin-top:.5rem;"><strong>Objectives:</strong> ${tpl.learning_objectives.join(', ')}</p>` : ''}
            <p style="margin-top:.75rem;font-weight:500;">Chapters (${chapters.length}):</p>
            <ol style="margin:.4rem 0 0 1.25rem;font-size:.875rem;line-height:1.8;">
                ${chapters.map(ch => `<li>${ch}</li>`).join('')}
            </ol>`;
    } catch(e) {
        document.getElementById('approval-content').innerHTML = `<p style="color:var(--danger)">Error: ${e.message}</p>`;
    }
}

function closeApprovalModal() {
    document.getElementById('approval-modal').classList.remove('open');
    _currentApprovalId = null;
}

async function handleApprovalSubmit() {
    if (!_currentApprovalId) return;
    const btn = document.getElementById('approval-submit-btn');
    toggleLoadingState(btn, true);
    try {
        await api.approveCourse(_currentApprovalId);
        showNotification('Approved! Full content generation started.', 'success');
        closeApprovalModal();
        await loadApprovals();
    } catch(e) {
        showNotification(`Approval failed: ${e.message}`, 'error');
    } finally {
        toggleLoadingState(btn, false);
    }
}

async function handleReject() {
    if (!_currentApprovalId) return;
    const comments = document.getElementById('approval-comments').value.trim();
    showNotification(`Course ${_currentApprovalId} rejected. ${comments ? `Note: ${comments}` : ''}`, 'warning');
    closeApprovalModal();
}

// ── Download helper ───────────────────────────────────────────────────────────
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
