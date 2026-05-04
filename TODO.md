# Frontend Replacement TODO

## [ ] 1. Backup current frontend
- cp -r Pages Pages_backup

## [ ] 2. Delete existing frontend  
- rm -rf Pages

## [ ] 3. Create new frontend/ directory structure
- Create package.json, vite.config.ts, index.html
- npm init vite (React TS)
- Install deps: tailwind, react-router-dom, lucide-react (icons)

## [ ] 4. Implement core components
- UI: Stepper, Toast, Logger, SessionManager
- Pages: CreateCourse, ReviewTemplate, FinalReview

## [ ] 5. API integration & testing
- Fetch wrappers for /generate, /courses/:id
- SSE live logger
- Error handling, loading states

## [ ] 6. Backend updates
- Update Main.py for new static mount /frontend
- CORS for vite dev proxy

## [ ] 7. Delete/update tests
- rm Application/Tests/test_frontend_api_interactivity.py

## [ ] 8. Demo & complete
- npm run dev in frontend/
- Full workflow test

Updated: Step 1 starting...

