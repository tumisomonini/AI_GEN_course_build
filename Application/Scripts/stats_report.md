# Performance Statistical Analysis
**Source:** `/Users/tumiso_monini/Documents/GitHub/AI_GEN_course_build/Application/Scripts/perf_results.txt`  
**Target Latency:** 120s — **PASS ✅**

## Descriptive Statistics
| Metric | Mean (s) | Std (s) | SEM | 95% CI | N ||--------|----------|---------|-----|--------|---|| API | 11.04 | 1.33 | 0.42 | [10.09, 12.00] | 10 || WORKFLOW | 32.18 | 3.44 | 1.54 | [27.91, 36.45] | 5 || TOTAL | 43.22 | 1.33 | 0.42 | [42.27, 44.18] | 10 |
## Inferential Statistics
- **t-test (API vs Workflow):** t = -17.4789, p = 0.0 (significant)
- **Cohen's d:** -9.5736 (large)
- **Shapiro-Wilk (API):** W = 0.9542, p = 0.7184 (normal)
- **Shapiro-Wilk (WORKFLOW):** W = 0.958, p = 0.7938 (normal)

## Postgres Metrics
| Metric | Mean | Std | Count ||--------|------|-----|-------|
## Plots
- `histograms.png`
- `boxplot.png`
- `ci_errorbars.png`

## Overall Scores (from perf_test)
- **latency_score:** 6.4
- **accuracy_score:** 9.17
- **ethical_score:** 10.0
- **context_score:** 10.0
- **cost_score:** 9.96
- **total_score:** 9.11
