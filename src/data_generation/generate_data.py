"""Generate the synthetic business-operations & customer-support datasets.

Run:
    python -m src.data_generation.generate_data

The generator works in two stages:

1. **Simulate a clean, internally consistent business** (customers, agents,
   tickets, feedback, operations, costs). Business behaviour is driven by
   explicit, documented assumptions (see ``reference_data.py``) such as
   workload-dependent resolution speed, seasonal peaks, a 2025 pricing change
   that inflates Billing ticket volume, and agent attrition in Billing.
2. **Inject realistic data-quality defects** (duplicates, missing values,
   inconsistent labels, impossible timestamps, out-of-range scores, orphan
   keys, cost outliers) so the cleaning pipeline has real work to do.
   Every injected defect is counted in ``data/raw/_generation_manifest.json``
   so tests can confirm the cleaning stage detects them.

All people and companies are fictitious (Faker); no real personal data is used.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from faker import Faker

from src import config
from src.data_generation import reference_data as ref

log = logging.getLogger(__name__)


@dataclass
class GeneratedData:
    """Container for all generated tables (clean + raw-with-defects)."""
    clean: dict[str, pd.DataFrame] = field(default_factory=dict)
    raw: dict[str, pd.DataFrame] = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)


class SupportDataGenerator:
    """Simulates a mid-sized e-commerce/SaaS company's support operation."""

    def __init__(self, seed: int = config.SEED,
                 n_customers: int = config.N_CUSTOMERS,
                 n_tickets: int = config.N_TICKETS):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.fake = Faker("en_US")
        Faker.seed(seed)
        self.n_customers = n_customers
        self.n_tickets = n_tickets
        self.start = pd.Timestamp(config.START_DATE)
        self.end = pd.Timestamp(config.END_DATE)
        self.snapshot = pd.Timestamp(config.SNAPSHOT_DATE)

    # ------------------------------------------------------------------ dims
    def departments(self) -> pd.DataFrame:
        rows = []
        for dep_id, name, loc, budget in ref.DEPARTMENTS:
            rows.append({
                "department_id": dep_id,
                "department_name": name,
                "department_manager": self.fake.name(),
                "department_location": loc,
                "operational_budget": float(budget),
            })
        return pd.DataFrame(rows)

    def agents(self) -> pd.DataFrame:
        rows, n = [], 1
        levels = list(ref.EXPERIENCE)
        for dep_id, count in ref.AGENTS_PER_DEPT.items():
            for i in range(count):
                # first four agents in each department pre-date the window so
                # every department is staffed from day one
                if i < 4 or self.rng.random() < 0.70:
                    hire = pd.Timestamp("2016-01-01") + pd.Timedelta(days=int(self.rng.integers(0, 2550)))
                else:
                    hire = self.start + pd.Timedelta(days=int(self.rng.integers(0, 900)))
                tenure_years = (self.end - hire).days / 365.25
                # experience correlates with tenure (with noise)
                score = tenure_years + self.rng.normal(0, 1.5)
                level = levels[0] if score < 2.5 else levels[1] if score < 5.5 else levels[2] if score < 8.5 else levels[3]
                rows.append({
                    "agent_id": f"AGT-{n:03d}",
                    "agent_name": self.fake.name(),
                    "team": self.rng.choice(ref.TEAMS[dep_id]),
                    "department_id": dep_id,
                    "hire_date": hire.normalize(),
                    "experience_level": level,
                    "employment_status": "Active",
                    "shift": self.rng.choice(ref.SHIFTS, p=[0.45, 0.35, 0.20]),
                    "location": self.rng.choice(ref.AGENT_LOCATIONS[dep_id]),
                    "_capacity": self.rng.gamma(6, 1 / 6),       # relative share of work
                    "_skill": self.rng.normal(0, 0.22),          # CSAT shift
                    "_termination": pd.NaT,
                })
                n += 1
        df = pd.DataFrame(rows)
        # Attrition: two experienced Billing agents leave in early 2025 (drives
        # a real workload/SLA problem), plus a few departures elsewhere.
        billing_old = df[(df.department_id == "DEP-02") & (df.hire_date < self.start)].index[:2]
        df.loc[billing_old, "_termination"] = [pd.Timestamp("2025-02-14"), pd.Timestamp("2025-03-28")]
        others = df[(df.department_id != "DEP-02") & (df.hire_date < self.start)].sample(3, random_state=self.seed).index
        df.loc[others, "_termination"] = [pd.Timestamp(d) for d in ("2024-05-31", "2024-10-15", "2025-06-30")]
        df.loc[df._termination.notna(), "employment_status"] = "Terminated"
        on_leave = df[df._termination.isna()].sample(2, random_state=self.seed + 1).index
        df.loc[on_leave, "employment_status"] = "On Leave"
        return df

    def customers(self) -> pd.DataFrame:
        seg_names = list(ref.SEGMENTS)
        seg_w = np.array([ref.SEGMENTS[s][0] for s in seg_names])
        reg_names = list(ref.REGIONS)
        reg_w = np.array([ref.REGIONS[r][0] for r in reg_names])
        segs = self.rng.choice(seg_names, self.n_customers, p=seg_w / seg_w.sum())
        regions = self.rng.choice(reg_names, self.n_customers, p=reg_w / reg_w.sum())
        countries = [self.rng.choice(ref.REGIONS[r][1], p=ref.REGIONS[r][2]) for r in regions]
        # registration skewed toward earlier years (established customer base)
        span = (pd.Timestamp("2025-11-30") - pd.Timestamp("2021-01-01")).days
        reg_days = (self.rng.beta(1.3, 1.6, self.n_customers) * span).astype(int)
        reg_dates = pd.Timestamp("2021-01-01") + pd.to_timedelta(reg_days, unit="D")
        names, ctypes, clv = [], [], []
        for s in segs:
            if s == "Consumer":
                names.append(self.fake.name())
                ctypes.append("Individual")
            else:
                names.append(self.fake.company())
                ctypes.append("Business")
            mu, sigma = ref.SEGMENTS[s][1], ref.SEGMENTS[s][2]
            clv.append(round(float(self.rng.lognormal(mu, sigma)), 2))
        df = pd.DataFrame({
            "customer_id": [f"CUS-{i:05d}" for i in range(1, self.n_customers + 1)],
            "customer_name": names,
            "customer_segment": segs,
            "customer_region": regions,
            "customer_country": countries,
            "customer_type": ctypes,
            "registration_date": reg_dates.normalize(),
            "customer_status": "Active",       # set after tickets are simulated
            "customer_lifetime_value": clv,
        })
        df["_propensity"] = [ref.SEGMENTS[s][3] for s in segs] * self.rng.gamma(0.9, 1 / 0.9, self.n_customers)
        return df

    @staticmethod
    def calendar(start="2021-01-01", end=config.END_DATE) -> pd.DataFrame:
        d = pd.date_range(start, end, freq="D")
        return pd.DataFrame({
            "date": d,
            "year": d.year,
            "quarter": d.quarter,
            "month": d.month,
            "month_name": d.month_name(),
            "week": d.isocalendar().week.astype(int).values,
            "day": d.day,
            "day_name": d.day_name(),
            "weekday_flag": (d.dayofweek < 5).astype(int),
            "year_month": d.strftime("%Y-%m"),
            "quarter_label": [f"{y}-Q{q}" for y, q in zip(d.year, d.quarter)],
        })

    # --------------------------------------------------------------- tickets
    def _ticket_timestamps(self) -> pd.DatetimeIndex:
        days = pd.date_range(self.start, self.end, freq="D")
        t = np.arange(len(days)) / len(days)
        trend = 1.0 + 0.32 * t                                     # business growth
        month_f = np.array([1.08, 0.97, 1.0, 0.98, 0.97, 0.93, 0.90, 0.92, 1.0, 1.04, 1.22, 1.28])[days.month - 1]
        dow_f = np.array([1.22, 1.15, 1.10, 1.06, 1.00, 0.58, 0.47])[days.dayofweek]
        w = trend * month_f * dow_f
        chosen = self.rng.choice(len(days), self.n_tickets, p=w / w.sum())
        hour_w = np.array([0.4, 0.3, 0.25, 0.25, 0.3, 0.5, 1.0, 2.2, 4.0, 5.6, 6.2, 6.0, 5.2, 5.6,
                           5.9, 5.6, 5.0, 4.2, 3.2, 2.6, 2.0, 1.5, 1.0, 0.6])
        hours = self.rng.choice(24, self.n_tickets, p=hour_w / hour_w.sum())
        secs = self.rng.integers(0, 3600, self.n_tickets)
        ts = days[chosen] + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(secs, unit="s")
        return pd.DatetimeIndex(np.sort(ts.values))

    def tickets(self, customers: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
        n = self.n_tickets
        rng = self.rng
        created = self._ticket_timestamps()

        # ---- category (Billing volume jumps after the April-2025 pricing change)
        cats = list(ref.CATEGORIES)
        base_w = np.array([ref.CATEGORIES[c][3] for c in cats])
        billing_idx = cats.index("Billing & Payment")
        category = np.empty(n, dtype=object)
        post = created >= pd.Timestamp("2025-04-01")
        for mask, boost in ((~post, 1.0), (post, 1.65)):
            w = base_w.copy()
            w[billing_idx] *= boost
            category[mask] = rng.choice(cats, mask.sum(), p=w / w.sum())
        subcat = np.array([rng.choice(ref.CATEGORIES[c][1]) for c in category])
        dept = np.array([ref.CATEGORIES[c][0] for c in category])

        prios = list(ref.PRIORITIES)
        pw = np.array([ref.PRIORITIES[p][0] for p in prios])
        priority = rng.choice(prios, n, p=pw / pw.sum())
        # complaints and technical issues skew more urgent
        bump = np.isin(category, ["Complaint", "Technical Issue"]) & (rng.random(n) < 0.18)
        priority = np.where(bump & (priority == "Low"), "Medium", priority)
        priority = np.where(bump & (priority == "Medium"), "High", priority)

        chans = list(ref.CHANNELS)
        cw = np.array([ref.CHANNELS[c][0] for c in chans])
        # gradual shift toward live chat over time
        channel = np.empty(n, dtype=object)
        for yr, chat_boost in ((2023, 0.85), (2024, 1.0), (2025, 1.25)):
            m = created.year == yr
            w = cw.copy()
            w[chans.index("Live Chat")] *= chat_boost
            channel[m] = rng.choice(chans, m.sum(), p=w / w.sum())

        # ---- customers (must be registered before ticket creation)
        cust_reg = customers.registration_date.values
        cust_p = customers._propensity.values / customers._propensity.values.sum()
        cust_idx = rng.choice(len(customers), n, p=cust_p)
        bad = cust_reg[cust_idx] > created.values
        while bad.any():
            cust_idx[bad] = rng.choice(len(customers), bad.sum(), p=cust_p)
            bad = cust_reg[cust_idx] > created.values
        customer_id = customers.customer_id.values[cust_idx]

        # ---- agent assignment (eligible = in department, hired, not yet left)
        agent_id = np.empty(n, dtype=object)
        ag = agents.set_index("agent_id")
        for dep_id in ref.AGENTS_PER_DEPT:
            idx = np.where(dept == dep_id)[0]
            pool = ag[ag.department_id == dep_id]
            hire = pool.hire_date.values
            term = pool._termination.fillna(pd.Timestamp("2100-01-01")).values
            cap = pool._capacity.values
            ids = pool.index.values
            for i in idx:
                ok = (hire <= created.values[i]) & (term > created.values[i])
                p = cap * ok
                agent_id[i] = ids[rng.choice(len(ids), p=p / p.sum())]

        df = pd.DataFrame({
            "ticket_created_date": created, "customer_id": customer_id, "agent_id": agent_id,
            "department_id": dept, "ticket_category": category, "ticket_subcategory": subcat,
            "ticket_priority": priority, "support_channel": channel,
        })
        df["_exp"] = df.agent_id.map(ag.experience_level)

        # ---- workload factor: tickets per active agent per dept-month vs norm
        df["_ym"] = df.ticket_created_date.dt.to_period("M")
        load = df.groupby(["department_id", "_ym"]).size().rename("tickets").reset_index()
        active = []
        for _, r in load.iterrows():
            month_start = r["_ym"].to_timestamp()
            pool = agents[agents.department_id == r.department_id]
            act = ((pool.hire_date <= month_start + pd.offsets.MonthEnd(0)) &
                   (pool._termination.fillna(pd.Timestamp("2100-01-01")) > month_start)).sum()
            active.append(max(act, 1))
        load["per_agent"] = load.tickets / np.array(active)
        load["load_ratio"] = load.per_agent / load.groupby("department_id").per_agent.transform("median")
        df = df.merge(load[["department_id", "_ym", "load_ratio"]], on=["department_id", "_ym"], how="left")
        load_f = np.clip(df.load_ratio.values, 0.6, 2.5) ** 0.9

        # ---- escalation / reopen / first-contact resolution
        prio_esc = df.ticket_priority.map({"Critical": 2.0, "High": 1.4, "Medium": 1.0, "Low": 0.7}).values
        exp_esc = df._exp.map({"Junior": 1.4, "Mid-Level": 1.0, "Senior": 0.8, "Lead": 0.7}).values
        cat_esc = df.ticket_category.map({c: v[4] for c, v in ref.CATEGORIES.items()}).values
        escalated = rng.random(n) < np.clip(cat_esc * prio_esc * exp_esc, 0, 0.8)

        cat_reo = df.ticket_category.map({c: v[5] for c, v in ref.CATEGORIES.items()}).values
        exp_reo = df._exp.map({k: v[2] for k, v in ref.EXPERIENCE.items()}).values
        reopen_p = np.clip(cat_reo * exp_reo * np.where(escalated, 1.5, 1.0) * (0.8 + 0.4 * (load_f > 1.2)), 0, 0.7)
        reopened = rng.random(n) < reopen_p
        reopen_count = np.where(reopened, rng.choice([1, 2, 3], n, p=[0.8, 0.17, 0.03]), 0)

        ch_fcr = df.support_channel.map({c: v[3] for c, v in ref.CHANNELS.items()}).values
        cat_fcr = df.ticket_category.map({"Product Inquiry": 1.7, "Account Access": 1.6, "Order Status": 1.25,
                                          "Billing & Payment": 0.9, "Technical Issue": 0.6, "Delivery Problem": 0.55,
                                          "Returns & Refunds": 0.5, "Complaint": 0.4}).values
        pr_fcr = df.ticket_priority.map({"Low": 1.1, "Medium": 1.0, "High": 0.8, "Critical": 0.5}).values
        ex_fcr = df._exp.map({"Junior": 0.85, "Mid-Level": 1.0, "Senior": 1.12, "Lead": 1.2}).values
        fcr = (rng.random(n) < np.clip(ch_fcr * cat_fcr * pr_fcr * ex_fcr, 0, 0.85)) & ~escalated & ~reopened

        # ---- first response time (hours)
        ch_base = df.support_channel.map({c: v[1] for c, v in ref.CHANNELS.items()}).values
        pr_frt = df.ticket_priority.map({p: v[2] for p, v in ref.PRIORITIES.items()}).values
        frt = ch_base * pr_frt * rng.lognormal(0, 0.75, n) * load_f ** 0.6
        async_ch = np.isin(df.support_channel.values, ["Email", "Web Portal", "Social Media"])
        hr = df.ticket_created_date.dt.hour.values
        dow = df.ticket_created_date.dt.dayofweek.values
        out_of_hours = (hr < 8) | (hr >= 19) | (dow >= 5)
        hours_to_open = np.where(hr < 8, 8 - hr, 32 - hr) + np.where(dow == 5, 24, 0) + np.where(dow == 6, 0, 0)
        frt = frt + np.where(async_ch & out_of_hours, hours_to_open * rng.uniform(0.3, 0.9, n), 0)
        frt = np.clip(frt, 0.01, None)

        # ---- resolution time (hours, from creation)
        cat_base = df.ticket_category.map({c: v[2] for c, v in ref.CATEGORIES.items()}).values
        pr_res = df.ticket_priority.map({p: v[1] for p, v in ref.PRIORITIES.items()}).values
        ex_res = df._exp.map({k: v[1] for k, v in ref.EXPERIENCE.items()}).values
        ch_res = df.support_channel.map({c: v[2] for c, v in ref.CHANNELS.items()}).values
        q4 = np.where(df.ticket_created_date.dt.month.isin([11, 12]).values, 1.15, 1.0)
        work = (cat_base * pr_res * ex_res * ch_res * load_f * q4 * np.where(escalated, 1.9, 1.0)
                * (1 + 0.45 * reopen_count) * rng.lognormal(0, 0.62, n))
        res_h = np.where(fcr, frt + rng.uniform(0.05, 0.75, n), frt + work)

        df["escalation_flag"] = escalated.astype(int)
        df["reopened_count"] = reopen_count.astype(int)
        df["_fcr"] = fcr
        df["_frt_h"] = frt
        df["_res_h"] = res_h
        df["sla_target_hours"] = df.ticket_priority.map(config.SLA_TARGET_HOURS).astype(int)

        # ---- status as of the snapshot date
        first_resp = df.ticket_created_date + pd.to_timedelta(frt, unit="h")
        resolved = df.ticket_created_date + pd.to_timedelta(res_h, unit="h")
        status = np.full(n, "Closed", dtype=object)
        cancelled = rng.random(n) < 0.02
        not_done = resolved > self.snapshot
        age_days = (self.snapshot - df.ticket_created_date).dt.days.values
        stuck = (~cancelled) & (((age_days < 120) & (rng.random(n) < 0.06)) |
                                ((age_days >= 120) & (age_days < 400) & (rng.random(n) < 0.006)))
        unresolved = (not_done | stuck) & ~cancelled
        # a quarter of stalled tickets were never picked up (no first response)
        never_picked = stuck & (rng.random(n) < 0.25)
        responded = (first_resp <= self.snapshot) & ~never_picked
        status[unresolved & ~responded] = "Open"
        ip = unresolved & responded
        status[ip] = np.where(rng.random(ip.sum()) < 0.55, "In Progress", "Pending")
        status[cancelled] = "Cancelled"
        is_res = ~unresolved & ~cancelled
        recent = (self.snapshot - resolved).dt.days.values < 5
        status[is_res & recent] = "Resolved"
        status[is_res & ~recent & (rng.random(n) < 0.08)] = "Resolved"

        df["ticket_status"] = status
        df["first_response_date"] = first_resp.where(responded)
        df["resolved_date"] = resolved.where(pd.Series(is_res, index=df.index))
        # a cancelled ticket cannot have been reopened or escalated
        df.loc[cancelled, ["reopened_count", "escalation_flag"]] = 0

        res_types = {
            "Technical Issue": ["Technical Fix", "Workaround Provided", "Configuration Change"],
            "Account Access": ["Credentials Reset", "Access Restored"],
            "Billing & Payment": ["Account Adjustment", "Refund Issued", "Payment Re-processed"],
            "Order Status": ["Order Updated", "Information Provided"],
            "Delivery Problem": ["Reshipment", "Carrier Claim Filed", "Address Corrected"],
            "Returns & Refunds": ["Refund Issued", "Replacement Sent", "Return Approved"],
            "Product Inquiry": ["Information Provided", "Knowledge Base Article"],
            "Complaint": ["Goodwill Credit", "Apology & Explanation", "Policy Exception"],
        }
        rtype = np.array([rng.choice(res_types[c]) for c in df.ticket_category], dtype=object)
        rtype = np.where(escalated, "Escalated Resolution", rtype)
        rtype = np.where(fcr, "First Contact Resolution", rtype)
        df["resolution_type"] = np.where(is_res, rtype, None)

        df.insert(0, "ticket_id", [f"TCK-{i:06d}" for i in range(1, n + 1)])
        df["_cancelled"] = cancelled
        df["_unresolved"] = unresolved
        return df

    # -------------------------------------------------------------- feedback
    def feedback(self, tickets: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
        rng = self.rng
        t = tickets[tickets.ticket_status.isin(["Closed", "Resolved"])].copy()
        breached = t._res_h > t.sla_target_hours
        bad_exp = breached | (t.reopened_count > 0) | (t.escalation_flag == 1)
        respond = rng.random(len(t)) < np.where(bad_exp, 0.62, 0.50)
        t = t[respond].copy()
        breached = breached[respond]
        skill = t.agent_id.map(agents.set_index("agent_id")._skill).values
        ch_shift = t.support_channel.map({c: v[4] for c, v in ref.CHANNELS.items()}).values
        score = (4.35 - 1.05 * breached.values - 0.16 * np.log1p(t._frt_h.values)
                 - 0.55 * t.reopened_count.values - 0.45 * t.escalation_flag.values
                 + 0.30 * t._fcr.values + ch_shift + skill
                 - 0.25 * (t.ticket_category.values == "Complaint")
                 + rng.normal(0, 0.62, len(t)))
        csat = np.clip(np.round(score), 1, 5).astype(int)
        rating = np.clip(np.round(csat * 2 - 0.5 + rng.normal(0, 0.9, len(t))), 1, 10).astype(int)

        cat = np.empty(len(t), dtype=object)
        for i, (b, ro, c, s, tc) in enumerate(zip(breached.values, t.reopened_count.values, csat,
                                                   rng.random(len(t)), t.ticket_category.values)):
            if b and s < 0.6:
                cat[i] = "Response Speed"
            elif ro > 0 and s < 0.7:
                cat[i] = "Resolution Quality"
            elif tc == "Complaint" and s < 0.5:
                cat[i] = "Process & Policy"
            elif tc in ("Technical Issue", "Product Inquiry", "Returns & Refunds") and s < 0.25:
                cat[i] = "Product Issue"
            elif c >= 4:
                cat[i] = rng.choice(["Agent Professionalism", "Communication", "Resolution Quality", "Response Speed"],
                                    p=[0.35, 0.25, 0.25, 0.15])
            else:
                cat[i] = rng.choice(ref.FEEDBACK_CATEGORIES)
        sentiment = np.where(csat >= 4, "positive", np.where(csat == 3, "neutral", "negative"))
        comments = np.array([rng.choice(ref.COMMENTS[s]) for s in sentiment], dtype=object)
        comments[rng.random(len(t)) < 0.28] = None          # many customers leave no comment
        fdate = t.resolved_date + pd.to_timedelta(rng.exponential(1.4, len(t)) * 24 + 0.5, unit="h")
        fdate = fdate.where(fdate <= self.snapshot, self.snapshot)
        fb = pd.DataFrame({
            "ticket_id": t.ticket_id.values, "customer_id": t.customer_id.values,
            "feedback_date": fdate.values, "satisfaction_score": csat, "customer_rating": rating,
            "feedback_category": cat, "customer_comment": comments,
        }).sort_values("feedback_date").reset_index(drop=True)
        fb.insert(0, "feedback_id", [f"FBK-{i:06d}" for i in range(1, len(fb) + 1)])
        return fb

    # ---------------------------------------------------- agent performance
    def agent_performance(self, tickets: pd.DataFrame, feedback: pd.DataFrame) -> pd.DataFrame:
        """Monthly agent scorecards, derived from the simulated tickets so the
        two tables are mutually consistent."""
        rng = self.rng
        t = tickets[~tickets._cancelled].copy()
        t["frt_h"] = t._frt_h.where(t.first_response_date.notna())
        t["res_h"] = t._res_h.where(t.resolved_date.notna())
        t["sla_met"] = np.where(t.resolved_date.notna(), (t._res_h <= t.sla_target_hours).astype(float), np.nan)
        handle_min = (t.support_channel.map({"Phone": 14, "Live Chat": 18, "Email": 22, "Web Portal": 20, "Social Media": 16})
                      * (1 + 0.5 * t.reopened_count) * np.where(t.escalation_flag == 1, 1.6, 1.0)
                      * rng.lognormal(0, 0.35, len(t)))
        t["handle_h"] = handle_min / 60
        t["cmonth"] = t.ticket_created_date.dt.to_period("M")
        t["rmonth"] = t.resolved_date.dt.to_period("M")
        a = t.groupby(["agent_id", "cmonth"]).agg(tickets_assigned=("ticket_id", "count"),
                                                   average_response_time=("frt_h", "mean"),
                                                   handle_h=("handle_h", "sum"))
        r = t[t.resolved_date.notna()].groupby(["agent_id", "rmonth"]).agg(
            tickets_resolved=("ticket_id", "count"), average_resolution_time=("res_h", "mean"),
            sla_compliance_rate=("sla_met", "mean"))
        r.index.names = ["agent_id", "cmonth"]
        f = feedback.merge(t[["ticket_id", "agent_id", "rmonth"]], on="ticket_id")
        f = f.groupby(["agent_id", "rmonth"]).satisfaction_score.mean().rename("customer_satisfaction_score")
        f.index.names = ["agent_id", "cmonth"]
        perf = a.join(r, how="outer").join(f, how="left").reset_index()
        perf = perf[perf.cmonth <= pd.Period(self.end, "M")]
        perf[["tickets_assigned", "tickets_resolved"]] = perf[["tickets_assigned", "tickets_resolved"]].fillna(0).astype(int)
        perf["handle_h"] = perf.handle_h.fillna(0)
        # workload = ticket handling time + admin/meeting time per working month
        perf["workload_hours"] = (perf.handle_h + rng.uniform(18, 30, len(perf))).round(1)
        perf["sla_compliance_rate"] = (perf.sla_compliance_rate * 100).round(2)
        perf["average_response_time"] = perf.average_response_time.round(2)
        perf["average_resolution_time"] = perf.average_resolution_time.round(2)
        perf["customer_satisfaction_score"] = perf.customer_satisfaction_score.round(2)
        perf["performance_date"] = perf.cmonth.dt.to_timestamp(how="end").dt.normalize()
        perf = perf.sort_values(["performance_date", "agent_id"]).reset_index(drop=True)
        perf.insert(0, "performance_id", [f"PRF-{i:05d}" for i in range(1, len(perf) + 1)])
        return perf[["performance_id", "agent_id", "performance_date", "tickets_assigned", "tickets_resolved",
                     "average_response_time", "average_resolution_time", "customer_satisfaction_score",
                     "sla_compliance_rate", "workload_hours"]]

    # ------------------------------------------------------------ operations
    def operations(self) -> pd.DataFrame:
        rng = self.rng
        days = pd.date_range(self.start, self.end, freq="D")
        t = np.arange(len(days)) / len(days)
        rows = []
        for dep_id, procs in ref.PROCESSES.items():
            for op_type, proc, vol, fail, minutes, unit_cost in procs:
                dow = np.array([1.15, 1.1, 1.05, 1.05, 1.0, 0.55, 0.45])[days.dayofweek]
                season = np.where(days.month.isin([11, 12]), 1.30, 1.0)
                volume = rng.poisson(vol * (1 + 0.28 * t) * dow * season)
                fr = np.full(len(days), fail)
                if proc == "Refund Approval":
                    fr = fail * (1 + 0.9 * t)                     # worsening over time
                if proc == "Payment Reconciliation":
                    fr = np.where(days >= pd.Timestamp("2025-04-01"), fail * 1.8, fail)
                incident = rng.random(len(days)) < 0.012
                fr = np.clip(fr * np.where(incident, rng.uniform(3, 6, len(days)), 1) * rng.lognormal(0, 0.18, len(days)), 0, 0.6)
                failed = rng.binomial(volume, fr)
                ptime = minutes * rng.lognormal(0, 0.12, len(days))
                if proc == "Shipment Dispatch":
                    ptime = ptime * np.where(days.month.isin([11, 12]), 1.55, 1.0)
                if proc == "Returns Inspection":
                    ptime = ptime * (1 + 0.25 * t)
                ptime = ptime * np.where(incident, 1.6, 1.0)
                cost_trend = (1 + 0.10 * t) if proc != "Payment Reconciliation" else (1 + 0.30 * t)
                cost = volume * unit_cost * cost_trend * rng.lognormal(0, 0.08, len(days)) + 120 * rng.uniform(0.8, 1.2, len(days))
                frate = np.divide(failed, volume, out=np.zeros(len(days)), where=volume > 0)
                status = np.where(frate >= 0.10, "Critical", np.where(frate >= 0.05, "Degraded", "Normal"))
                rows.append(pd.DataFrame({
                    "department_id": dep_id, "operation_date": days, "operation_type": op_type,
                    "process_name": proc, "total_transactions": volume,
                    "successful_transactions": volume - failed, "failed_transactions": failed,
                    "processing_time_minutes": ptime.round(2), "operational_cost": cost.round(2),
                    "operational_status": status,
                }))
        ops = pd.concat(rows).sort_values(["operation_date", "department_id", "process_name"]).reset_index(drop=True)
        ops.insert(0, "operation_id", [f"OPS-{i:06d}" for i in range(1, len(ops) + 1)])
        return ops

    def business_costs(self, departments: pd.DataFrame) -> pd.DataFrame:
        rng = self.rng
        months = pd.date_range(self.start, self.end, freq="MS")
        t = np.arange(len(months)) / len(months)
        rows = []
        for _, d in departments.iterrows():
            monthly = d.operational_budget / 12
            for cat, (share, direct_share) in ref.COST_CATEGORIES.items():
                base = monthly * share * (1 + 0.12 * t) * rng.lognormal(0, 0.05, len(months))
                if d.department_id == "DEP-02" and cat == "Outsourcing":
                    # Billing brings in an outsourcing partner after attrition in 2025
                    base = base * np.where(months >= pd.Timestamp("2025-04-01"), 2.4, 1.0)
                if cat == "Training & Development":
                    base = base * np.where(months.month.isin([1, 9]), 1.8, 0.9)
                direct = base * direct_share
                indirect = base - direct
                rows.append(pd.DataFrame({
                    "department_id": d.department_id, "cost_date": months, "cost_category": cat,
                    "direct_cost": direct.round(2), "indirect_cost": indirect.round(2),
                }))
        c = pd.concat(rows).sort_values(["cost_date", "department_id", "cost_category"]).reset_index(drop=True)
        c["total_cost"] = (c.direct_cost + c.indirect_cost).round(2)
        c.insert(0, "cost_id", [f"CST-{i:05d}" for i in range(1, len(c) + 1)])
        return c

    def finalise_customer_status(self, customers: pd.DataFrame, tickets: pd.DataFrame,
                                 feedback: pd.DataFrame) -> pd.DataFrame:
        """Churn/inactivity is more likely for customers with poor experiences."""
        rng = self.rng
        c = customers.copy()
        csat = feedback.groupby("customer_id").satisfaction_score.mean()
        last = tickets.groupby("customer_id").ticket_created_date.max()
        c["_csat"] = c.customer_id.map(csat).fillna(4.0)
        c["_last"] = c.customer_id.map(last)
        p_churn = np.clip(0.05 + 0.09 * (4.2 - c._csat).clip(lower=0), 0, 0.45)
        u = rng.random(len(c))
        status = np.where(u < p_churn, "Churned", "Active")
        inactive = (status == "Active") & ((c._last.isna()) | (c._last < pd.Timestamp("2025-01-01"))) & (rng.random(len(c)) < 0.6)
        status = np.where(inactive, "Inactive", status)
        c["customer_status"] = status
        return c

    # ------------------------------------------------------ defect injection
    def inject_defects(self, clean: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict]:
        """Return raw copies with realistic data-quality issues + a manifest."""
        rng = np.random.default_rng(self.seed + 99)
        raw = {k: v.copy() for k, v in clean.items()}
        m: dict = {}

        # Customers --------------------------------------------------------
        c = raw["customers"]
        idx = rng.choice(c.index, 45, replace=False)
        c.loc[idx, "customer_region"] = np.nan
        m["customers_missing_region"] = 45
        idx = rng.choice(c.index, 70, replace=False)
        c.loc[idx, "customer_lifetime_value"] = np.nan
        m["customers_missing_clv"] = 70
        c["registration_date"] = c.registration_date.dt.strftime("%Y-%m-%d").astype(object)
        idx = rng.choice(c.index, 60, replace=False)
        c.loc[idx, "registration_date"] = pd.to_datetime(c.loc[idx, "registration_date"]).dt.strftime("%d-%b-%Y")
        m["customers_alt_date_format"] = 60
        idx = rng.choice(c.index, 40, replace=False)
        c.loc[idx, "customer_segment"] = c.loc[idx, "customer_segment"].str.upper()
        m["customers_bad_case_segment"] = 40
        dups = c.sample(30, random_state=1)
        raw["customers"] = pd.concat([c, dups]).sort_values("customer_id").reset_index(drop=True)
        m["customers_exact_duplicates"] = 30

        # Tickets ----------------------------------------------------------
        t = raw["support_tickets"]
        resolved_idx = t.index[t.resolved_date.notna()]
        swap = rng.choice(resolved_idx, 25, replace=False)
        t.loc[swap, "resolved_date"] = t.loc[swap, "ticket_created_date"] - pd.to_timedelta(rng.uniform(1, 30, 25), unit="h")
        m["tickets_resolved_before_created"] = 25
        fr_idx = np.setdiff1d(resolved_idx, swap)
        miss = rng.choice(fr_idx, 90, replace=False)
        t.loc[miss, "first_response_date"] = pd.NaT
        m["tickets_missing_first_response"] = 90
        idx = rng.choice(t.index, 120, replace=False)
        t.loc[idx, "support_channel"] = np.nan
        m["tickets_missing_channel"] = 120
        variants = {"Email": ["email", "E-mail", "EMAIL"], "Live Chat": ["chat", "live chat", "LiveChat"],
                    "Phone": ["phone", "PHONE"], "Web Portal": ["web", "Web portal"], "Social Media": ["social", "Social"]}
        idx = rng.choice(t.index[t.support_channel.notna()], 400, replace=False)
        t.loc[idx, "support_channel"] = [rng.choice(variants[v]) for v in t.loc[idx, "support_channel"]]
        m["tickets_channel_label_variants"] = 400
        idx = rng.choice(t.index, 300, replace=False)
        t.loc[idx, "ticket_priority"] = t.loc[idx, "ticket_priority"].str.upper()
        m["tickets_priority_upper_case"] = 300
        idx = rng.choice(t.index, 180, replace=False)
        t.loc[idx, "sla_target_hours"] = t.loc[idx, "sla_target_hours"].map({8: 24, 24: 48, 48: 72, 72: 48})
        m["tickets_wrong_sla_target"] = 180
        idx = rng.choice(t.index, 15, replace=False)
        t.loc[idx, "agent_id"] = [f"AGT-{x}" for x in rng.integers(900, 999, 15)]
        m["tickets_orphan_agent"] = 15
        dups = t.sample(150, random_state=2)
        raw["support_tickets"] = pd.concat([t, dups]).sort_values("ticket_id").reset_index(drop=True)
        m["tickets_exact_duplicates"] = 150

        # Feedback ---------------------------------------------------------
        f = raw["customer_feedback"]
        idx = rng.choice(f.index, 40, replace=False)
        f.loc[idx, "satisfaction_score"] = rng.choice([0, 6, 7, 10, -1], 40)
        m["feedback_out_of_range_score"] = 40
        valid_idx = np.setdiff1d(f.index, idx)
        miss = rng.choice(valid_idx, 110, replace=False)
        f["satisfaction_score"] = f.satisfaction_score.astype("Float64")
        f.loc[miss, "satisfaction_score"] = pd.NA
        m["feedback_missing_score"] = 110
        idx = rng.choice(f.index, 25, replace=False)
        f.loc[idx, "customer_id"] = f.loc[np.roll(idx, 1), "customer_id"].values
        m["feedback_customer_mismatch_max"] = 25
        orph = f.sample(12, random_state=3).copy()
        orph["feedback_id"] = [f"FBK-9{i:05d}" for i in range(12)]
        orph["ticket_id"] = [f"TCK-9{i:05d}" for i in range(12)]
        dups = f.sample(60, random_state=4)
        raw["customer_feedback"] = pd.concat([f, orph, dups]).reset_index(drop=True)
        m["feedback_orphan_ticket"] = 12
        m["feedback_exact_duplicates"] = 60

        # Operations -------------------------------------------------------
        o = raw["operations"]
        idx = rng.choice(o.index, 70, replace=False)
        o.loc[idx, "processing_time_minutes"] = np.nan
        m["operations_missing_processing_time"] = 70
        idx = rng.choice(o.index, 12, replace=False)
        o.loc[idx, "operational_cost"] = -o.loc[idx, "operational_cost"]
        m["operations_negative_cost"] = 12
        idx = rng.choice(np.setdiff1d(o.index, idx), 18, replace=False)
        o.loc[idx, "operational_cost"] = o.loc[idx, "operational_cost"] * rng.uniform(12, 25, 18)
        m["operations_cost_outliers"] = 18
        idx = rng.choice(o.index, 20, replace=False)
        o.loc[idx, "successful_transactions"] = o.loc[idx, "successful_transactions"] + rng.integers(5, 50, 20)
        m["operations_success_failed_mismatch"] = 20

        # Business costs ---------------------------------------------------
        b = raw["business_costs"]
        idx = rng.choice(b.index, 25, replace=False)
        b.loc[idx, "total_cost"] = (b.loc[idx, "total_cost"] * rng.uniform(1.05, 1.3, 25)).round(2)
        m["costs_total_mismatch"] = 25
        idx = rng.choice(np.setdiff1d(b.index, idx), 15, replace=False)
        b.loc[idx, "indirect_cost"] = np.nan
        m["costs_missing_indirect"] = 15

        # Agent performance -----------------------------------------------
        p = raw["agent_performance"]
        idx = rng.choice(p.index[p.sla_compliance_rate.notna()], 8, replace=False)
        p.loc[idx, "sla_compliance_rate"] = rng.uniform(101, 140, 8).round(2)
        m["performance_sla_over_100"] = 8
        return raw, m

    # -------------------------------------------------------------- orchestr
    def generate(self) -> GeneratedData:
        log.info("Generating dimensions")
        departments = self.departments()
        agents = self.agents()
        customers = self.customers()
        log.info("Simulating %s tickets", self.n_tickets)
        tickets = self.tickets(customers, agents)
        feedback = self.feedback(tickets, agents)
        perf = self.agent_performance(tickets, feedback)
        customers = self.finalise_customer_status(customers, tickets, feedback)
        ops = self.operations()
        costs = self.business_costs(departments)
        cal = self.calendar()

        ticket_cols = ["ticket_id", "customer_id", "agent_id", "department_id", "ticket_created_date",
                       "first_response_date", "resolved_date", "ticket_category", "ticket_subcategory",
                       "ticket_priority", "ticket_status", "support_channel", "resolution_type",
                       "reopened_count", "escalation_flag", "sla_target_hours"]
        clean = {
            "customers": customers[[c for c in customers.columns if not c.startswith("_")]],
            "departments": departments,
            "agents": agents[[c for c in agents.columns if not c.startswith("_")]],
            "support_tickets": tickets[ticket_cols].copy(),
            "customer_feedback": feedback,
            "operations": ops,
            "agent_performance": perf,
            "business_costs": costs,
            "calendar": cal,
        }
        for col in ("ticket_created_date", "first_response_date", "resolved_date"):
            clean["support_tickets"][col] = clean["support_tickets"][col].dt.floor("s")
        raw, manifest = self.inject_defects(clean)
        manifest.update({"seed": self.seed, "snapshot_date": config.SNAPSHOT_DATE,
                         "clean_row_counts": {k: len(v) for k, v in clean.items()},
                         "raw_row_counts": {k: len(v) for k, v in raw.items()}})
        return GeneratedData(clean=clean, raw=raw, manifest=manifest)


def save_raw(data: GeneratedData, out_dir=config.RAW_DIR) -> None:
    """Write raw CSVs and the defect manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in data.raw.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    (out_dir / "_generation_manifest.json").write_text(json.dumps(data.manifest, indent=2, default=str))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = SupportDataGenerator().generate()
    save_raw(data)
    for k, v in data.manifest["raw_row_counts"].items():
        log.info("raw %-20s %7d rows", k, v)


if __name__ == "__main__":
    main()
