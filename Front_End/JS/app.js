// app.js — shared bootstrap, only runs on pages that load it directly
// Page-specific logic lives in courses.js / Syllabus.js / Approvals.js

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

// Close any modal when clicking its backdrop
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal').forEach(m => {
        m.addEventListener('click', (e) => { if (e.target === m) m.classList.remove('open'); });
    });
});
