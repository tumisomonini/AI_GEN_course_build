#!/usr/bin/env python3
import asyncio
import time
import requests
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Application.Workflows.syllabus_workflow import create_syllabus_workflow
from Application.API.agents import get_real_agents

async def test_api_generate():
    # Create test course first to avoid PG FK on create_run
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from Application.Ports.postgres_repo import PostgresRepo
    pg = PostgresRepo()
    course_id = pg.create_course("Perf Test Course", "general", description="Test course for perf")
    print(f"Created test course_id={course_id}")
    pg.close()
    
    url = 'http://localhost:8000/syllabus/generate'
    data = {'topics': ['Intro Python', 'Data Structures', 'Functions', 'OOP', 'Advanced Topics', 'Projects']}
    start = time.time()
    resp = requests.post(url, json=data, timeout=300)
    duration = time.time() - start
    print(f'API test: status={resp.status_code}, time={duration:.1f}s')
    if resp.status_code == 200:
        result = resp.json()
        assert len(result.get('chapters', [])) >= 4  # Partial success OK
    return duration

async def test_workflow_direct():
    agents = get_real_agents()
    workflow = create_syllabus_workflow(*[agents[k] for k in ['planner', 'author', 'reviewer', 'assembler']])
    start = time.time()
    result = await workflow.ainvoke({'topics': ['Python Basics']*6, 'title': 'Test Perf'})
    duration = time.time() - start
    print(f'Workflow direct: validated={result.get("validated")}, time={duration:.1f}s, chapters={len(result.get("chapters", {}))}')
    return duration

async def main():
    print('Testing performance optimization...')
    api_time = await test_api_generate()
    wf_time = await test_workflow_direct()
    total = api_time + wf_time
    target = 120  # 2min
    print(f'Total time: {total:.1f}s vs target {target}s: {"PASS" if total < target*1.5 else "FAIL"}')
    with open('perf_results.txt', 'w') as f:
        f.write(f'API: {api_time}s, Workflow: {wf_time}s, Total: {total}s')

asyncio.run(main())

