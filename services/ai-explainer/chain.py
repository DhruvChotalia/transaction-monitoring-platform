import os

from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

_llm: ChatAnthropic | None = None

PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a financial fraud analyst AI. Given a flagged transaction, write a concise, "
        "clear explanation (2-3 sentences) for a bank operations team explaining WHY this transaction "
        "was flagged. Be specific about the risk factors. Use plain English — no jargon.",
    ),
    (
        "human",
        """Transaction details:
- Transaction ID: {transaction_id}
- Amount: ${amount:.2f}
- Merchant: {merchant_name} ({merchant_category})
- Time: {hour_of_day}:00 ({day_name})
- Distance from cardholder home: {geo_dist:.1f} km
- ML Fraud Probability: {fraud_probability:.1%}
- Rules triggered: {rule_flags}

Explain why this transaction was flagged.""",
    ),
])

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(
            model="claude-haiku-4-5",
            anthropic_api_key=ANTHROPIC_API_KEY,
            max_tokens=200,
        )
    return _llm


async def explain_alert(alert: dict) -> str:
    if not ANTHROPIC_API_KEY:
        return _fallback_explanation(alert)

    chain = PROMPT | get_llm()
    rule_flags = alert.get("rule_flags", [])
    response = await chain.ainvoke({
        "transaction_id": alert.get("transaction_id", "N/A"),
        "amount": alert.get("amount", 0),
        "merchant_name": alert.get("merchant_name", "Unknown"),
        "merchant_category": alert.get("merchant_category", "Unknown"),
        "hour_of_day": alert.get("hour_of_day", 0),
        "day_name": DAY_NAMES[alert.get("day_of_week", 0) % 7],
        "geo_dist": alert.get("geo_dist", 0),
        "fraud_probability": alert.get("fraud_probability", 0),
        "rule_flags": ", ".join(rule_flags) if rule_flags else "ML score only",
    })
    return response.content


def _fallback_explanation(alert: dict) -> str:
    flags = alert.get("rule_flags", [])
    prob = alert.get("fraud_probability", 0)
    parts = [f"Fraud probability: {prob:.1%}."]
    if "high_amount" in flags or "very_high_amount" in flags:
        parts.append(f"Amount of ${alert.get('amount', 0):.2f} significantly exceeds typical transaction sizes.")
    if "late_night" in flags or "late_night_high_risk" in flags:
        parts.append(f"Transaction occurred at {alert.get('hour_of_day', 0)}:00 — a high-risk time window.")
    if "high_risk_category" in flags:
        parts.append(f"Merchant category '{alert.get('merchant_category')}' is associated with elevated fraud rates.")
    if "high_geo_dist" in flags:
        parts.append(f"Location is {alert.get('geo_dist', 0):.0f}km from cardholder home address.")
    return " ".join(parts)
