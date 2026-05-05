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

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('syllabus-form')?.addEventListener('submit', handleSyllabusFormSubmit);
    document.getElementById('scrape-btn')?.addEventListener('click', handleScrape);
    document.getElementById('approve-btn')?.addEventListener('click', handleApprove);
    document.getElementById('edit-btn')?.addEventListener('click', handleEdit);
    document.getElementById('export-btn')?.addEventListener('click', handleExport);
});

async function handleScrape() {
    const title = document.getElementById('syllabus-title').value.trim();
    if (!title) { showNotification('Enter a course title first.', 'warning'); return; }
    const btn = document.getElementById('scrape-btn');
    toggleLoadingState(btn, true);
    try {
        const res = await api.scrapeSyllabus(title);
        showNotification(`Scraped ${res.syllabi_found} sources (${res.total_chunks_stored} chunks stored).`, 'success');
    } catch(e) {
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

    const topics = document.getElementById('topics-input').value
        .split(',').map(t => t.trim()).filter(Boolean);

    const payload = {
        title: document.getElementById('syllabus-title').value.trim(),
        topics: topics.length ? topics : ['Introduction'],
    };

    try {
        progressBar.style.width = '30%';
        const res = await api.generateSyllabus(payload);
        progressBar.style.width = '100%';
        displaySyllabusResults(res, payload.title);
        document.getElementById('syllabus-results').style.display = 'block';
        document.getElementById('syllabus-results').scrollIntoView({ behavior: 'smooth' });
        showNotification('Syllabus generated!', 'success');
    } catch(e) {
        showNotification(`Generation failed: ${e.message}`, 'error');
    } finally {
        toggleLoadingState(btn, false);
        setTimeout(() => { progressWrap.style.display = 'none'; progressBar.style.width = '0%'; }, 800);
    }
}

function displaySyllabusResults(data, title) {
    document.getElementById('results-title').textContent = `Syllabus: ${title || data.title || 'Course'}`;
    const content = document.getElementById('syllabus-content');
    const syllabus = data.syllabus || [];
    const chapters = data.chapters || {};

    if (!syllabus.length) {
        content.innerHTML = '<p>No syllabus returned. Try again.</p>';
        return;
    }

    content.innerHTML = `<ol style="margin:0;padding-left:1.25rem;">
        ${syllabus.map(topic => `
            <li class="syllabus-topic">
                <h4>${topic}</h4>
                ${chapters[topic] ? `<p>${chapters[topic]}</p>` : ''}
            </li>`).join('')}
    </ol>`;

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

function handleEdit() {
    document.getElementById('syllabus-results').style.display = 'none';
    document.getElementById('syllabus-form').scrollIntoView({ behavior: 'smooth' });
}

async function handleApprove() {
    showNotification('Syllabus submitted for approval!', 'success');
    setTimeout(() => { window.location.href = 'approvals.html'; }, 1200);
}

async function handleExport() {
    showNotification('Redirecting to exports…', 'info');
    setTimeout(() => { window.location.href = 'exports.html'; }, 800);
}
