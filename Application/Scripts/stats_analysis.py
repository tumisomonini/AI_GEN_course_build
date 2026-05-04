#!/usr/bin/env python3
import json
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Try to connect PG for metrics table (optional, global instance)
pg_repo_instance = None
pg_connected = False
try:
    from Application.Ports.postgres_repo import PostgresRepo
    pg_repo_instance = PostgresRepo()
    with pg_repo_instance.get_cursor() as cur:
        cur.execute("SELECT 1")
    pg_connected = True
    print('✅ Postgres connection established for metrics.')
except Exception as e:
    print(f'⚠️ Postgres optional connect failed: {e}')
    pg_connected = False


PERF_FILE = Path(__file__).parent / 'perf_results.txt'
RESULTS_JSON = Path(__file__).parent / 'stats_report.json'
RESULTS_MD = Path(__file__).parent / 'stats_report.md'
PLOTS_DIR = Path(__file__).parent / 'stats_plots'
PLOTS_DIR.mkdir(exist_ok=True)


def load_perf_json(file_path):
    """Load performance results from JSON file."""
    with open(file_path) as f:
        data = json.load(f)
    return data


def compute_stats(timings):
    arr = np.array(timings, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    sem = stats.sem(arr)
    ci_low, ci_high = stats.t.interval(0.95, len(arr) - 1, loc=mean, scale=sem)
    return {
        'mean': mean,
        'std': std,
        'sem': float(sem),
        'ci_95': [float(ci_low), float(ci_high)],
        'n': len(arr)
    }


def cohens_d(group1, group2):
    """Compute Cohen's d effect size for two independent groups."""
    arr1 = np.array(group1, dtype=float)
    arr2 = np.array(group2, dtype=float)
    n1, n2 = len(arr1), len(arr2)
    s1, s2 = np.var(arr1, ddof=1), np.var(arr2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return float((np.mean(arr1) - np.mean(arr2)) / pooled_std)


def shapiro_wilk(data, name="data"):
    """Shapiro-Wilk normality test."""
    arr = np.array(data, dtype=float)
    if len(arr) < 3:
        return {'test': 'Shapiro-Wilk', 'W': None, 'p': None, 'note': 'insufficient data'}
    W, p = stats.shapiro(arr)
    return {'test': 'Shapiro-Wilk', 'W': round(float(W), 4), 'p': round(float(p), 4),
            'normal': p > 0.05}


def ascii_hist(data, bins=10):
    hist, edges = np.histogram(data, bins=bins)
    max_h = max(hist) if len(hist) > 0 and max(hist) > 0 else 1
    for i, h in enumerate(hist):
        bar = '*' * int(20 * h / max_h)
        print(f'{edges[i]:.1f}-{edges[i+1]:.1f}: {bar} ({h})')


def plot_histograms(api_t, wf_t, tot_t):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].hist(api_t, bins=8, color='steelblue', edgecolor='black')
    axes[0].set_title('API Latency Distribution')
    axes[0].set_xlabel('Seconds')
    axes[0].set_ylabel('Frequency')

    axes[1].hist(wf_t, bins=8, color='coral', edgecolor='black')
    axes[1].set_title('Workflow Latency Distribution')
    axes[1].set_xlabel('Seconds')

    axes[2].hist(tot_t, bins=8, color='seagreen', edgecolor='black')
    axes[2].set_title('Total Latency Distribution')
    axes[2].set_xlabel('Seconds')

    plt.tight_layout()
    path = PLOTS_DIR / 'histograms.png'
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'📊 Histograms saved to {path}')
    return str(path)


def plot_boxplot(api_t, wf_t):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot([api_t, wf_t], tick_labels=['API', 'Workflow'])
    ax.set_title('Latency Boxplot Comparison')
    ax.set_ylabel('Seconds')
    plt.tight_layout()
    path = PLOTS_DIR / 'boxplot.png'
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'📊 Boxplot saved to {path}')
    return str(path)


def plot_ci_errorbars(api_stats, wf_stats, tot_stats):
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ['API', 'Workflow', 'Total']
    means = [api_stats['mean'], wf_stats['mean'], tot_stats['mean']]
    ci_lows = [api_stats['ci_95'][0], wf_stats['ci_95'][0], tot_stats['ci_95'][0]]
    ci_highs = [api_stats['ci_95'][1], wf_stats['ci_95'][1], tot_stats['ci_95'][1]]
    errs = [[m - l for m, l in zip(means, ci_lows)],
            [h - m for m, h in zip(means, ci_highs)]]

    ax.errorbar(labels, means, yerr=errs, fmt='o', capsize=8, color='darkblue', ecolor='gray')
    ax.set_title('Mean Latency with 95% Confidence Intervals')
    ax.set_ylabel('Seconds')
    ax.axhline(120, color='red', linestyle='--', label='Target (120s)')
    ax.legend()
    plt.tight_layout()
    path = PLOTS_DIR / 'ci_errorbars.png'
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'📊 CI errorbars saved to {path}')
    return str(path)


def query_pg_metrics():
    """Query latest run metrics and overall summary from Postgres."""
    metrics = {}
    if not pg_connected or not pg_repo_instance:
        return metrics

    try:
        with pg_repo_instance.get_cursor() as cur:
            # Latest run_id
            cur.execute("SELECT MAX(run_id) FROM metrics")
            row = cur.fetchone()
            latest_run_id = row[0] if row and row[0] else None

            if latest_run_id:
                cur.execute(
                    "SELECT metric_name, value FROM metrics WHERE run_id = %s ORDER BY metric_id",
                    (latest_run_id,)
                )
                latest_metrics = cur.fetchall()
                metrics['latest_run_id'] = latest_run_id
                metrics['latest'] = {name: float(val) for name, val in latest_metrics}

            # Summary by metric_name
            cur.execute(
                """SELECT metric_name, AVG(value), STDDEV(value), COUNT(*)
                   FROM metrics GROUP BY metric_name"""
            )
            summary = cur.fetchall()
            metrics['summary'] = [
                {'metric': name, 'mean': float(avg), 'std': float(std) if std else 0.0, 'count': int(cnt)}
                for name, avg, std, cnt in summary
            ]
    except Exception as e:
        print(f'⚠️ PG metrics query failed: {e}')
    return metrics


def build_report(data, api_stats, wf_stats, tot_stats, ttest, effect_size, normality, pg_metrics, plot_paths):
    target = 120
    total_mean = tot_stats['mean']
    target_pass = total_mean < target

    report = {
        'source': str(PERF_FILE),
        'target_seconds': target,
        'target_pass': target_pass,
        'api': {
            'timings': data['api']['timings'],
            **api_stats,
            'normality': normality['api']
        },
        'workflow': {
            'timings': data['workflow']['timings'],
            **wf_stats,
            'normality': normality['workflow']
        },
        'total': {
            'timings': tot_stats.get('timings', []),
            **tot_stats
        },
        'ttest_api_wf': {
            't': round(float(ttest.statistic), 4),
            'p': round(float(ttest.pvalue), 4),
            'significant': ttest.pvalue < 0.05
        },
        'effect_size': {
            'cohens_d': round(effect_size, 4),
            'interpretation': (
                'negligible' if abs(effect_size) < 0.2 else
                'small' if abs(effect_size) < 0.5 else
                'medium' if abs(effect_size) < 0.8 else
                'large'
            )
        },
        'pg_metrics': pg_metrics,
        'plots': plot_paths,
        'overall_scores': data.get('overall', {})
    }
    return report


def write_md_report(report, md_path):
    lines = [
        "# Performance Statistical Analysis\n",
        f"**Source:** `{report['source']}`  \n",
        f"**Target Latency:** {report['target_seconds']}s — **{'PASS ✅' if report['target_pass'] else 'FAIL ❌'}**\n",
        "\n## Descriptive Statistics\n",
        "| Metric | Mean (s) | Std (s) | SEM | 95% CI | N |",
        "|--------|----------|---------|-----|--------|---|",
    ]
    for key in ['api', 'workflow', 'total']:
        s = report[key]
        lines.append(
            f"| {key.upper()} | {s['mean']:.2f} | {s['std']:.2f} | {s.get('sem', 0):.2f} | "
            f"[{s['ci_95'][0]:.2f}, {s['ci_95'][1]:.2f}] | {s['n']} |"
        )

    t = report['ttest_api_wf']
    lines.extend([
        "\n## Inferential Statistics\n",
        f"- **t-test (API vs Workflow):** t = {t['t']}, p = {t['p']} ({'significant' if t['significant'] else 'not significant'})\n",
        f"- **Cohen's d:** {report['effect_size']['cohens_d']} ({report['effect_size']['interpretation']})\n",
    ])

    for key in ['api', 'workflow']:
        n = report[key]['normality']
        if n.get('W') is not None:
            lines.append(
                f"- **Shapiro-Wilk ({key.upper()}):** W = {n['W']}, p = {n['p']} ({'normal' if n['normal'] else 'non-normal'})\n"
            )

    lines.extend(["\n## Postgres Metrics\n"])
    if report['pg_metrics']:
        if 'summary' in report['pg_metrics']:
            lines.append("| Metric | Mean | Std | Count |")
            lines.append("|--------|------|-----|-------|")
            for s in report['pg_metrics']['summary']:
                lines.append(f"| {s['metric']} | {s['mean']:.4f} | {s['std']:.4f} | {s['count']} |")
    else:
        lines.append("_No Postgres metrics available._\n")

    lines.extend(["\n## Plots\n"])
    for p in report['plots'].values():
        lines.append(f"- `{Path(p).name}`\n")

    lines.extend(["\n## Overall Scores (from perf_test)\n"])
    scores = report.get('overall_scores', {})
    for k, v in scores.items():
        lines.append(f"- **{k}:** {v}\n")

    with open(md_path, 'w') as f:
        f.writelines(lines)
    print(f'📝 Markdown report saved to {md_path}')


def main():
    print('Statistical Analysis of Performance Data')

    # Load JSON performance data
    try:
        data = load_perf_json(PERF_FILE)
    except Exception as e:
        print(f"❌ Failed to load {PERF_FILE}: {e}")
        return

    api_t = np.array(data['api']['timings'], dtype=float)
    wf_t = np.array(data['workflow']['timings'], dtype=float)
    tot_t = api_t + np.mean(wf_t)  # approx total per API iteration

    print('\nAPI Timings:', api_t.tolist())
    print('WF Timings:', wf_t.tolist())

    # Stats
    api_stats = compute_stats(api_t)
    wf_stats = compute_stats(wf_t)
    tot_stats = compute_stats(tot_t)

    # t-test
    ttest = stats.ttest_ind(api_t, wf_t)

    # Cohen's d
    effect_size = cohens_d(api_t, wf_t)

    # Shapiro-Wilk
    normality = {
        'api': shapiro_wilk(api_t, 'API'),
        'workflow': shapiro_wilk(wf_t, 'Workflow')
    }

    # Plots
    plot_paths = {
        'histograms': plot_histograms(api_t, wf_t, tot_t),
        'boxplot': plot_boxplot(api_t, wf_t),
        'ci_errorbars': plot_ci_errorbars(api_stats, wf_stats, tot_stats)
    }

    # PG metrics
    pg_metrics = query_pg_metrics()
    if pg_metrics:
        print('\nPG Metrics Summary:', pg_metrics.get('summary', []))

    # Build report
    report = build_report(data, api_stats, wf_stats, tot_stats, ttest, effect_size, normality, pg_metrics, plot_paths)

    with open(RESULTS_JSON, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print('\n📄 JSON report saved to', RESULTS_JSON)

    write_md_report(report, RESULTS_MD)

    print('\n=== STATS ===')
    print('API:', api_stats)
    print('Workflow:', wf_stats)
    print('Total:', tot_stats)
    print(f"t-test (API vs WF): t={round(float(ttest.statistic),3)}, p={round(float(ttest.pvalue),3)}")
    print(f"Cohen's d: {effect_size:.3f} ({report['effect_size']['interpretation']})")
    print(f"\nTotal vs Target {report['target_seconds']}s: {'PASS' if report['target_pass'] else 'FAIL'}")
    print('\nAPI Histogram:')
    ascii_hist(api_t)

    if pg_repo_instance:
        pg_repo_instance.close()


if __name__ == '__main__':
    main()

