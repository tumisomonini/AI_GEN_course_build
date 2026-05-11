// Course Management Logic
document.addEventListener('DOMContentLoaded', async function() {

    // Load courses on page load
    await loadCourses();

    // Set up event listeners
    document.getElementById('create-course-btn')?.addEventListener('click', () => {
        openCourseModal();
    });

    document.getElementById('cancel-btn')?.addEventListener('click', () => {
        closeCourseModal();
    });

    // Submit / generate
    document.getElementById('course-form')?.addEventListener('submit', onCourseFormSubmit);

    // Set up search and filter
    document.getElementById('course-search')?.addEventListener('input', filterCourses);
    document.getElementById('course-status-filter')?.addEventListener('change', filterCourses);
});

let activeCourseStream = null;
let activeCourseId = null;

function appendGenLogLine(text, level = 'info') {
    const logEl = document.getElementById('gen-log');
    if (!logEl) return;

    const line = document.createElement('div');
    line.className = `gen-log-line gen-log-${level}`;
    const ts = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    line.innerHTML = `<span class="gen-log-ts">${ts}</span><span class="gen-log-msg">${text}</span>`;
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
}

function clearGenLog() {
    const logEl = document.getElementById('gen-log');
    if (!logEl) return;
    logEl.innerHTML = '';
}

async function onCourseFormSubmit(e) {
    e.preventDefault();

    const title = document.getElementById('course-title')?.value?.trim();
    const level = document.getElementById('course-level')?.value || 'beginner';
    const duration_months = parseInt(document.getElementById('course-duration')?.value, 10) || 3;

    if (!title) {
        showNotification('Enter a course title first.', 'warning');
        return;
    }

    const logSection = document.getElementById('gen-log-section');
    if (logSection) logSection.style.display = 'block';

    const submitBtn = document.getElementById('submit-course-btn');
    toggleLoadingState(submitBtn, true);
    clearGenLog();

    try {
        appendGenLogLine(`Starting generation for '${title}'...`, 'info');

        // Open SSE stream that both triggers and reports progress.
        const input = new URLSearchParams({ title, level, duration_months });
        const url = `${api.baseUrl}/courses/generate/course-template-stream?${input.toString()}`;

        // Ensure the progress modal is visible on mobile/desktop.
        const progressModal = document.getElementById('progress-modal');
        if (progressModal) progressModal.style.display = 'block';


        if (activeCourseStream) {
            try { activeCourseStream.close(); } catch {}
            activeCourseStream = null;
        }

        activeCourseStream = new EventSource(url);

        activeCourseStream.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'init') {
                    activeCourseId = data.course_id;
                    appendGenLogLine(`Created course_id=${data.course_id} run_id=${data.run_id}`, 'success');
                    return;
                }

                if (data.type === 'log') {
                    appendGenLogLine(`[${data.agent || 'Agent'}] ${data.message}`, data.level || 'info');
                    return;
                }

                if (data.type === 'error') {
                    const msg = data.message || 'Generation failed';
                    appendGenLogLine(msg, 'error');
                    showNotification(msg, 'error');
                    toggleLoadingState(submitBtn, false);
                    if (activeCourseStream) {
                        activeCourseStream.close();
                        activeCourseStream = null;
                    }
                    return;
                }


                if (data.type === 'done') {
                    const status = data.status;
                    appendGenLogLine(`Generation finished: ${status}`, status === 'failed' ? 'error' : 'success');
                    if (activeCourseStream) {
                        activeCourseStream.close();
                        activeCourseStream = null;
                    }
                    closeCourseModal();
                    loadCourses();
                    showNotification(
                        status === 'failed' ? 'Generation failed. Check logs.' : 'Generation completed. You can review/download the course.',
                        status === 'failed' ? 'error' : 'success'
                    );
                    return;
                }
            } catch (err) {
                console.error('SSE parse error', err);
            }
        };

        activeCourseStream.onerror = () => {
            appendGenLogLine('SSE stream error. Generation may still be running on backend.', 'error');
            if (activeCourseStream) {
                activeCourseStream.close();
                activeCourseStream = null;
            }
            showNotification('Stream connection error. See logs for details.', 'error');
            toggleLoadingState(submitBtn, false);
        };
    } catch (error) {
        console.error('Failed to start generation:', error);
        showNotification(`Failed to start generation: ${error.message}`, 'error');

        const progressModal = document.getElementById('progress-modal');
        if (progressModal) progressModal.style.display = 'none';

    } finally {
        toggleLoadingState(submitBtn, false);
    }
}


/**
 * Load all courses
 */
async function loadCourses() {
    try {
        const coursesContainer = document.getElementById('courses-container');
        coursesContainer.innerHTML = '<div class="loading-spinner">Loading courses...</div>';

        const courses = await api.getCourses();

        if (courses.length === 0) {
            coursesContainer.innerHTML = '<p>No courses found. Create your first course!</p>';
            return;
        }

        coursesContainer.innerHTML = '';
        courses.forEach(course => {
            const courseCard = createCourseCard(course);
            coursesContainer.appendChild(courseCard);
        });
    } catch (error) {
        console.error('Failed to load courses:', error);
        showNotification('Failed to load courses', 'error');
    }
}

/**
 * Create a course card element
 */
function createCourseCard(course) {
    const card = document.createElement('div');
    card.className = 'course-card';
    card.innerHTML = `
        <div class="course-card-header">
            <h3>${course.title}</h3>
            <span class="status-badge status-${course.status}">${course.status}</span>
        </div>
        <div class="course-card-body">
            <p>${course.description || 'No description provided'}</p>
            <div class="course-meta">
                <span>👥 ${course.audience || 'General'}</span>
                <span>📅 Created: ${new Date(course.created_at).toLocaleDateString()}</span>
            </div>
        </div>
        <div class="course-card-footer">
            <div class="course-actions">
                <button class="btn btn-sm btn-secondary view-btn" data-id="${course.course_id}">View</button>
                <button class="btn btn-sm btn-primary edit-btn" data-id="${course.course_id}">Edit</button>
                <button class="btn btn-sm btn-danger delete-btn" data-id="${course.course_id}">Delete</button>
            </div>
        </div>
    `;

    // Add event listeners
    card.querySelector('.view-btn').addEventListener('click', () => {
        viewCourse(course.course_id);
    });

    card.querySelector('.edit-btn').addEventListener('click', () => {
        editCourse(course.course_id);
    });

    card.querySelector('.delete-btn').addEventListener('click', () => {
        deleteCourse(course.course_id);
    });

    return card;
}

/**
 * Open the course modal for creating a new course
 */
function openCourseModal() {
    const modal = document.getElementById('course-modal');
    const form = document.getElementById('course-form');

    // Reset form
    form.reset();
    document.getElementById('modal-title').textContent = 'Create Course';

    // courses.html may not include a hidden course-id field (create mode)
    const courseIdEl = document.getElementById('course-id');
    if (courseIdEl) courseIdEl.value = '';


    // Show modal
    modal.style.display = 'block';
}

/**
 * Close the course modal
 */
function closeCourseModal() {
    document.getElementById('course-modal').style.display = 'none';
}

/**
 * Handle course form submission
 */
async function handleCourseFormSubmit(form) {
    const courseId = document.getElementById('course-id').value;
    const courseData = {
        title: document.getElementById('course-title').value,
        description: document.getElementById('course-description').value,
        audience: document.getElementById('course-audience').value,
        status: document.getElementById('course-status').value
    };

    try {
        let result;
        if (courseId) {
            // Update existing course
            result = await api.updateCourse(courseId, courseData);
            showNotification('Course updated successfully!', 'success');
        } else {
            // Create new course
            result = await api.createCourse(courseData);
            showNotification('Course created successfully!', 'success');
        }

        // Close modal and refresh courses
        closeCourseModal();
        await loadCourses();
    } catch (error) {
        console.error('Failed to save course:', error);
        showNotification(`Failed to save course: ${error.message}`, 'error');
    }
}

/**
 * View a course
 */
async function viewCourse(courseId) {
    try {
        const course = await api.getCourse(courseId);
        // For now, just edit the course
        editCourse(courseId);
    } catch (error) {
        console.error('Failed to view course:', error);
        showNotification('Failed to load course details', 'error');
    }
}

/**
 * Edit a course
 */
async function editCourse(courseId) {
    try {
        const course = await api.getCourse(courseId);
        const modal = document.getElementById('course-modal');
        const form = document.getElementById('course-form');

        // Populate form
        document.getElementById('modal-title').textContent = 'Edit Course';
        document.getElementById('course-id').value = course.course_id;
        document.getElementById('course-title').value = course.title;
        document.getElementById('course-description').value = course.description || '';
        document.getElementById('course-audience').value = course.audience || '';
        document.getElementById('course-status').value = course.status;

        // Show modal
        modal.style.display = 'block';
    } catch (error) {
        console.error('Failed to load course for editing:', error);
        showNotification('Failed to load course for editing', 'error');
    }
}

/**
 * Delete a course
 */
async function deleteCourse(courseId) {
    if (confirm('Are you sure you want to delete this course? This action cannot be undone.')) {
        try {
            await api.deleteCourse(courseId);
            showNotification('Course deleted successfully!', 'success');
            await loadCourses();
        } catch (error) {
            console.error('Failed to delete course:', error);
            showNotification(`Failed to delete course: ${error.message}`, 'error');
        }
    }
}

/**
 * Filter courses based on search and status
 */
function filterCourses() {
    const searchTerm = document.getElementById('course-search').value.toLowerCase();
    const statusFilter = document.getElementById('course-status-filter').value;

    const courseCards = document.querySelectorAll('.course-card');

    courseCards.forEach(card => {
        const title = card.querySelector('h3').textContent.toLowerCase();
        const status = card.querySelector('.status-badge').textContent.toLowerCase();

        const matchesSearch = title.includes(searchTerm);
        const matchesStatus = statusFilter === 'all' || status === statusFilter;

        if (matchesSearch && matchesStatus) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}