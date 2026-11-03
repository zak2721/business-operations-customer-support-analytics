"""Execute every SQL script against PostgreSQL and document the results.

Run (after ``python -m src.database.load_postgres``):
    python -m src.database.run_sql

1. Creates the reporting views (sql/09_reporting_views).
2. Parses each analysis file into individual queries using ``-- @query`` headers.
3. Executes every query, saves full results to data/reports/sql_results/<id>.csv.
4. Writes docs/SQL_documentation.md with purpose, techniques and a real result
   preview for each query.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import pandas as pd

from src import config
from src.database.load_postgres import connect, run_sql_file

QUERY_DIRS = ["03_data_quality", "04_customer_analysis", "05_customer_support_analysis", "06_agent_performance",
              "07_business_operations", "08_advanced_analytics"]
RESULTS_DIR = config.REPORTS_DATA_DIR / "sql_results"


@dataclass
class SqlQuery:
    qid: str
    title: str
    question: str
    techniques: str
    sql: str
    file: str
    result: pd.DataFrame | None = field(default=None, repr=False)
    seconds: float = 0.0


def parse_file(path) -> list[SqlQuery]:
    text = path.read_text()
    blocks = re.split(r"(?m)^-- @query ", text)[1:]
    out = []
    for b in blocks:
        meta = dict(re.findall(r"(?m)^-- @(\w+) (.*)$", "-- @query " + b))
        sql = "\n".join(l for l in b.splitlines()[1:] if not l.startswith("-- @")).strip()
        out.append(SqlQuery(qid=b.splitlines()[0].strip(), title=meta.get("title", ""), question=meta.get("question", ""),
                            techniques=meta.get("techniques", ""), sql=sql, file=str(path.relative_to(config.PROJECT_ROOT))))
    return out


def all_queries() -> list[SqlQuery]:
    qs = []
    for d in QUERY_DIRS:
        for f in sorted((config.SQL_DIR / d).glob("*.sql")):
            qs.extend(parse_file(f))
    return qs


def execute_all() -> list[SqlQuery]:
    conn = connect()
    run_sql_file(conn, config.SQL_DIR / "09_reporting_views" / "01_reporting_views.sql")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    qs = all_queries()
    for q in qs:
        t0 = time.perf_counter()
        q.result = pd.read_sql_query(q.sql, conn)
        q.seconds = time.perf_counter() - t0
        q.result.to_csv(RESULTS_DIR / f"{q.qid.replace('.', '_')}.csv", index=False)
    conn.close()
    return qs


def _preview(df: pd.DataFrame, n: int = 6) -> str:
    d = df.head(n).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:,.2f}")
    d = d.astype(str)
    cols = list(d.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(r) + " |" for r in d.itertuples(index=False)]
    return "\n".join(lines)


def write_docs(qs: list[SqlQuery]) -> None:
    techniques = sorted({t.strip() for q in qs for t in q.techniques.split(",")})
    n_analytical = sum(1 for q in qs if q.qid.startswith("Q"))
    md = ["# SQL Documentation", "",
          "PostgreSQL 16 analytical layer. **Every query below was executed against the loaded database** by "
          "`python -m src.database.run_sql`; the previews are the first rows of the real output and the full results "
          "are saved in `data/reports/sql_results/`.", "",
          f"* Analytical queries: **{n_analytical}**  ·  data-quality checks: **{len(qs) - n_analytical}**  ·  reporting views: **11**",
          "* Schema: `sql/01_database_setup/` (3NF tables, PK/FK, CHECK constraints for business rules, indexes)",
          "* Loading: `python -m src.database.load_postgres` (COPY from `data/processed/`, row counts verified)",
          "* KPI definitions are identical to `src/kpi/kpis.py` and `powerbi/dax_measures.dax`; `tests/test_sql.py` asserts SQL = Python.", "",
          "## How to run", "", "```bash",
          "cp .env.example .env            # set PGHOST / PGUSER / PGPASSWORD",
          "python -m src.database.load_postgres   # creates DB + schema, loads data, builds indexes",
          "python -m src.database.run_sql         # creates views, runs every query, regenerates this file",
          "```", "", "## Schema overview", "",
          "| Table | Grain | Key constraints |", "|---|---|---|",
          "| departments | department | PK department_id, budget ≥ 0 |",
          "| agents | agent | PK agent_id, FK department, experience/status domains |",
          "| customers | customer | PK customer_id, segment/type/status domains, CLV ≥ 0 |",
          "| calendar | day | PK date |",
          "| support_tickets | ticket | PK, FKs, priority/status/channel domains, chronology checks, SLA target = f(priority) |",
          "| customer_feedback | survey | PK, **UNIQUE ticket_id** (prevents CSAT double counting), CSAT 1-5, rating 1-10 |",
          "| operations | process-day | PK, UNIQUE (date, process), success + failed = total, cost ≥ 0 |",
          "| agent_performance | agent-month | PK, UNIQUE (agent, month), SLA % 0-100 |",
          "| business_costs | dept-month-category | PK, UNIQUE, total = direct + indirect |", "",
          "## Reporting views (`sql/09_reporting_views/01_reporting_views.sql`)", "",
          "| View | Purpose |", "|---|---|",
          "| v_ticket_metrics | ticket grain + FRT/resolution hours, SLA/FCR/repeat flags, age, CSAT |",
          "| v_kpi_summary | single-row headline KPIs |",
          "| v_monthly_support_kpis | monthly volume, FRT, resolution, SLA, FCR, CSAT |",
          "| v_department_sla | SLA by department and year |",
          "| v_agent_scorecard | per-agent volume, productivity, SLA, reopen, CSAT |",
          "| v_channel_performance | per-channel KPIs |",
          "| v_backlog_aging | open tickets by age bucket |",
          "| v_operations_monthly / v_process_performance | operations by month / process |",
          "| v_cost_by_department_month | departmental cost vs monthly budget |",
          "| v_customer_360 | customer-level support profile (no contact details) |", "",
          "## SQL techniques covered", "", ", ".join(f"`{t}`" for t in techniques), "", "## Query catalogue", "",
          "| ID | Title | Rows | File |", "|---|---|---:|---|"]
    md += [f"| [{q.qid}](#{q.qid.lower().replace('.', '')}) | {q.title} | {len(q.result)} | `{q.file}` |" for q in qs]
    for q in qs:
        md += ["", f"### {q.qid}", "", f"**{q.title}**", "", f"* **Business question:** {q.question}",
               f"* **Techniques:** {q.techniques}", f"* **Result:** {len(q.result)} rows in {q.seconds*1000:.0f} ms",
               "", "<details><summary>SQL</summary>", "", "```sql", q.sql, "```", "", "</details>", "",
               _preview(q.result)]
    (config.PROJECT_ROOT / "docs" / "SQL_documentation.md").write_text("\n".join(md) + "\n")


def main() -> None:
    qs = execute_all()
    write_docs(qs)
    print(f"Executed {len(qs)} queries ({sum(q.qid.startswith('Q') for q in qs)} analytical). Docs written.")


if __name__ == "__main__":
    main()
