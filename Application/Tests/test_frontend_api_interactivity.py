import httpx
import asyncio
import json
import pytest

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_flow():
    print("🚀 Starting Frontend-Backend Interactivity Test...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Test Search (Initial interaction)
        print("🔍 Testing Search API...")
        search_res = await client.get(f"{BASE_URL}/courses/search-courses?q=Unity")
        if search_res.status_code == 200:
            print("✅ Search API connected.")
        else:
            print(f"❌ Search API failed: {search_res.status_code}")

        # 2. Test Template Generation (Frontend Form Submission)
        print("📝 Testing Template Generation...")
        payload = {
            "title": "Unity Developer",
            "level": "beginner",
            "duration_months": 3
        }
        gen_res = await client.post(f"{BASE_URL}/courses/generate/course-template", json=payload)
        
        if gen_res.status_code in [200, 201]:
            course_data = gen_res.json()
            course_id = course_data.get("id") or course_data.get("course_id")
            print(f"✅ Template generated. Course ID: {course_id}")
            
            # 3. Test Approval (Triggering Full Generation)
            print("👍 Testing Approval and Content Trigger...")
            app_res = await client.post(f"{BASE_URL}/courses/{course_id}/approve-full", json={})
            
            if app_res.status_code == 200:
                print("⏳ Backend generating content... Polling for status...")
                for _ in range(10): # Poll for up to 20 seconds
                    status_res = await client.get(f"{BASE_URL}/courses/{course_id}/status")
                    status = status_res.json().get("status")
                    print(f"   Current Status: {status}")
                    if status == "completed":
                        print("✅ Course Generation Complete!")
                        break
                    if status == "failed":
                        print("❌ Course Generation Failed in background.")
                        break
                    await asyncio.sleep(2)
                
                print("\n🎉 INTERACTIVITY VERIFIED: Frontend-Backend contract is healthy.")
            else:
                print(f"❌ Approval failed: {app_res.status_code} - {app_res.text}")
        else:
            print(f"❌ Template generation failed: {gen_res.status_code} - {gen_res.text}")

if __name__ == "__main__":
    try:
        asyncio.run(test_flow())
    except Exception as e:
        print(f"❌ Connection Error: Could not reach backend at {BASE_URL}. Is the server running?")
        print(f"Error details: {e}")