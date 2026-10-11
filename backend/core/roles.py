"""
roles.py — who is allowed to see what.

This is the single place access rules are defined. The service layer reads it
and drops columns BEFORE returning data. The frontend never sees a value a role
isn't entitled to, so there is nothing for the UI to hide.

Each role declares:
    denied_columns   columns stripped from every result set
    views            which screens appear in the navigation
    landing_question which question opens by default
    headline         which metrics the dashboard leads with
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Role:
    name: str
    description: str
    denied_columns: tuple = ()
    views: tuple = ()
    landing_question: str = ""
    headline: tuple = field(default=())


ROLES = {
    "Study Manager": Role(
        name="Study Manager",
        description="Oversees the whole trial. Full access to all five systems.",
        denied_columns=(),
        views=("ask", "graph", "catalog", "review", "health", "about"),
        landing_question="sites_at_risk",
        headline=("enrolled_patients", "open_safety_cases", "kits_remaining"),
    ),
    "Finance Analyst": Role(
        name="Finance Analyst",
        description="Tracks site payments. No access to patient or safety data.",
        denied_columns=("enrolled_patients", "open_safety_cases", "adverse_events",
                        "patient_id", "case_patient_ref", "arm", "age", "sex"),
        views=("ask", "catalog", "health", "about"),
        landing_question="overdue_payments",
        headline=("invoice_amount_usd", "days_payment_overdue"),
    ),
    "Site Monitor": Role(
        name="Site Monitor",
        description="Oversees site conduct and supply. No access to financial data.",
        denied_columns=("invoice_amount_usd", "days_payment_overdue"),
        views=("ask", "graph", "catalog", "review", "health", "about"),
        landing_question="low_supply",
        headline=("enrolled_patients", "open_safety_cases", "kits_remaining"),
    ),
    "Data Steward": Role(
        name="Data Steward",
        description="Owns data quality and identity matching. Sees structure, not "
                    "patient detail.",
        denied_columns=("arm", "age", "sex", "invoice_amount_usd"),
        views=("catalog", "review", "health", "graph", "ask", "about"),
        landing_question="incomplete_sites",
        headline=("systems_contributing",),
    ),
}

DEFAULT_ROLE = "Study Manager"


def get(role_name: str) -> Role:
    return ROLES.get(role_name, ROLES[DEFAULT_ROLE])


def names() -> list:
    return list(ROLES)
