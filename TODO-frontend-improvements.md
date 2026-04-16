# Frontend Improvements TODO

Generated: $(date)

## Current Status ✅

- Backend fully supports 3-step workflow (create→review→download)
- No API schema mismatches
- Static serving + CORS working
- Workflow persistence via localStorage + URL params

## Priority 1: Critical UX Fixes (1-2 hours)

### test_interface.html

- [ ] Configurable API base URL (data-api-base attr)
- [ ] Backend validation error surfacing (red banners w/ details)
- [ ] Form submission loading spinner + timeout handling

### approval_interface.html  

- [ ] Backend error modals (retry/cancel)
- [ ] Mobile-responsive chapter editing (flex/grid fixes)
- [ ] Save draft button (localStorage snapshot)

### course_review_interface.html

- [ ] Client-side PDF generation (jsPDF lib)
- [ ] Print-friendly CSS (@media print)
- [ ] Shareable course links (course_id param)

## Priority 2: Polish (2-3 hours)

- [ ] Consistent error toast notifications (all pages)
- [ ] Loading skeletons for course cards/chapters
- [ ] Keyboard shortcuts (Enter=submit, Esc=cancel)
- [ ] Accessibility: ARIA labels, focus management

## Priority 3: Advanced (future)

- [ ] WebSocket/SSE for real-time generation progress
- [ ] PWA manifest + offline fallback
- [ ] Frontend unit tests (fetch mocks)
- [ ] Theme toggle (dark mode CSS vars)

## Testing Checklist

- [ ] Mobile: iPhone/Android portrait/landscape
- [ ] Error scenarios: 400/500 responses, network offline
- [ ] End-to-end: generate→approve→download→final-approve
- [ ] Edge cases: long titles, empty fields, special chars

## Commands

```bash
# Serve for local dev (already working)
uvicorn Application.API.Main:app --reload --port 8000

# Test full workflow
open http://localhost:8000/Pages/test_interface.html
```