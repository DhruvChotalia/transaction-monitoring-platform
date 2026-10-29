HIGH_RISK_CATEGORIES = {"shopping_net", "misc_net", "grocery_pos"}

RULES = [
    {
        "name": "high_amount",
        "description": "Amount exceeds $1,000",
        "check": lambda t: t["amount"] > 1000,
        "severity": "CRITICAL",
    },
    {
        "name": "very_high_amount",
        "description": "Amount exceeds $5,000",
        "check": lambda t: t["amount"] > 5000,
        "severity": "CRITICAL",
    },
    {
        "name": "late_night",
        "description": "Transaction between 22:00–04:00",
        "check": lambda t: t["hour_of_day"] >= 22 or t["hour_of_day"] <= 4,
        "severity": "WARNING",
    },
    {
        "name": "high_risk_category",
        "description": "High-risk merchant category",
        "check": lambda t: t["merchant_category"] in HIGH_RISK_CATEGORIES,
        "severity": "WARNING",
    },
    {
        "name": "high_geo_dist",
        "description": "Transaction > 500km from cardholder home",
        "check": lambda t: t["geo_dist"] > 500,
        "severity": "WARNING",
    },
    {
        "name": "late_night_high_risk",
        "description": "Late-night transaction in high-risk category",
        "check": lambda t: (t["hour_of_day"] >= 22 or t["hour_of_day"] <= 4)
        and t["merchant_category"] in HIGH_RISK_CATEGORIES,
        "severity": "CRITICAL",
    },
]


def evaluate(txn: dict) -> list[str]:
    return [r["name"] for r in RULES if r["check"](txn)]
