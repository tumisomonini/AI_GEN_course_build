# Statistical Analysis Implementation Tracker

## Plan Breakdown & Progress:

### 1. Edit perf_test.py (Add raw timings to JSON, PG logging, 10x API/5x WF iterations)
- [ ] a. Update test_api_generate: Save timings list to metrics dict
- [ ] b. Update test_workflow_direct: Same for WF
- [ ] c. In main(): Append 'raw_timings_api': timings, 'raw_timings_wf': timings to report JSON
- [ ] d. Add PG logging: pg.log_metric(run_id, 'api_latency', timing) per iteration
- [ ] e. Increase iterations: API=10, WF=5

### 2. Edit stats_analysis.py (Plots, PG expansion, JSON parsing)
- [ ] a. Import matplotlib.pyplot as plt; save figs as PNG
- [ ] b. Load full JSON perf_results.txt with timings lists (no regex)
- [ ] c. Plot: Histograms (API/WF/total), boxplot comparison, CI errorbars
- [ ] d. PG: Query by latest run_id, all metrics summary table
- [ ] e. Add Cohen's d effect size, Shapiro-Wilk normality test

### 3. Final Verification
- [ ] Run perf_test.py → Check JSON has raw_timings
- [ ] Run stats_analysis.py → Verify plots/reports with real data
- [ ] Update tracker to [x] on completion

**Current: Starting edits...**

