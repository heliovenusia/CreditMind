import numpy as np
from typing import List

REASON_MAP = {
    "monthly_income_med": "Low documented monthly income",
    "income_regularity_cv": "Irregular income pattern",
    "spend_volatility": "High spend volatility",
    "ess_disc_ratio": "High discretionary spend share",
    "buffer_days": "Low liquidity buffer",
    "emi_ontime_rate": "Poor EMI on-time rate",
    "low_balance_event_rate": "Frequent low-balance events",
    "digital_spend_share": "Low digital adoption",

    "sms_credit_freq": "Sparse credit inflow alerts (SMS)",
    "sms_debit_freq": "High debit activity (SMS)",
    "sms_due_freq": "Frequent bill/EMI due alerts",
    "sms_paid_freq": "Low bill paid confirmations",
    "sms_income_median": "Low typical income (from SMS alerts)",
    "sms_spend_median": "High typical spend (from SMS alerts)",

    "telco_regularity_index": "Irregular recharge behaviour",
    "telco_unique_contacts": "Narrow social contact network",
    "telco_sim_age_months": "Low SIM tenure (identity instability)",
    "telco_data_usage_gb": "Low digital activity (data usage)",
    "telco_home_stability": "Unstable home/work location pattern",
    "telco_avg_call_duration": "Erratic call duration patterns",
}

COACH_TIPS = {
    "Low documented monthly income": "Route income to bank consistently; avoid cash-only inflows.",
    "Irregular income pattern": "Stabilize income deposits (aim for consistent monthly inflow).",
    "High spend volatility": "Keep monthly spending within ±15% of your median.",
    "High discretionary spend share": "Trim discretionary spends until essential:discretionary ≥ 0.8.",
    "Low liquidity buffer": "Maintain an average balance ≈ 10 days of expenses.",
    "Poor EMI on-time rate": "Enable auto-pay for EMIs and pay 48h before due.",
    "Frequent low-balance events": "Set a low-balance alert and keep a floor buffer.",
    "Low digital adoption": "Prefer UPI/card to build a verifiable digital footprint.",

    "Sparse credit inflow alerts (SMS)": "Ensure salaries/receipts generate bank SMS (route to the bank).",
    "High debit activity (SMS)": "Reduce unnecessary debits; consolidate bills to one auto-pay.",
    "Frequent bill/EMI due alerts": "Pay within 48h of due alerts; set calendar reminders.",
    "Low bill paid confirmations": "Enable auto-pay so paid confirmations appear consistently.",
    "Low typical income (from SMS alerts)": "Increase bank-documented income; avoid cash transactions.",
    "High typical spend (from SMS alerts)": "Cap monthly spend and smooth large purchases.",

    "Irregular recharge behaviour": "Recharge on a fixed cycle to signal stability.",
    "Narrow social contact network": "Sustain regular contact with a broader stable network.",
    "Low SIM tenure (identity instability)": "Keep the same number active; avoid frequent SIM changes.",
    "Low digital activity (data usage)": "Use digital channels for bills and payments.",
    "Unstable home/work location pattern": "Maintain stable residence/work patterns for a few months.",
    "Erratic call duration patterns": "Normalize daily patterns; avoid sharp usage spikes.",
}


def decide(score: float) -> str:
    if score >= 0.75:
        return "APPROVE"
    elif score >= 0.5:
        return "REVIEW"
    return "DECLINE"

def top_reason_codes(feature_names: List[str], shap_values: np.ndarray, k: int = 3) -> List[str]:
    idx = np.argsort(np.abs(shap_values))[::-1][:k]
    return [REASON_MAP.get(feature_names[i], feature_names[i]) for i in idx]