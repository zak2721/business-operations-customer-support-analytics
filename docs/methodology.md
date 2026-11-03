# Methodology

## 1. Data generation (`src/data_generation/`)

The synthetic company is a mid-sized e-commerce / SaaS business with six support departments, 60 agents, 3,200 customers and 13 operational processes, simulated for **1 Jan 2023 – 31 Dec 2025** (snapshot 31 Dec 2025 23:59:59).

The simulation is driven by explicit, documented assumptions (`reference_data.py`) so that relationships in the data have a cause that can be explained:

| Mechanism | Effect in the data |
|---|---|
| Growth trend + Nov/Dec seasonality + weekday/hour profile | realistic volume curves and day × hour heatmap |
| Category → department mapping, priority/channel mixes | consistent ownership and demand mix |
| Agent eligibility (hired before, not yet left) | no ticket is assigned to an agent who did not work there |
| Workload factor (tickets per active agent per month vs department norm) | heavier months resolve more slowly |
| Experience multipliers | juniors slower, more reopenings and escalations |
| Channel effects | async channels slower to first response; out-of-hours delay until next business morning |
| April 2025 pricing change + two Billing departures (Feb/Mar 2025) | Billing volume ↑, Billing SLA ↓, Billing outsourcing cost ↑ |
| Refund Approval failure drift; Payment Reconciliation step change (Apr 2025); Shipment Dispatch Q4 slowdown | operational bottlenecks to discover |
| CSAT generated from SLA outcome, first-response time, reopen, escalation, FCR, channel, agent skill + noise | satisfaction relationships with realistic noise |
| Churn probability rises with low CSAT (weakly) | a weak, honest association |

Ticket status is derived from simulated timings relative to the snapshot: tickets whose simulated resolution falls after the snapshot are Open/In Progress/Pending; open tickets therefore never carry a resolution date. A small share of recent tickets are deliberately left stalled to create an aging backlog.

**Defect injection.** After the clean simulation, a separate step copies the tables and injects realistic defects (exact duplicates, missing values, label variants, legacy date formats, impossible timestamps, out-of-range scores, orphan keys, cost sign errors and outliers, broken totals). Exact counts are written to `data/raw/_generation_manifest.json`, which the test suite uses to prove that cleaning detects every defect.

## 2. Cleaning and validation (`src/data_cleaning/`, `src/data_validation/`)

Order: departments → agents → customers → tickets → feedback → operations → costs → performance → calendar (parents before children so foreign keys can be checked).

Action vocabulary and principles:

* **removed** — exact duplicates; feedback whose ticket does not exist (cannot be attributed).
* **corrected** — value derivable from other fields (region from country, SLA target from priority, successful = total − failed, total = direct + indirect, sign errors).
* **imputed** — estimated value plus a flag column (CLV by segment median, processing time by process-month median, cost outliers by process-month median unit cost).
* **flagged** — kept, problem value nulled, flag column added (impossible timestamps, unknown agent, out-of-range CSAT).
* CSAT is **never imputed**; raw files are **never modified**.

Quality score per table = 0.4 × completeness + 0.3 × uniqueness + 0.3 × validity. The full log and scores are in `data/reports/data_quality_report.md`.

## 3. Feature engineering (`src/feature_engineering/`)

Ticket-level flags (`is_resolved`, `sla_eligible`, `sla_met`, `is_fcr`, `is_repeat_contact`, aging buckets ...) are created once and reused by every layer, so denominators cannot drift between Python, SQL and Power BI. `tickets_enriched` adds customer, agent, department and survey attributes with a 1:1 join (row count asserted).

## 4. Exploratory analysis

Aggregations live in `src/analytics/eda.py`; plotting in `src/visualization/`. Charts use a colour-vision-deficiency-checked palette in a fixed order, one y-axis per chart, and status colours (good/warning/critical) reserved for SLA and success states. Seven notebooks are generated from `notebooks/build_notebooks.py` and executed end-to-end so all outputs are real.

## 5. Statistical analysis (`src/analytics/statistics.py`)

| Question | Method | Why this method |
|---|---|---|
| Are time metrics and CSAT related? | Spearman rank correlation (Pearson reported too) | time metrics are heavily skewed; CSAT is ordinal |
| Is SLA breach independent of priority / channel / category / segment? | Chi-square test of independence + Cramér's V | categorical × categorical; V gives effect size |
| Do two groups differ (e.g. CSAT within SLA vs breached)? | Mann-Whitney U (primary), Welch's t-test (secondary), rank-biserial effect size | no normality assumption; unequal variances |
| Do 6 channels differ in resolution time? | Kruskal-Wallis | non-parametric k-group test |
| How precise are group averages? | t-based 95% CI for CSAT; Wilson 95% CI for SLA proportions | Wilson is accurate near 0/100% |
| Did Billing SLA change 2024 → 2025? | two-proportion z-test | |
| Which factors are associated with CSAT holding others constant? | OLS with HC3 robust standard errors | interpretable; CSAT treated as approximately interval |
| Which ticket attributes are associated with SLA breach? | logistic regression, odds ratios with 95% CI | binary outcome |

**Assumptions and caveats.** Observations are treated as independent, but tickets from the same customer or agent are correlated, so p-values are optimistic. With thousands of observations almost everything is "significant"; conclusions rely on **effect sizes**. All results are associations in synthetic data; none establish causation.

## 6. Root-cause analysis (`src/analytics/root_cause.py`)

For each adverse outcome (SLA breach, long resolution > P90, CSAT ≤ 2, reopen, escalation, operational failure) the outcome rate is computed in every level of eight candidate factors and compared with the baseline (**lift**). Levels are ranked by **excess cases** (cases above what the baseline rate would predict), which balances rate and volume. Cost growth is split into **volume** and **unit-cost** effects with a price-volume decomposition: ΔC = (V₁ − V₀)·P₀ + (P₁ − P₀)·V₁.

## 7. Predictive model (`src/analytics/predictive.py`)

* **Target:** SLA breach for resolved tickets.
* **Features:** only what is known when a ticket is created (priority, category, subcategory, channel, department, calendar, agent experience, agent's trailing 7-day assignments computed strictly from past tickets, customer's prior contact history).
* **Excluded as leakage:** first response time, reopen count, escalation, resolution type, CSAT, resolution time.
* **Validation:** time-based split (train 2023-2024, test 2025); `TimeSeriesSplit` 5-fold CV on the training period; decision threshold chosen on a 2024-H2 validation slice, never on test.
* **Models:** logistic regression (baseline) and histogram gradient boosting; selected by test ROC-AUC.
* **Reported:** ROC-AUC, PR-AUC, precision, recall, F1, confusion matrix, permutation importance, breach rate by risk decile.

## 8. Insights

`src/analytics/insights.py` computes every number quoted in `reports/business_insights.md`. Each insight separates the **observed finding** and **evidence** (computed) from the **hypothesis**, **action** and **expected outcome** (analyst judgement, phrased as a measurable direction, never as a promised saving).
