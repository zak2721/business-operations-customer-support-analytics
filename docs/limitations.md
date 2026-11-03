# Limitations

## Data

* **Synthetic data.** Every record is simulated. Patterns exist because the simulation was designed to contain them (see `docs/methodology.md` §1). The project demonstrates *method*; its findings are not facts about any real company.
* **Simplified support process.** One agent per ticket, no hand-offs between agents, no ticket-level interaction count (FCR is defined via resolution type + no reopen + no escalation), no business-hours SLA clocks (SLA is measured in calendar hours).
* **Agent workload hours** are simulated from ticket handling time plus a random admin allowance; Average Handling Time therefore includes admin time.
* **Customer status** is a single snapshot value; there is no churn date, so churn cannot be modelled as a time-to-event outcome.
* **Costs.** Departmental budgets are flat across years while spend grows, which makes every department overspend by construction. Operational (transaction) cost and departmental (staffing) cost are separate concepts and are never summed together.
* **Comments** are drawn from a small template pool and are not suitable for text analytics.

## Analysis

* **Independence assumption.** Statistical tests treat tickets as independent; repeated tickets from one customer or agent violate this, so p-values are too small. Effect sizes are the meaningful output.
* **Correlation ≠ causation.** Root-cause "drivers" are where problems concentrate, not proven causes. Hypotheses in the insights must be validated (e.g. with process reviews or controlled pilots).
* **OLS on an ordinal outcome.** The CSAT regression is an interpretable approximation; an ordinal logit would be more rigorous.
* **Predictive model.** Performance on synthetic data says nothing about real-world performance. In production it would need recalibration, drift monitoring, fairness checks across segments, and a controlled pilot before use.

## Deliverables

* **Power BI.** No `.pbix` file is included: Power BI Desktop is Windows-only and was not available in the build environment. The model, DAX, Power Query M, theme, page designs and validation values are provided; the HTML prototype in `powerbi/dashboard_prototype/` reproduces the design with real numbers but is not a Power BI report.
* **Screenshots** in `screenshots/` are genuine captures of the HTML prototype and the Streamlit app, not of Power BI.
* **PostgreSQL** scripts were executed on PostgreSQL 16; other databases may need syntax changes (`FILTER`, `PERCENTILE_CONT ... WITHIN GROUP`, `generate_series`).

## Future improvements

* Business-hours SLA clocks and holiday calendars.
* Interaction-level data (messages, hand-offs) for true FCR and handling-time measurement.
* Ordinal regression for CSAT; mixed-effects models with agent and customer random effects.
* Survival analysis of time-to-resolution and of churn (requires churn dates).
* Text analytics on real feedback comments.
* Incremental loading (dbt or Airflow) and a scheduled Power BI refresh against PostgreSQL.
* Deploy the Streamlit app (Streamlit Community Cloud / Docker) and publish the Power BI report to the Power BI Service.
