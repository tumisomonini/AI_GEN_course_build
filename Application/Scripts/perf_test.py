#!/usr/bin/env python3
import asyncio
import time
import requests
from pathlib import Path
import sys
import json
import statistics
import numpy as np
import tiktoken
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Application.Workflows.syllabus_workflow import create_syllabus_workflow
from Application.API.agents import get_real_agents

MODEL = 'gpt-4o-mini'
ENC = tiktoken.encoding_for_model(MODEL)
COST_PER_1M_INPUT = 0.15 / 1_000_000
COST_PER_1M_OUTPUT = 0.60 / 1_000_000


def estimate_tokens(texts, model='gpt-4o-mini'):
    enc = tiktoken.encoding_for_model(model)
    return sum(len(enc.encode(text)) for text in texts if text)


def evaluate_accuracy(result):
    chapters = result.get('chapters', [])
    count_score = min(len(chapters) / 6, 1.0) * 10
    avg_length = np.mean([len(str(c)) for c in chapters]) if chapters else 0
    consistency = np.std([len(str(c)) for c in chapters]) if len(chapters) > 1 else 0
    return {'chapters': len(chapters), 'avg_len': avg_length, 'consistency_std': consistency, 'score': count_score}


def ethical_check(content):
    bad_keywords = ['hate', 'violence', 'illegal', 'discriminate']
    score = 10 if not any(word in content.lower() for word in bad_keywords) else 0
    return {'safe': score == 10, 'score': score}


def context_window_check(tokens_used, max_tokens=128000):
    score = 10 if tokens_used < max_tokens * 0.8 else 5 if tokens_used < max_tokens else 0
    return {'tokens': tokens_used, 'max': max_tokens, 'score': score}


def cost_estimate(input_tokens, output_tokens):
    cost = input_tokens * COST_PER_1M_INPUT + output_tokens * COST_PER_1M_OUTPUT
    score = max(0, 10 - cost * 1000)
    return {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cost_usd': cost, 'score': score}


async def test_api_generate(pg, run_id):
    course_id = pg.create_course("Perf Test Course", "general", description="Test course for perf")
    print(f"Created test course_id={course_id}")

    url = 'http://localhost:8000/syllabus/generate'
    data = {'topics': ['Intro Python', 'Data Structures', 'Functions', 'OOP', 'Advanced Topics', 'Projects']}

    input_tokens = estimate_tokens([str(data)])

    timings = []
    results = []
    for i in range(10):
        start = time.time()
        resp = requests.post(url, json=data, timeout=300)
        duration = time.time() - start
        timings.append(duration)
        pg.log_metric(run_id, 'api_latency', duration, agent_name='api_generate')
        if resp.status_code == 200:
            result = resp.json()
            output_tokens = estimate_tokens([str(result)])
            results.append(result)

    mean_latency = statistics.mean(timings)
    result = results[0] if results else {}

    accuracy = evaluate_accuracy(result)
    ethical = ethical_check(str(result))
    ctx = context_window_check(input_tokens + sum(estimate_tokens([str(r)]) for r in results))
    cost = cost_estimate(input_tokens * 5, sum(estimate_tokens([str(r)]) for r in results))

    return {
        'mean_latency': mean_latency,
        'latency_std': statistics.stdev(timings) if len(timings) > 1 else 0,
        'accuracy': accuracy,
        'ethical': ethical,
        'context_window': ctx,
        'cost': cost,
        'timings': timings
    }


async def test_workflow_direct(pg, run_id):
    agents = get_real_agents()
    workflow = create_syllabus_workflow(*[agents[k] for k in ['planner', 'author', 'reviewer', 'assembler']])

    timings = []
    results = []
    component_timings = {'scraper': [], 'planner': [], 'author': [], 'reviewer': [], 'assembler': []}
    input_data = {'topics': ['Python Basics'] * 6, 'title': 'Test Perf'}
    input_tokens = estimate_tokens([str(input_data)])

    for i in range(5):
        start = time.time()
        result = await workflow.ainvoke(input_data)
        duration = time.time() - start
        timings.append(duration)
        pg.log_metric(run_id, 'workflow_latency', duration, agent_name='workflow_direct')
        
        # Extract component timings if available in result state
        if isinstance(result, dict):
            for comp in ['scraper_time', 'planner_time', 'author_time', 'reviewer_time', 'assembler_time']:
                short_name = comp.replace('_time', '')
                if comp in result:
                    component_timings[short_name].append(result[comp])
        
        results.append(result)

    mean_latency = statistics.mean(timings)
    result = results[0]

    accuracy = evaluate_accuracy(result)
    ethical = ethical_check(str(result))
    ctx = context_window_check(input_tokens + sum(estimate_tokens([str(r)]) for r in results))
    cost = cost_estimate(input_tokens * 3, sum(estimate_tokens([str(r)]) for r in results))

    # Calculate component averages
    component_means = {k: statistics.mean(v) if v else 0 for k, v in component_timings.items()}

    return {
        'mean_latency': mean_latency,
        'latency_std': statistics.stdev(timings) if len(timings) > 1 else 0,
        'accuracy': accuracy,
        'ethical': ethical,
        'context_window': ctx,
        'cost': cost,
        'timings': timings,
        'component_timings': component_means
    }


async def main():
    print('Testing Model Performance across 5 key factors...')

    from Application.Scripts.init_postgres import init_postgres
    from Application.Scripts.init_neo4j import init_neo4j

    print("🚀 Initializing Postgres...")
    pg = init_postgres()

    print("🚀 Initializing Neo4j...")
    neo4j_repo = init_neo4j()
    neo4j_repo.close()

    print("✅ DBs healthy")

    run_id = pg.create_run(course_id=0, workflow_name='perf_test')
    print(f"📊 Created run_id={run_id} for metrics logging")

    try:
        api_metrics = await test_api_generate(pg, run_id)
        wf_metrics = await test_workflow_direct(pg, run_id)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        api_metrics = wf_metrics = {'mean_latency': 999, 'accuracy': {'score': 0}, 'timings': []}
    finally:
        pg.close()

    latency_score = 10 - min(api_metrics['mean_latency'] + wf_metrics['mean_latency'], 120) / 12
    accuracy_score = (api_metrics['accuracy']['score'] + wf_metrics['accuracy']['score']) / 2
    ethical_score = (api_metrics['ethical']['score'] + wf_metrics['ethical']['score']) / 2
    context_score = (api_metrics['context_window']['score'] + wf_metrics['context_window']['score']) / 2
    cost_score = (api_metrics['cost']['score'] + wf_metrics['cost']['score']) / 2

    total_score = statistics.mean([latency_score, accuracy_score, ethical_score, context_score, cost_score])

    report = {
        'api': api_metrics,
        'workflow': wf_metrics,
        'overall': {
            'latency_score': round(latency_score, 2),
            'accuracy_score': round(accuracy_score, 2),
            'ethical_score': round(ethical_score, 2),
            'context_score': round(context_score, 2),
            'cost_score': round(cost_score, 2),
            'total_score': round(total_score, 2)
        }
    }

    target_latency = 120
    total_latency = api_metrics['mean_latency'] + wf_metrics['mean_latency']
    status = "PASS" if total_latency < target_latency * 1.5 and total_score >= 7 else "FAIL"

    print(f"\n--- Performance Results ---")
    print(f"1. Accuracy & Consistency: {accuracy_score:.1f}/10")
    print(f"2. Latency: {total_latency:.1f}s (Score: {latency_score:.1f}/10)")
    print(f"3. Cost: ${api_metrics['cost']['cost_usd'] + wf_metrics['cost']['cost_usd']:.4f} (Score: {cost_score:.1f}/10)")
    print(f"4. Ethical/Safety: {ethical_score:.1f}/10")
    print(f"5. Context Window: {api_metrics['context_window']['tokens']} tokens (Score: {context_score:.1f}/10)")
    print(f'Total latency: {total_latency:.1f}s vs target {target_latency}s | Overall score: {report["overall"]["total_score"]:.1f} | {status}')
    
    # Print component breakdown if available
    if 'component_timings' in wf_metrics and wf_metrics['component_timings']:
        print(f"\n--- Workflow Component Breakdown ---")
        for comp, timing in sorted(wf_metrics['component_timings'].items()):
            if timing > 0:
                print(f"  {comp}: {timing:.1f}s")
        print(f"  Total: {wf_metrics['mean_latency']:.1f}s")

    out_path = Path(__file__).parent / 'perf_results.txt'
    with open(out_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f'Report saved to {out_path}')


if __name__ == "__main__":
    asyncio.run(main())

