#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, '.')
from Application.Workflows import create_real_syllabus_workflow
from Domain.syllabus import SyllabusState  # Pylance may need reload; runtime uses sys.path
from typing import Any

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
    input_data = SyllabusState(title=title, duration_months=duration, level=level)
    
    print("🎓 Running full agent workflow (Planner → Author → Reviewer → Assembler)...")
    result_dict, _ = await create_real_syllabus_workflow(
        title=input_data.title,
        duration_months=input_data.duration_months,
        level=input_data.level
    )
    result: Any = result_dict if result_dict else None
    
    print("\\n✅ Course generated!")
    print("Title:", result.get("title", "N/A") if result else "N/A")
    print("Chapters:", len(result.get("chapters", [])) if result and "chapters" in result else 0)
    print("Status:", result.get("status", "Failed") if result else "Failed")
    
    if result and result.get("chapters"):
        for i, ch in enumerate(result["chapters"][:3], 1):
            print(f"Chapter {i}: {ch.get('title', 'Untitled')[:80]}...")
    
    print("\\nRun `./run_dev.sh` for full web dashboard.")

if __name__ == '__main__':
    asyncio.run(main())

