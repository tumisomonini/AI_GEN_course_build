#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, '.')
from Application.Workflows.syllabus_workflow import run_full_workflow
from Domain.syllabus import SyllabusInput

async def main():
    print("🚀 AI Course Generation CLI Demo")
    print("OpenRouter keys loaded. Enter course details:")
    
    title = input("Course title: ").strip()
    if not title:
        print("❌ Invalid title")
        return
    
    duration_str = input("Duration (months, e.g. 3): ").strip()
    duration = int(duration_str) if duration_str.isdigit() else 3
    
    level = input("Level (beginner/intermediate/advanced): ").strip() or "beginner"
    
    print("\\n📝 Scraping syllabus...")
    input_data = SyllabusInput(title=title, duration_months=duration, level=level)
    
    print("🎓 Running full agent workflow (Planner → Author → Reviewer → Assembler)...")
    result = await run_full_workflow(input_data)
    
    print("\\n✅ Course generated!")
    print("Title:", result.title if result else "N/A")
    print("Chapters:", len(result.chapters) if result and result.chapters else 0)
    print("Status:", result.status if result else "Failed")
    
    if result and result.chapters:
        for i, ch in enumerate(result.chapters[:3], 1):
            print(f"Chapter {i}: {ch.title[:80]}...")
    
    print("\\nRun `./run_dev.sh` for full web dashboard.")

if __name__ == '__main__':
    asyncio.run(main())

