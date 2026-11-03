"""Static reference data used by the generator (departments, categories, processes...).

Keeping these lookups separate from the simulation logic makes the business
assumptions easy to read and change.
"""

DEPARTMENTS = [
    # id, name, location, annual operational budget (USD) for staffing & overhead.
    # (Variable transaction-processing costs are tracked separately in operations.)
    ("DEP-01", "Technical Support", "Austin, US", 900_000),
    ("DEP-02", "Billing & Accounts", "Dublin, IE", 520_000),
    ("DEP-03", "Order Management", "Austin, US", 480_000),
    ("DEP-04", "Logistics & Delivery", "Rotterdam, NL", 650_000),
    ("DEP-05", "Returns & Refunds", "Manila, PH", 380_000),
    ("DEP-06", "Customer Success", "Toronto, CA", 560_000),
]

# Ticket category -> (owning department, subcategories, base resolution hours,
#                     category weight, escalation propensity, reopen propensity)
CATEGORIES = {
    "Technical Issue": ("DEP-01", ["Login Failure", "App Crash", "Integration Error", "Performance Degradation", "Data Sync Issue"], 30, 0.24, 0.16, 0.12),
    "Account Access": ("DEP-01", ["Password Reset", "2FA Problem", "Account Locked", "Permission Change"], 9, 0.11, 0.04, 0.05),
    "Billing & Payment": ("DEP-02", ["Incorrect Charge", "Payment Failed", "Invoice Request", "Subscription Change", "Double Billing"], 20, 0.18, 0.09, 0.09),
    "Order Status": ("DEP-03", ["Order Tracking", "Order Modification", "Order Cancellation", "Missing Items"], 16, 0.13, 0.05, 0.06),
    "Delivery Problem": ("DEP-04", ["Late Delivery", "Damaged Package", "Wrong Address", "Lost Shipment"], 34, 0.12, 0.11, 0.10),
    "Returns & Refunds": ("DEP-05", ["Refund Status", "Return Label", "Refund Denied", "Exchange Request"], 38, 0.12, 0.10, 0.14),
    "Product Inquiry": ("DEP-06", ["Feature Question", "Pricing Question", "Compatibility", "Upgrade Options"], 7, 0.06, 0.02, 0.03),
    "Complaint": ("DEP-06", ["Service Complaint", "Agent Behaviour", "Policy Complaint", "Product Quality"], 28, 0.04, 0.22, 0.13),
}

PRIORITIES = {  # weight, resolution factor, FRT factor
    "Critical": (0.07, 0.22, 0.20),
    "High": (0.21, 0.50, 0.45),
    "Medium": (0.42, 1.00, 1.00),
    "Low": (0.30, 1.45, 1.50),
}

CHANNELS = {  # weight, base first-response hours, resolution factor, FCR propensity, CSAT shift
    "Email": (0.33, 5.0, 1.10, 0.18, 0.00),
    "Phone": (0.22, 0.06, 0.80, 0.42, 0.10),
    "Live Chat": (0.24, 0.10, 0.85, 0.38, 0.08),
    "Web Portal": (0.14, 7.5, 1.15, 0.15, -0.05),
    "Social Media": (0.07, 3.0, 1.20, 0.20, -0.20),
}

EXPERIENCE = {  # weight, resolution speed multiplier, reopen multiplier
    "Junior": (0.30, 1.30, 1.6),
    "Mid-Level": (0.38, 1.00, 1.0),
    "Senior": (0.24, 0.85, 0.75),
    "Lead": (0.08, 0.75, 0.6),
}

SHIFTS = ["Morning", "Afternoon", "Night"]
AGENT_LOCATIONS = {
    "DEP-01": ["Austin, US", "Remote - US", "Manila, PH"],
    "DEP-02": ["Dublin, IE", "Remote - EU"],
    "DEP-03": ["Austin, US", "Remote - US"],
    "DEP-04": ["Rotterdam, NL", "Remote - EU"],
    "DEP-05": ["Manila, PH"],
    "DEP-06": ["Toronto, CA", "Remote - US"],
}
TEAMS = {
    "DEP-01": ["Tier 1 Support", "Tier 2 Engineering"],
    "DEP-02": ["Billing Operations"],
    "DEP-03": ["Order Desk"],
    "DEP-04": ["Delivery Exceptions"],
    "DEP-05": ["Returns Desk"],
    "DEP-06": ["Customer Success", "Escalations Desk"],
}
AGENTS_PER_DEPT = {"DEP-01": 17, "DEP-02": 9, "DEP-03": 8, "DEP-04": 8, "DEP-05": 8, "DEP-06": 10}

REGIONS = {
    "North America": (0.38, ["United States", "Canada", "Mexico"], [0.78, 0.17, 0.05]),
    "Europe": (0.30, ["United Kingdom", "Germany", "France", "Netherlands", "Spain", "Ireland"], [0.27, 0.24, 0.17, 0.12, 0.12, 0.08]),
    "Asia Pacific": (0.20, ["Australia", "India", "Japan", "Singapore", "Philippines"], [0.30, 0.28, 0.18, 0.14, 0.10]),
    "Latin America": (0.08, ["Brazil", "Chile", "Colombia", "Argentina"], [0.50, 0.18, 0.17, 0.15]),
    "Middle East & Africa": (0.04, ["United Arab Emirates", "South Africa", "Saudi Arabia"], [0.40, 0.35, 0.25]),
}

SEGMENTS = {  # weight, CLV lognormal mean, sigma, ticket propensity
    "Enterprise": (0.12, 10.6, 0.55, 3.2),
    "Mid-Market": (0.23, 9.4, 0.55, 1.8),
    "Small Business": (0.30, 8.2, 0.60, 1.0),
    "Consumer": (0.35, 6.4, 0.70, 0.55),
}

# Operations: department -> list of (operation_type, process_name, base daily volume,
#   base failure rate, minutes per transaction, unit cost USD)
PROCESSES = {
    "DEP-01": [("Service Requests", "Account Provisioning", 420, 0.020, 3.5, 0.95),
               ("Service Requests", "Password Reset Automation", 900, 0.012, 0.8, 0.12)],
    "DEP-02": [("Payment Processing", "Invoice Generation", 1500, 0.008, 0.6, 0.18),
               ("Payment Processing", "Payment Reconciliation", 1100, 0.030, 2.2, 0.55),
               ("Refund Processing", "Refund Approval", 260, 0.055, 9.5, 2.40)],
    "DEP-03": [("Order Processing", "Order Validation", 2400, 0.015, 0.9, 0.20),
               ("Order Processing", "Order Entry", 1900, 0.010, 1.4, 0.26)],
    "DEP-04": [("Fulfillment", "Shipment Dispatch", 1700, 0.022, 4.0, 1.10),
               ("Fulfillment", "Carrier Handoff", 1600, 0.018, 1.8, 0.48)],
    "DEP-05": [("Returns Processing", "Returns Inspection", 300, 0.040, 14.0, 3.10),
               ("Returns Processing", "Restocking", 280, 0.020, 6.0, 1.30)],
    "DEP-06": [("Customer Onboarding", "Onboarding Setup", 120, 0.025, 25.0, 6.50),
               ("Customer Onboarding", "Contract Renewal", 90, 0.018, 18.0, 4.20)],
}

COST_CATEGORIES = {  # share of monthly budget, direct share of the category cost
    "Personnel": (0.58, 0.92),
    "Technology & Software": (0.14, 0.80),
    "Facilities": (0.08, 0.30),
    "Training & Development": (0.04, 0.85),
    "Outsourcing": (0.10, 0.95),
    "Telecommunications": (0.06, 0.70),
}

FEEDBACK_CATEGORIES = ["Response Speed", "Resolution Quality", "Agent Professionalism",
                       "Communication", "Product Issue", "Process & Policy"]

COMMENTS = {
    "positive": [
        "Quick and friendly help, issue sorted.",
        "The agent understood the problem straight away.",
        "Very professional, thank you for the fast resolution.",
        "Great experience, clear explanation of the fix.",
        "Resolved on the first call, appreciated.",
        "Helpful and patient support.",
    ],
    "neutral": [
        "Issue resolved but it took a while.",
        "Okay experience, had to explain twice.",
        "Fine, although updates could be more frequent.",
        "Resolved eventually.",
    ],
    "negative": [
        "Waited far too long for a reply.",
        "Had to contact support several times for the same problem.",
        "The problem came back after it was marked as resolved.",
        "Was passed between teams with no ownership.",
        "Still not happy with how this was handled.",
        "Slow response and no clear updates.",
    ],
}
