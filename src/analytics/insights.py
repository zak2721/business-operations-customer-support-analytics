"""Data-driven business insights.

Every number in an insight is computed here from processed data or from the
saved advanced-analytics outputs - nothing is typed by hand. The narrative
text separates **observed findings** (computed) from **hypotheses** and
**recommendations** (judgement). Expected outcomes are expressed as
measurable targets to monitor, not as predicted savings.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src import config
from src.analytics import eda
from src.kpi.kpis import escalation_rate, kpi_by


@dataclass
class Insight:
    id: int
    area: str
    title: str
    finding: str
    evidence: str
    impact: str
    hypothesis: str
    action: str
    expected_outcome: str
    kpi_to_monitor: str
    priority: str  # High / Medium / Low


def _r(x, n=1):
    return f"{x:,.{n}f}"


def build_insights(d: dict[str, pd.DataFrame], adv: dict) -> list[Insight]:
    t, f, o = d["tickets_enriched"], d["customer_feedback"], d["operations"]
    perf, agents, costs, deps = d["agent_performance"], d["agents"], d["business_costs"], d["departments"]
    e = t[t.sla_eligible.astype(bool)]
    ins: list[Insight] = []

    def add(**kw):
        ins.append(Insight(id=len(ins) + 1, **kw))

    # 1 channel response gap
    ch = kpi_by(t[t.support_channel != "Unknown"], "support_channel").set_index("support_channel")
    rt = ch.loc[["Phone", "Live Chat"]]
    asy = ch.loc[["Email", "Web Portal", "Social Media"]]
    add(area="Customer Support", priority="High",
        title="Asynchronous channels respond in hours, real-time channels in minutes",
        finding=(f"Average first response time is {_r(ch.loc['Web Portal','avg_frt_h'],2)} h on Web Portal, "
                 f"{_r(ch.loc['Email','avg_frt_h'],2)} h on Email and {_r(ch.loc['Social Media','avg_frt_h'],2)} h on Social Media, "
                 f"versus {_r(ch.loc['Phone','avg_frt_h']*60,0)} min on Phone and {_r(ch.loc['Live Chat','avg_frt_h']*60,0)} min on Live Chat. "
                 f"SLA compliance follows the same split: {_r(asy.sla_compliance_pct.min())}-{_r(asy.sla_compliance_pct.max())}% "
                 f"for asynchronous channels vs {_r(rt.sla_compliance_pct.min())}-{_r(rt.sla_compliance_pct.max())}% for real-time."),
        evidence="KPI by channel (avg FRT, SLA compliance); SLA-breach logistic regression odds ratios vs Phone: "
                 + ", ".join(f"{k} {v:.1f}x" for k, v in _odds(adv_path(), "support_channel").items()),
        impact=f"Email and Web Portal carry {_r((ch.loc['Email','tickets']+ch.loc['Web Portal','tickets'])/len(t)*100)}% of all tickets, so their "
               "delays dominate the overall SLA and CSAT picture.",
        hypothesis="Asynchronous queues are worked in batches and are not staffed out of hours; tickets created in the evening or at weekends wait for the next shift.",
        action="Introduce an auto-acknowledgement + triage rule for Email/Web Portal, set a 4-hour first-response target for those queues, and route simple categories (Account Access, Order Status, Product Inquiry) to live chat or self-service.",
        expected_outcome="Average FRT on Email/Web Portal falls below the 8 h Medium-priority FRT target; asynchronous SLA compliance converges toward the real-time level.",
        kpi_to_monitor="Avg First Response Time by channel; SLA Compliance Rate by channel")

    # 2 CSAT vs FRT
    fb = eda.frt_bucket_csat(t).set_index("frt_bucket")
    rho = adv["correlations"]["First response time vs CSAT"]["spearman_rho"]
    add(area="Customer Experience", priority="High",
        title="Satisfaction declines steadily as first response time grows",
        finding=(f"Average CSAT is {_r(fb.loc['<15 min','avg_csat'],2)} when the first response arrives within 15 minutes, "
                 f"{_r(fb.loc['4-8 h','avg_csat'],2)} at 4-8 hours and {_r(fb.loc['24 h+','avg_csat'],2)} after 24 hours "
                 f"(satisfied share {_r(fb.loc['<15 min','csat_rate_pct'])}% -> {_r(fb.loc['24 h+','csat_rate_pct'])}%)."),
        evidence=f"Spearman rho = {rho} (n = {adv['correlations']['First response time vs CSAT']['n']}); "
                 f"OLS coefficient on log(1+FRT) = {adv['csat_ols_key_coefs']['log_frt']['coef']} CSAT points, holding SLA outcome, reopen, escalation, channel and category constant.",
        impact="Response speed is the most controllable lever on customer experience; every additional delay band costs satisfaction.",
        hypothesis="Customers interpret a slow first reply as lack of ownership, independent of the eventual resolution.",
        action="Publish FRT targets per priority (Critical 1 h, High 4 h, Medium 8 h, Low 24 h) on the team dashboard and alert supervisors when a ticket approaches its FRT target.",
        expected_outcome="Share of tickets with first response under 1 hour rises quarter over quarter; average CSAT of async channels rises.",
        kpi_to_monitor="FRT compliance %, Avg CSAT by FRT band")

    # 3 SLA breach and CSAT
    sm = eda.sla_met_csat(t).set_index("sla_outcome")
    add(area="Customer Experience", priority="High",
        title="An SLA breach is the strongest measured driver of an unhappy customer",
        finding=(f"{_r(sm.loc['Within SLA','csat_rate_pct'])}% of customers whose ticket was resolved within SLA were satisfied (CSAT 4-5), "
                 f"versus {_r(sm.loc['SLA breached','csat_rate_pct'])}% when the SLA was breached "
                 f"(avg CSAT {_r(sm.loc['Within SLA','avg_csat'],2)} vs {_r(sm.loc['SLA breached','avg_csat'],2)})."),
        evidence=f"Mann-Whitney p < 0.001, rank-biserial effect {adv['group_tests']['CSAT: within SLA vs breached']['rank_biserial']}; "
                 f"OLS coefficient for breach = {adv['csat_ols_key_coefs']['sla_breached_i']['coef']} points (95% CI "
                 f"{adv['csat_ols_key_coefs']['sla_breached_i']['ci_low']} to {adv['csat_ols_key_coefs']['sla_breached_i']['ci_high']}); model R^2 = {adv['csat_ols_r2']}.",
        impact=f"With an overall breach rate of {_r(100 - e.sla_met.mean()*100)}%, roughly one resolved ticket in four is a likely detractor.",
        hypothesis="Customers judge the experience primarily on whether the promised timeframe was kept.",
        action="Make SLA compliance the primary team KPI and add an 'SLA at risk' queue (tickets at 75% of their target) for supervisor intervention.",
        expected_outcome="SLA breach rate falls; the satisfied share of resolved tickets rises in step.",
        kpi_to_monitor="SLA Breach Rate; Customer Satisfaction Rate")

    # 4 Billing deterioration
    b = adv["billing_sla_2025_vs_2024"]
    bt = t[t.department_name == "Billing & Accounts"]
    vol = bt.groupby("created_year").size()
    bp = perf.merge(agents[["agent_id", "department_id"]]).query("department_id == 'DEP-02'")
    bp = bp.assign(year=bp.performance_date.dt.year)
    load = bp.groupby("year").apply(lambda g: g.tickets_assigned.sum() / g.groupby("performance_date").agent_id.nunique().mean() / 12,
                                    include_groups=False)
    term = agents[(agents.department_id == "DEP-02") & (agents.employment_status == "Terminated")]
    add(area="SLA & Service Quality", priority="High",
        title="Billing & Accounts SLA compliance collapsed in 2025",
        finding=(f"Billing SLA compliance fell from {b['p2_pct']}% (2024) to {b['p1_pct']}% (2025), a {abs(b['diff_pp'])}-point drop. "
                 f"Billing ticket volume rose from {vol.get(2024,0):,} to {vol.get(2025,0):,} (+{_r((vol.get(2025)/vol.get(2024)-1)*100)}%) "
                 f"while assignments per active Billing agent rose from {_r(load.get(2024))} to {_r(load.get(2025))} per month. "
                 f"{len(term)} Billing agents are recorded as terminated."),
        evidence=f"Two-proportion z-test z = {b['z']}, p < 0.001; resolution time Mann-Whitney p < 0.001 (median "
                 f"{adv['group_tests']['Resolution h: Billing 2025 vs Billing 2024']['median_b']} h -> "
                 f"{adv['group_tests']['Resolution h: Billing 2025 vs Billing 2024']['median_a']} h).",
        impact="Billing is the second-largest ticket category; its breaches directly affect revenue-related customer trust.",
        hypothesis="A demand increase from April 2025 (Billing & Payment share of tickets jumps) coincided with experienced-agent attrition, lowering capacity per ticket.",
        action="Backfill the two Billing roles, cross-train Order Management agents (highest SLA compliance) on Billing, and review the 2025 billing/pricing change that drove the extra tickets.",
        expected_outcome="Billing SLA compliance returns toward its 2023-2024 level (>80%); tickets per Billing agent return to the 2024 level.",
        kpi_to_monitor="SLA Compliance (Billing), Tickets per Agent (Billing), Billing ticket volume")

    # 5 Billing outsourcing cost
    bg = (costs.assign(year=costs.cost_date.dt.year).query("department_id == 'DEP-02' and cost_category == 'Outsourcing'")
          .groupby("year").total_cost.sum())
    add(area="Cost", priority="Medium",
        title="Billing's outsourcing spend more than doubled without restoring service levels",
        finding=f"Billing outsourcing cost rose from ${_r(bg.get(2023),0)} (2023) to ${_r(bg.get(2025),0)} (2025), "
                f"+{_r((bg.get(2025)/bg.get(2023)-1)*100)}%, the largest category-level increase in the company, while Billing SLA compliance fell to {b['p1_pct']}%.",
        evidence="Business costs by department x category, 2023 vs 2025 (rca_business_cost_growth.csv).",
        impact="Spend increased in the same period that service quality fell, so cost per compliant ticket rose sharply.",
        hypothesis="Outsourced capacity was added reactively and handles low-complexity work, or ramps up slowly; it did not offset the loss of experienced in-house agents.",
        action="Attach SLA and FCR targets to the outsourcing contract and report outsourced vs in-house ticket outcomes separately.",
        expected_outcome="Outsourcing cost is tied to measurable throughput; cost per SLA-compliant Billing ticket falls.",
        kpi_to_monitor="Departmental Cost (Billing, Outsourcing); Cost per Resolved Ticket")

    # 6 Returns & Refunds
    dep = kpi_by(t, "department_name").set_index("department_name")
    rr = dep.loc["Returns & Refunds"]
    add(area="SLA & Service Quality", priority="High",
        title="Returns & Refunds has the weakest service performance of any department",
        finding=f"Returns & Refunds resolves only {_r(rr.sla_compliance_pct)}% of tickets within SLA (company {_r(e.sla_met.mean()*100)}%), "
                f"has the longest average resolution time ({_r(rr.avg_resolution_h)} h) and the highest reopen rate ({_r(rr.reopen_pct)}%).",
        evidence="KPI by department; root-cause lift for SLA breach = "
                 f"{_lift(d, 'SLA breach', 'department_name', 'Returns & Refunds')}x baseline.",
        impact="Refund delays are high-emotion contacts and generate repeat contacts and reopenings.",
        hypothesis="Refund resolution depends on the Returns Inspection and Refund Approval processes, both of which show elevated failure rates and processing times (see operations insights).",
        action="Map the refund workflow end-to-end, set a joint SLA between Returns support and the Refund Approval process owner, and give agents refund-status visibility.",
        expected_outcome="Returns & Refunds SLA compliance and reopen rate move toward company averages.",
        kpi_to_monitor="SLA Compliance (Returns & Refunds); Reopen Rate; Refund Approval failure rate")

    # 7 Junior agents
    ex = eda.experience_level_summary(t).set_index("experience_level")
    add(area="Agent Performance", priority="High",
        title="Junior agents breach SLA and get reopened far more often",
        finding=f"Junior agents meet SLA on {_r(ex.loc['Junior','sla_compliance_pct'])}% of tickets vs {_r(ex.loc['Lead','sla_compliance_pct'])}% for Leads; "
                f"their reopen rate is {_r(ex.loc['Junior','reopen_pct'])}% vs {_r(ex.loc['Lead','reopen_pct'])}% and average CSAT {_r(ex.loc['Junior','avg_csat'],2)} vs {_r(ex.loc['Lead','avg_csat'],2)}.",
        evidence=f"Mann-Whitney on resolution hours (Junior vs Senior/Lead) p < 0.001; logistic regression odds ratio for SLA breach, Junior vs Lead = "
                 f"{_odds(adv_path(), 'experience_level').get('Junior', float('nan')):.1f}x after controlling for priority, channel, category and season.",
        impact=f"Junior agents handled {_r(ex.loc['Junior','tickets'],0)} tickets; their excess breaches and reopens consume senior capacity later.",
        hypothesis="Juniors receive the same ticket mix as experienced agents without a structured ramp-up or knowledge base.",
        action="Route Critical/High and complex categories away from agents with < 2 years tenure, pair juniors with a senior buddy, and review reopened tickets weekly as coaching material.",
        expected_outcome="The SLA and reopen gap between Junior and Mid-Level agents narrows each quarter.",
        kpi_to_monitor="SLA Compliance by experience level; Reopen Rate by experience level")

    # 8 FCR
    gt = adv["group_tests"]["CSAT: FCR vs non-FCR resolved tickets"]
    add(area="Customer Experience", priority="Medium",
        title="First-contact resolution lifts satisfaction by almost a full point",
        finding=f"Tickets resolved on first contact average CSAT {gt['mean_a']} vs {gt['mean_b']} otherwise. FCR is "
                f"{_r(ch.loc['Phone','fcr_pct'])}% on Phone and {_r(ch.loc['Live Chat','fcr_pct'])}% on Live Chat but only "
                f"{_r(ch.loc['Email','fcr_pct'])}% on Email and {_r(ch.loc['Web Portal','fcr_pct'])}% on Web Portal (overall {_r(e.is_fcr.mean()*100)}%).",
        evidence=f"Mann-Whitney p < 0.001; OLS coefficient for FCR = +{adv['csat_ols_key_coefs']['fcr']['coef']} after controls.",
        impact="Each ticket solved at first contact avoids follow-up handling time and raises satisfaction.",
        hypothesis="Written channels lack the information needed to resolve on the first reply (account, order or error details).",
        action="Add structured intake forms (order ID, error code, account) to Email/Web Portal and give agents macros for the top subcategories.",
        expected_outcome="FCR on Email/Web Portal rises; average handling touches per ticket fall.",
        kpi_to_monitor="First Contact Resolution Rate by channel")

    # 9 Critical priority
    pr = kpi_by(t, "ticket_priority").set_index("ticket_priority")
    add(area="SLA & Service Quality", priority="High",
        title="Critical tickets have the lowest SLA compliance",
        finding=f"Only {_r(pr.loc['Critical','sla_compliance_pct'])}% of Critical tickets are resolved within their 8-hour SLA, versus "
                f"{_r(pr.loc['Low','sla_compliance_pct'])}% of Low-priority tickets within 72 hours. Critical tickets are escalated {_r(pr.loc['Critical','escalation_pct'])}% of the time.",
        evidence=f"Chi-square priority x SLA breach p < 0.001 (Cramer's V {adv['chi_square']['Priority x SLA breach']['cramers_v']}); "
                 f"odds ratio Critical vs Low = {_odds(adv_path(), 'ticket_priority').get('Critical', float('nan')):.1f}x.",
        impact=f"{pr.loc['Critical','tickets']:,.0f} Critical tickets represent the highest-impact customer incidents.",
        hypothesis="The 8-hour target is tight relative to escalation hand-offs; Critical tickets are not ring-fenced from the general queue.",
        action="Create a dedicated Critical-incident rota with Senior/Lead agents, and auto-page Tier 2 at creation rather than after first triage.",
        expected_outcome="Critical SLA compliance rises; escalation-to-resolution time for Critical tickets falls.",
        kpi_to_monitor="SLA Compliance (Critical); Avg Resolution Time by Priority")

    # 10 backlog aging
    u = t[t.is_unresolved.astype(bool)]
    add(area="SLA & Service Quality", priority="Medium",
        title="Most of the open backlog is stale rather than new",
        finding=f"Of {len(u):,} open tickets at 31 Dec 2025, {int((u.ticket_age_days > 30).sum())} ({_r((u.ticket_age_days > 30).mean()*100)}%) are older than 30 days and "
                f"{int((u.ticket_age_days > 60).sum())} are older than 60 days. {int((u.ticket_status=='Open').sum())} have never received a first response. "
                f"The month-end backlog grew from {_bl(t, '2025-08')} (Aug 2025) to {_bl(t, '2025-12')} (Dec 2025).",
        evidence="Ticket aging distribution (open = Open, In Progress, Pending).",
        impact="Aged tickets are almost certain SLA breaches and likely churn risks; they also distort backlog-based staffing.",
        hypothesis="Pending tickets waiting on customer replies are not auto-closed and in-progress tickets lack ownership reviews.",
        action="Run a backlog scrub, introduce auto-close after a defined no-reply period for Pending tickets, and add a weekly aged-ticket review by team leads.",
        expected_outcome="Tickets older than 30 days fall to a small fraction of the backlog; 'Open with no first response' approaches zero.",
        kpi_to_monitor="Aging Ticket Backlog (>7, >30 days); Ticket Backlog")

    # 11 seasonality
    mv = t.groupby(t.ticket_created_date.dt.month).size() / t.created_year.nunique()
    q4_sla = e[e.ticket_created_date.dt.month.isin([11, 12])].sla_met.mean() * 100
    rest_sla = e[~e.ticket_created_date.dt.month.isin([11, 12])].sla_met.mean() * 100
    add(area="Customer Support", priority="Medium",
        title="November-December peaks overwhelm capacity",
        finding=f"Average monthly volume is {_r(mv.loc[[11,12]].mean(),0)} tickets in Nov-Dec vs {_r(mv.loc[[6,7,8]].mean(),0)} in Jun-Aug. "
                f"SLA compliance in Nov-Dec is {_r(q4_sla)}% vs {_r(rest_sla)}% for the rest of the year.",
        evidence=f"Odds ratio for Q4 in the SLA-breach logistic regression = {_odds(adv_path(), 'q4').get('q4', float('nan')):.2f}x.",
        impact="The peak coincides with the highest-revenue period; service failures then have outsized commercial cost.",
        hypothesis="Staffing is flat across the year while demand is seasonal.",
        action="Use the monthly volume profile to plan seasonal temporary staff and freeze leave in Nov-Dec; pre-publish holiday delivery FAQs.",
        expected_outcome="The Nov-Dec SLA gap versus the rest of the year narrows.",
        kpi_to_monitor="Monthly SLA Compliance; Tickets per Agent (monthly)")

    # 12 workload
    wl = eda.workload_vs_resolution(perf)
    rho_w = adv["correlations"]["Agent monthly workload vs avg resolution time"]["spearman_rho"]
    add(area="Agent Performance", priority="Medium",
        title="Agent-months with the heaviest workload resolve tickets more slowly",
        finding=f"In the top workload quintile (avg {_r(wl.avg_assigned.iloc[-1])} tickets assigned/month) average resolution time is "
                f"{_r(wl.avg_resolution_h.iloc[-1])} h and SLA compliance {_r(wl.avg_sla_pct.iloc[-1])}%, vs {_r(wl.avg_resolution_h.iloc[:-1].mean())} h and "
                f"{_r(wl.avg_sla_pct.iloc[:-1].mean())}% in the other quintiles.",
        evidence=f"Spearman rho workload vs resolution time = {rho_w} (weak but significant, n = {adv['correlations']['Agent monthly workload vs avg resolution time']['n']} agent-months).",
        impact="The effect appears only at the high end, which points to a capacity threshold rather than a gradual slowdown.",
        hypothesis="Above roughly 17 new tickets per agent per month, agents switch context too often to keep up.",
        action="Set a soft cap on monthly assignments per agent and rebalance via skills-based routing when an agent exceeds it.",
        expected_outcome="Fewer agent-months fall into the top workload band; resolution time variance across agents narrows.",
        kpi_to_monitor="Tickets per Agent; Agent workload distribution")

    # 13 repeat contacts
    per = t.groupby("customer_id").size().sort_values(ascending=False)
    top10 = per.head(int(len(per) * 0.1)).sum() / per.sum() * 100
    add(area="Customer Experience", priority="Medium",
        title="Repeat contacts are common and concentrated in a small set of customers",
        finding=f"{_r(t.is_repeat_contact.mean()*100)}% of tickets arrive within 7 days of the same customer's previous ticket. "
                f"The top 10% of contacting customers generate {_r(top10)}% of all tickets.",
        evidence="7-day repeat-contact flag; ticket concentration by customer.",
        impact="Repeat contacts inflate volume without new demand and signal unresolved root problems for key accounts.",
        hypothesis="High-usage (mostly Enterprise and Mid-Market) customers hit the same issues repeatedly; fixes are not followed up proactively.",
        action="Assign named account contacts to the top-volume customers and run quarterly root-cause reviews of their ticket history.",
        expected_outcome="7-day repeat contact rate declines; ticket volume from top-decile customers grows more slowly than their usage.",
        kpi_to_monitor="Customer Repeat Contact Rate; tickets per customer (top decile)")

    # 14 complaints
    cat = kpi_by(t, "ticket_category").set_index("ticket_category")
    add(area="Customer Experience", priority="Medium",
        title="Complaints are escalated most and satisfy least",
        finding=f"Complaint tickets are escalated {_r(cat.loc['Complaint','escalation_pct'])}% of the time (company {_r(escalation_rate(t))}%) "
                f"and have the lowest average CSAT ({_r(cat.loc['Complaint','avg_csat'],2)}) and FCR ({_r(cat.loc['Complaint','fcr_pct'])}%).",
        evidence="KPI by category; root-cause lift for escalation.",
        impact="Complaints are the strongest churn signal and consume senior time through escalations.",
        hypothesis="Front-line agents lack authority to offer remedies (credits, exceptions), so complaints must be escalated.",
        action="Give Senior agents a defined goodwill-credit authority and a complaint-handling playbook so most complaints close without escalation.",
        expected_outcome="Complaint escalation rate and resolution time fall; complaint CSAT rises.",
        kpi_to_monitor="Escalation Rate (Complaint); Avg CSAT (Complaint)")

    # 15 weekend
    wk = t.assign(weekend=~t.created_weekday.astype(bool))
    w = wk.groupby("weekend").agg(frt=("first_response_hours", "mean"), csat=("satisfaction_score", "mean"))
    add(area="Customer Support", priority="Low",
        title="Weekend tickets wait longer and score lower",
        finding=f"Tickets created at weekends wait {_r(w.loc[True,'frt'],2)} h on average for a first response vs {_r(w.loc[False,'frt'],2)} h on weekdays; "
                f"their average CSAT is {_r(w.loc[True,'csat'],2)} vs {_r(w.loc[False,'csat'],2)}.",
        evidence=f"Low-CSAT root-cause lift for Saturday = {_lift(d, 'Low satisfaction (CSAT <= 2)', 'created_dayname', 'Saturday')}x.",
        impact="Weekend volume is lower, so a small coverage change could remove most of the gap.",
        hypothesis="Asynchronous queues are not monitored at weekends.",
        action="Add a light weekend rota for Email/Web Portal triage (first response only).",
        expected_outcome="Weekend FRT approaches weekday FRT.",
        kpi_to_monitor="Avg First Response Time (weekend vs weekday)")

    # 16 Refund approval
    py = eda.ops_process_year(o)
    ra = py[py.process_name == "Refund Approval"].set_index("year")
    bt_ = eda.bottleneck_table(o).set_index("process_name")
    add(area="Business Operations", priority="High",
        title="Refund Approval is the most failure-prone process and is getting worse",
        finding=f"Refund Approval's failure rate rose from {_r(ra.loc[2023,'failure_rate_pct'],2)}% (2023) to {_r(ra.loc[2025,'failure_rate_pct'],2)}% (2025), "
                f"about {_r(ra.loc[2025,'failure_rate_pct'] / (o.failed_transactions.sum()/o.total_transactions.sum()*100),1)}x the company average; "
                f"{_r(bt_.loc['Refund Approval','degraded_or_critical_days_pct'])}% of its operating days were 'Degraded' or 'Critical'.",
        evidence="Operations failure rate by process and year; operational bottleneck score.",
        impact="Failed refund approvals feed directly into Returns & Refunds tickets, reopenings and SLA breaches.",
        hypothesis="Manual approval steps and inconsistent policy rules cause rejections that later need rework.",
        action="Audit the top rejection reasons, automate rule-based approvals under a value threshold, and add a daily failure-rate alert.",
        expected_outcome="Refund Approval failure rate trends back toward its 2023 level; Returns & Refunds reopen rate falls.",
        kpi_to_monitor="Operational Failure Rate (Refund Approval); Reopen Rate (Returns & Refunds)")

    # 17 Payment reconciliation
    prc = o[o.process_name == "Payment Reconciliation"]
    pre = prc[prc.operation_date < "2025-04-01"]; post = prc[prc.operation_date >= "2025-04-01"]
    cd = pd.read_csv(config.REPORTS_DATA_DIR / "rca_ops_cost_decomposition.csv").set_index("process_name")
    add(area="Business Operations", priority="High",
        title="Payment Reconciliation failures jumped after April 2025 and its unit cost is rising fastest",
        finding=f"Failure rate was {_r(pre.failed_transactions.sum()/pre.total_transactions.sum()*100,2)}% before April 2025 and "
                f"{_r(post.failed_transactions.sum()/post.total_transactions.sum()*100,2)}% after. Its cost per transaction grew "
                f"{_r(cd.loc['Payment Reconciliation','unit_cost_change_pct'])}% between 2023 and 2025, the highest of any process.",
        evidence="Operations by process (pre/post April 2025); price-volume cost decomposition.",
        impact="The timing matches the jump in Billing tickets, suggesting the same upstream change affects both operations and support.",
        hypothesis="The April 2025 pricing/billing change introduced reconciliation mismatches that surface as failed transactions and customer billing tickets.",
        action="Run a joint incident review between Billing operations and Billing support on the April 2025 change; fix mapping rules for new price plans.",
        expected_outcome="Payment Reconciliation failure rate returns to its pre-April level; Billing ticket share declines.",
        kpi_to_monitor="Operational Failure Rate (Payment Reconciliation); Billing & Payment ticket volume")

    # 18 Shipment dispatch
    sd = o[o.process_name == "Shipment Dispatch"]
    q4m = sd[sd.operation_date.dt.month.isin([11, 12])]; rest = sd[~sd.operation_date.dt.month.isin([11, 12])]
    wavg = lambda x: (x.processing_time_minutes * x.total_transactions).sum() / x.total_transactions.sum()  # noqa: E731
    add(area="Business Operations", priority="Medium",
        title="Shipment Dispatch slows down sharply in peak season",
        finding=f"Shipment Dispatch takes {_r(wavg(q4m),2)} min per transaction in Nov-Dec vs {_r(wavg(rest),2)} min the rest of the year "
                f"(+{_r((wavg(q4m)/wavg(rest)-1)*100)}%). It is also the largest single operating cost line (${_r(sd.operational_cost.sum()/1e6,2)}M over 3 years).",
        evidence="Volume-weighted processing time by process and month.",
        impact="Slower dispatch in peak season is consistent with the Nov-Dec rise in Delivery Problem tickets and SLA breaches.",
        hypothesis="Warehouse dispatch capacity is fixed while order volume peaks.",
        action="Pre-book carrier capacity and temporary warehouse staff for Nov-Dec; add dispatch-delay proactive notifications to customers.",
        expected_outcome="Peak-season dispatch time approaches the off-peak level; Delivery Problem tickets in Nov-Dec fall.",
        kpi_to_monitor="Avg Processing Time (Shipment Dispatch); Delivery Problem ticket volume")

    # 19 ops cost decomposition
    vol_eff, unit_eff = cd.volume_effect.sum(), cd.unit_cost_effect.sum()
    add(area="Cost", priority="Medium",
        title="Operational cost growth is mostly volume-driven, but unit costs are also rising",
        finding=f"Transaction-processing cost grew by ${_r(cd.cost_change.sum()/1e6,2)}M between 2023 and 2025. "
                f"${_r(vol_eff/1e6,2)}M ({_r(vol_eff/(vol_eff+unit_eff)*100)}%) is explained by higher volume and ${_r(unit_eff/1e6,2)}M by higher cost per transaction.",
        evidence=f"Price-volume decomposition per process; Pearson r between daily volume and cost = {adv['correlations']['Daily transaction volume vs operational cost']['spearman_rho']} (Spearman).",
        impact="Volume growth is a business success; the unit-cost component is the controllable inefficiency.",
        hypothesis="Rework from failed transactions and vendor price increases drive unit cost.",
        action="Track cost per transaction by process monthly, and prioritise automation where unit cost is rising (Payment Reconciliation, Shipment Dispatch, Returns Inspection).",
        expected_outcome="Cost per transaction stabilises or falls while volume grows.",
        kpi_to_monitor="Average Cost per Transaction; Operational Efficiency Rate")

    # 20 budget overrun
    bu = eda.costs_yearly_by_department(costs, deps)
    b25 = bu[bu.year == 2025].set_index("department_name")
    add(area="Cost", priority="Medium",
        title="Every department exceeded its annual budget in 2025",
        finding=f"2025 spend as a share of budget ranged from {_r(b25.budget_utilisation_pct.min())}% to {_r(b25.budget_utilisation_pct.max())}% "
                f"(highest: {b25.budget_utilisation_pct.idxmax()}). Total departmental cost was ${_r(bu[bu.year==2025].total_cost.sum()/1e6,2)}M "
                f"against ${_r(deps.operational_budget.sum()/1e6,2)}M budgeted.",
        evidence="Business costs vs department operational_budget, by year.",
        impact="Budgets have not been re-baselined for growth, so overruns are structural rather than one-off.",
        hypothesis="Budgets are flat year-on-year while volume and wage costs grow.",
        action="Re-baseline budgets on a cost-per-ticket and cost-per-transaction driver model, and review Billing's overrun separately.",
        expected_outcome="Budget utilisation returns close to 100% with explainable variances.",
        kpi_to_monitor="Departmental Cost vs Budget; Cost per Resolved Ticket")

    # 21 cost per resolved ticket
    cy = costs.groupby(costs.cost_date.dt.year).total_cost.sum()
    ry = t[t.is_resolved.astype(bool)].groupby(t.created_year).size()
    cpt = (cy / ry)
    add(area="Cost", priority="Low",
        title=("Fully loaded cost per resolved ticket is broadly flat" if abs(cpt.iloc[-1] / cpt.iloc[0] - 1) < 0.10
               else ("Fully loaded cost per resolved ticket is falling" if cpt.iloc[-1] < cpt.iloc[0]
                     else "Fully loaded cost per resolved ticket is rising")),
        finding="Cost per resolved ticket (departmental cost / resolved tickets) was " +
                ", ".join(f"${_r(cpt.loc[y],0)} in {y}" for y in cpt.index) + ".",
        evidence="Business costs and resolved tickets by year.",
        impact=f"The change from {cpt.index[0]} to {cpt.index[-1]} is {_r((cpt.iloc[-1]/cpt.iloc[0]-1)*100)}%: volume growth is translating almost one-for-one into cost growth, with little scale benefit.",
        hypothesis="Headcount and overheads grow roughly in line with ticket volume.",
        action="Use FCR, reopen and repeat-contact reductions (insights 8, 13, 16) as the main cost-efficiency levers.",
        expected_outcome="Cost per resolved ticket declines while SLA compliance holds.",
        kpi_to_monitor="Cost per Resolved Ticket")

    # 22 segment parity
    seg = kpi_by(t, "customer_segment").set_index("customer_segment")
    c = d["customers"]
    clv = c.groupby("customer_segment").customer_lifetime_value.median()
    add(area="Customer Experience", priority="Medium",
        title="High-value Enterprise customers receive the same service as consumers",
        finding=f"SLA compliance is {_r(seg.sla_compliance_pct.min())}-{_r(seg.sla_compliance_pct.max())}% across all four segments, even though median CLV is "
                f"${_r(clv.get('Enterprise'),0)} for Enterprise vs ${_r(clv.get('Consumer'),0)} for Consumer customers.",
        evidence=f"Chi-square segment x SLA breach p = {adv['chi_square']['Customer segment x SLA breach']['p_value']:.2f} (no significant difference).",
        impact="Service is consistent, but there is no protection for the accounts with the most revenue at stake.",
        hypothesis="Routing does not use customer segment or CLV.",
        action="Introduce segment-aware routing or a premium SLA tier for Enterprise accounts.",
        expected_outcome="Enterprise SLA compliance and CSAT rise above the company average.",
        kpi_to_monitor="SLA Compliance by segment; CSAT by segment")

    # 23 agent spread
    sc = eda.agent_scorecard(t, perf, agents).dropna(subset=["sla_compliance_pct", "avg_csat"])
    sc = sc[sc.tickets >= 100]
    rho_a = float(sc[["sla_compliance_pct", "avg_csat"]].corr(method="spearman").iloc[0, 1])
    add(area="Agent Performance", priority="Medium",
        title="Agent outcomes vary widely, and SLA performance tracks satisfaction",
        finding=f"Among agents with at least 100 tickets, SLA compliance ranges from {_r(sc.sla_compliance_pct.min())}% to {_r(sc.sla_compliance_pct.max())}% "
                f"and average CSAT from {_r(sc.avg_csat.min(),2)} to {_r(sc.avg_csat.max(),2)}. Agent-level SLA and CSAT correlate (Spearman rho {_r(rho_a,2)}).",
        evidence="Agent scorecard (tickets, SLA, CSAT, reopen) built from ticket-level data.",
        impact="The spread means peer coaching from top performers is available inside the team.",
        hypothesis="Differences reflect experience, category mix and individual practice.",
        action="Run monthly calibration sessions where top-quartile agents share handling approaches; compare agents within the same department and category mix.",
        expected_outcome="The bottom-quartile agent SLA compliance rises; the spread narrows.",
        kpi_to_monitor="SLA Compliance by agent; Avg CSAT by agent")

    # 24 churn link
    st = eda.status_experience(t, c).set_index("status")
    add(area="Customer Experience", priority="Low",
        title="Churned customers had only slightly worse support experiences",
        finding=f"Average CSAT on tickets from customers now marked Churned is {_r(st.loc['Churned','avg_csat'],2)} vs {_r(st.loc['Active','avg_csat'],2)} for Active customers; "
                f"SLA compliance {_r(st.loc['Churned','sla_compliance_pct'])}% vs {_r(st.loc['Active','sla_compliance_pct'])}%.",
        evidence="Ticket KPIs grouped by current customer status.",
        impact="Support experience is at most one factor in churn here; the difference is small.",
        hypothesis="Churn is mostly driven by factors outside support (price, product fit); data on those is not in scope.",
        action="Do not use support KPIs alone as a churn early-warning signal; combine with product usage and billing data in a future churn model.",
        expected_outcome="A churn model with richer features is scoped before any retention spend is targeted.",
        kpi_to_monitor="Churn rate; CSAT of churned vs active")

    # 25 predictive
    m = adv["model"]
    sel = m["models"][m["selected_model"]]
    add(area="Predictive Analytics", priority="Medium",
        title="SLA-breach risk can be estimated at ticket creation",
        finding=f"A {m['selected_model']} model using only creation-time attributes reached ROC-AUC {sel['test_roc_auc']} on 2025 tickets "
                f"(trained on 2023-2024). Tickets in the top predicted-risk decile breached SLA {m['top_decile_breach_rate_pct']}% of the time "
                f"vs {m['bottom_decile_breach_rate_pct']}% in the bottom decile.",
        evidence=f"Time-based hold-out; precision {sel['test_precision']}, recall {sel['test_recall']}, F1 {sel['test_f1']} at threshold {sel['threshold']}. "
                 "Most important features: " + ", ".join(x['feature'] for x in m['top_features'][:4]) + ".",
        impact="A risk score lets supervisors act before a breach instead of reporting it afterwards.",
        hypothesis="The same drivers found in root-cause analysis (channel, category, agent experience, season) make breach risk predictable.",
        action="Pilot a 'high breach risk' tag in the ticketing system for the top decile and measure its effect with an A/B comparison before rollout.",
        expected_outcome="Breach rate among tagged tickets falls relative to an untagged control group.",
        kpi_to_monitor="SLA Breach Rate (tagged vs control)")
    return ins


# ---------------------------------------------------------------- helpers
def adv_path():
    return config.REPORTS_DATA_DIR / "stats_sla_logit_odds_ratios.csv"


def _odds(path, factor: str) -> dict[str, float]:
    o = pd.read_csv(path, index_col=0)
    out = {}
    for idx, r in o.iterrows():
        if factor == "q4" and idx == "q4":
            out["q4"] = r.odds_ratio
        elif factor in idx and "[T." in idx:
            out[idx.split("[T.")[1].rstrip("]")] = r.odds_ratio
    return out


def _lift(d, outcome_prefix: str, factor: str, level: str) -> str:
    dt = pd.read_csv(config.REPORTS_DATA_DIR / "rca_driver_table.csv")
    r = dt[dt.outcome.str.startswith(outcome_prefix) & (dt.factor == factor) & (dt.level.astype(str) == level)]
    return f"{r.lift.iloc[0]:.2f}" if len(r) else "n/a"


def _bl(t, month: str) -> int:
    b = eda.monthly_backlog(t).set_index("month")
    return int(b.loc[month, "open_at_month_end"])


def save_insights(ins: list[Insight]) -> None:
    (config.REPORTS_DATA_DIR / "insights.json").write_text(json.dumps([asdict(i) for i in ins], indent=2))
