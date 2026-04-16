# Fix Test Interface: Start Server & Verify

## ✅ Step 1: Start FastAPI Server (Fixed PYTHONPATH)

```bash
PYTHONPATH=. uvicorn Application.API.Main:app --reload --port 8000
```

- ✅ Port conflict resolved  
- ❌ Fixed Domain import error (PYTHONPATH=.)
- ⏳ Starting with correct Python path...

## ⏳ Step 2: Test Interface

- [ ] Visit http://localhost:8000/
- [ ] Select difficulty level → verify pill highlights
- [ ] Adjust duration → verify display updates
- [ ] Enter topic (3+ chars) → Generate button enables
- [ ] Click Generate → redirects to approval

## 🔍 Step 3: Verify Backend

- [ ] Check browser console (F12) for errors
- [ ] Test API directly: curl -X POST http://localhost:8000/courses/generate/course-template -d '{"title":"test","level":"beginner","duration_months":3}' -H 'Content-Type: application/json'

## ✅ Done

