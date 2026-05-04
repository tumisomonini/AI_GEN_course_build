/**
 * Workflow Stepper - Shared across all pages
 * Handles step navigation, progress, validation
 */

class Stepper {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.steps = this.container?.querySelectorAll('.step') || [];
        this.currentStep = 1;
        this.totalSteps = this.steps.length;
        this.init();
    }

    init() {
        // Listen to session changes
        window.sessionManager?.on('session_ready', () => {
            this.goToStep(window.sessionManager.workflowStep);
        });

        // Navigation buttons
        this.container.addEventListener('click', (e) => {
            if (e.target.matches('[data-step-next]')) this.next();
            if (e.target.matches('[data-step-prev]')) this.prev();
            if (e.target.matches('.step')) {
                const stepNum = parseInt(e.target.dataset.stepNum);
                if (stepNum) this.goToStep(stepNum);
            }
        });
    }

    goToStep(stepNum) {
        if (stepNum < 1 || stepNum > this.totalSteps) return;

        // Update visual state
        this.steps.forEach((step, idx) => {
            const stepIdx = idx + 1;
            step.classList.remove('active', 'complete', 'pending');
            step.classList.add(stepIdx < stepNum ? 'complete' : 
                           stepIdx === stepNum ? 'active' : 'pending');
        });

        this.currentStep = stepNum;
        window.sessionManager.workflowStep = stepNum;
        window.sessionManager.save();

        // Show/hide content sections
        document.querySelectorAll('[data-step]').forEach(section => {
            section.style.display = parseInt(section.dataset.step) === stepNum ? 'block' : 'none';
        });

        // Dispatch event
        window.dispatchEvent(new CustomEvent('step_changed', { 
            detail: { step: stepNum, stepper: this } 
        }));
    }

    next() {
        if (this.validateCurrentStep()) {
            this.goToStep(this.currentStep + 1);
        }
    }

    prev() {
        this.goToStep(this.currentStep - 1);
    }

    validateCurrentStep() {
        const currentSection = document.querySelector(`[data-step="${this.currentStep}"]`);
        const required = currentSection?.querySelectorAll('[required]');
        
        for (let el of required) {
            if (!el.value.trim()) {
                el.focus();
                showNotification('Please fill all required fields', 'error');
                return false;
            }
        }
        return true;
    }
}

// Auto-init if stepper found
if (document.querySelector('.stepper-container')) {
    window.stepper = new Stepper('stepper-container');
}

