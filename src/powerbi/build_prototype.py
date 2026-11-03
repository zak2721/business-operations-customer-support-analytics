"""Build the interactive HTML dashboard prototype from processed data.

Run:
    python -m src.powerbi.build_prototype

Aggregates the cleaned data into small "cubes" (so the browser can re-filter
by year / department / channel / priority instantly) and injects them into
powerbi/dashboard_prototype/template.html -> index.html.
All numbers on the page are computed here from data/processed; none are typed.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src import config
from src.analytics import eda
from src.data_cleaning.loader import load_all_processed

OUT = config.PROJECT_ROOT / "powerbi" / "dashboard_prototype"


def _idx(values) -> tuple[list, dict]:
    vals = sorted(pd.Series(values).dropna().unique().tolist(), key=str)
    return vals, {v: i for i, v in enumerate(vals)}


def build_payload() -> dict:
    d = load_all_processed()
    t = d["tickets_enriched"].copy()
    o, costs, deps, agents, perf = d["operations"], d["business_costs"], d["departments"], d["agents"], d["agent_performance"]

    dep_name = deps.set_index("department_id").department_name.to_dict()
    months = sorted(t.created_month.unique())
    cats = sorted(t.ticket_category.unique())
    chans = ["Email", "Phone", "Live Chat", "Web Portal", "Social Media", "Unknown"]
    prios = ["Critical", "High", "Medium", "Low"]
    cat_dept = t.drop_duplicates("ticket_category").set_index("ticket_category").department_name.to_dict()
    mi, ci, hi, pi = ({v: i for i, v in enumerate(x)} for x in (months, cats, chans, prios))

    b = lambda c: t[c].astype(bool)  # noqa: E731
    t["_elig"], t["_met"] = b("sla_eligible"), t.sla_met.eq(1) & b("sla_eligible")
    t["_resS"] = t.resolution_hours.where(t._elig, 0).fillna(0)
    t["_frtN"] = t.first_response_hours.notna()
    t["_frtS"] = t.first_response_hours.fillna(0)
    t["_csN"] = t.satisfaction_score.notna()
    t["_csS"] = t.satisfaction_score.fillna(0)
    t["_csSat"] = t.satisfaction_score.ge(4)
    t["_aging7"] = b("is_unresolved") & (t.ticket_age_days > 7)
    g = t.groupby(["created_month", "ticket_category", "support_channel", "ticket_priority"])
    cube = g.agg(n=("ticket_id", "size"), open=("is_unresolved", "sum"), res=("is_resolved", "sum"),
                 canc=("is_cancelled", "sum"), elig=("_elig", "sum"), met=("_met", "sum"), fcr=("is_fcr", "sum"),
                 esc=("is_escalated", "sum"), reo=("is_reopened", "sum"), frtS=("_frtS", "sum"), frtN=("_frtN", "sum"),
                 resS=("_resS", "sum"), rep=("is_repeat_contact", "sum"), ag7=("_aging7", "sum"),
                 csS=("_csS", "sum"), csN=("_csN", "sum"), csSat=("_csSat", "sum"),
                 stR=("ticket_status", lambda s: (s == "Resolved").sum()),
                 stP=("ticket_status", lambda s: (s == "Pending").sum()),
                 stI=("ticket_status", lambda s: (s == "In Progress").sum()),
                 stO=("ticket_status", lambda s: (s == "Open").sum())).reset_index()
    fields = ["n", "open", "res", "canc", "elig", "met", "fcr", "esc", "reo", "frtS", "frtN", "resS", "rep", "ag7",
              "csS", "csN", "csSat", "stR", "stP", "stI", "stO"]
    tk = [[mi[r.created_month], ci[r.ticket_category], hi[r.support_channel], pi[r.ticket_priority]]
          + [round(float(getattr(r, f)), 2) if f in ("frtS", "resS", "csS") else int(getattr(r, f)) for f in fields]
          for r in cube.itertuples(index=False)]

    # CSAT by FRT band / resolution band (year x dept x channel x priority)
    s = t[t._csN].copy()
    s["frtb"] = pd.cut(s.first_response_hours, eda.FRT_BINS, labels=eda.FRT_LABELS).astype(object).fillna("No response")
    s["resb"] = s.resolution_bucket.fillna("n/a")
    def band_cube(col, labels):
        gb = s.groupby([col, "created_year", "department_name", "support_channel", "ticket_priority"]).agg(
            n=("ticket_id", "size"), cs=("satisfaction_score", "sum"), sat=("_csSat", "sum")).reset_index()
        li = {v: i for i, v in enumerate(labels)}
        dl = sorted(dep_name.values())
        return [[li[r[col]], int(r.created_year), dl.index(r.department_name), hi[r.support_channel], pi[r.ticket_priority],
                 int(r.n), float(r.cs), int(r.sat)] for _, r in gb.iterrows() if r[col] in li]
    from src.feature_engineering.features import RES_LABELS
    frt_cube = band_cube("frtb", eda.FRT_LABELS)
    res_cube = band_cube("resb", RES_LABELS)

    fb = t[t.feedback_category.notna()].groupby(["feedback_category", "created_year", "department_name", "support_channel", "ticket_priority"]).agg(
        n=("ticket_id", "size"), cs=("_csS", "sum"), csn=("_csN", "sum")).reset_index()
    fcats = sorted(fb.feedback_category.unique())
    dl = sorted(dep_name.values())
    fb_cube = [[fcats.index(r.feedback_category), int(r.created_year), dl.index(r.department_name), hi[r.support_channel],
                pi[r.ticket_priority], int(r.n), float(r.cs), int(r.csn)] for r in fb.itertuples(index=False)]

    # agents x year
    ta = t[t.agent_id.notna()]
    ag = ta.groupby(["agent_id", "created_year"]).agg(n=("ticket_id", "size"), res=("is_resolved", "sum"), canc=("is_cancelled", "sum"),
        elig=("_elig", "sum"), met=("_met", "sum"), resS=("_resS", "sum"), csS=("_csS", "sum"), csN=("_csN", "sum"),
        reo=("is_reopened", "sum")).reset_index()
    pw = perf.assign(year=perf.performance_date.dt.year).groupby(["agent_id", "year"]).agg(
        wh=("workload_hours", "sum"), pres=("tickets_resolved", "sum"), months=("performance_id", "size")).reset_index()
    ag = ag.merge(pw, left_on=["agent_id", "created_year"], right_on=["agent_id", "year"], how="left").fillna(0)
    am = agents.set_index("agent_id")
    agent_list = sorted(ag.agent_id.unique())
    agent_meta = [{"id": a, "name": am.loc[a, "agent_name"], "dept": dl.index(dep_name[am.loc[a, "department_id"]]),
                   "level": am.loc[a, "experience_level"], "team": am.loc[a, "team"], "status": am.loc[a, "employment_status"]}
                  for a in agent_list]
    ag_rows = [[agent_list.index(r.agent_id), int(r.created_year), int(r.n), int(r.res), int(r.canc), int(r.elig), int(r.met),
                round(float(r.resS), 1), float(r.csS), int(r.csN), int(r.reo), round(float(r.wh), 1), int(r.pres), int(r.months)]
               for r in ag.itertuples(index=False)]

    # operations month x process
    o = o.assign(m=o.operation_date.dt.strftime("%Y-%m"), bad=(o.operational_status != "Normal"),
                 pw=o.processing_time_minutes * o.total_transactions)
    procs = sorted(o.process_name.unique())
    pmeta = o.drop_duplicates("process_name").set_index("process_name")
    proc_meta = [{"name": p, "dept": dl.index(dep_name[pmeta.loc[p, "department_id"]]), "type": pmeta.loc[p, "operation_type"]} for p in procs]
    og = o.groupby(["m", "process_name"]).agg(tx=("total_transactions", "sum"), ok=("successful_transactions", "sum"),
        fail=("failed_transactions", "sum"), pw=("pw", "sum"), cost=("operational_cost", "sum"), bad=("bad", "sum"),
        days=("operation_id", "size")).reset_index()
    ops_rows = [[months.index(r.m), procs.index(r.process_name), int(r.tx), int(r.ok), int(r.fail), round(float(r.pw), 1),
                 round(float(r.cost), 2), int(r.bad), int(r.days)] for r in og.itertuples(index=False)]

    ccats = sorted(costs.cost_category.unique())
    cg = costs.assign(m=costs.cost_date.dt.strftime("%Y-%m")).groupby(["m", "department_id", "cost_category"]).agg(
        tot=("total_cost", "sum"), dir=("direct_cost", "sum"), ind=("indirect_cost", "sum")).reset_index()
    cost_rows = [[months.index(r.m), dl.index(dep_name[r.department_id]), ccats.index(r.cost_category), round(float(r.tot), 2),
                  round(float(r.dir), 2), round(float(r.ind), 2)] for r in cg.itertuples(index=False)]

    # monthly backlog (open at month end) by department
    bl = []
    for dn in dl:
        mb = eda.monthly_backlog(t[t.department_name == dn])
        bl.append(mb.open_at_month_end.tolist())

    u = t[b("is_unresolved")]
    open_rows = [[dl.index(r.department_name), ci[r.ticket_category], hi[r.support_channel], pi[r.ticket_priority],
                  int(r.created_year), round(float(r.ticket_age_days), 1), int(r.ticket_age_days * 24 > r.sla_target_hours)]
                 for r in u.itertuples(index=False)]

    return {
        "meta": {"generated": pd.Timestamp.now().strftime("%Y-%m-%d"), "snapshot": "31 Dec 2025",
                 "source": "data/processed (synthetic, seed %d)" % config.SEED},
        "months": months, "cats": cats, "catDept": [dl.index(cat_dept[c]) for c in cats], "chans": chans, "prios": prios,
        "depts": dl, "budget": [float(deps.set_index("department_name").operational_budget[n]) for n in dl],
        "sla": [config.SLA_TARGET_HOURS[p] for p in prios],
        "tkFields": fields, "tk": tk,
        "frtLabels": eda.FRT_LABELS, "frt": frt_cube, "resLabels": RES_LABELS, "resb": res_cube,
        "fbCats": fcats, "fb": fb_cube,
        "agents": agent_meta, "ag": ag_rows,
        "procs": proc_meta, "ops": ops_rows, "costCats": ccats, "costs": cost_rows,
        "backlog": bl, "open": open_rows,
    }


def main() -> None:
    payload = build_payload()
    tpl = (OUT / "template.html").read_text()
    html = tpl.replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":"), default=lambda x: x.item() if hasattr(x, "item") else str(x)))
    (OUT / "index.html").write_text(html)
    print(f"index.html written ({len(html)/1024:.0f} KB, {len(payload['tk'])} ticket-cube rows)")


if __name__ == "__main__":
    main()
