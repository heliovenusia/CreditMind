import io
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

def _safe_cv(series):
    mu = np.mean(series)
    sigma = np.std(series)
    return 0.0 if mu == 0 else float(sigma / (mu + 1e-9))

def features_from_aa(aa_payload: Dict[str, Any]) -> Dict[str, float]:
    tx = pd.DataFrame(aa_payload.get("transactions", []))
    if tx.empty:
        return {}
    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    tx = tx.sort_values("timestamp")
    tx["month"] = tx["timestamp"].dt.to_period("M").astype(str)

    inflow = tx.query("type=='CREDIT'")["amount"] if "type" in tx else pd.Series(dtype=float)
    outflow = tx.query("type=='DEBIT'")["amount"] if "type" in tx else pd.Series(dtype=float)

    # income regularity by month (credits)
    if not inflow.empty:
        inflow_month = tx.query("type=='CREDIT'").groupby("month")["amount"].sum()
        income_regularity_cv = _safe_cv(inflow_month.values)
        monthly_income_med = float(np.median(inflow_month.values))
    else:
        income_regularity_cv = 1.0
        monthly_income_med = 0.0

    # spend volatility (debits)
    if not outflow.empty:
        outflow_month = tx.query("type=='DEBIT'").groupby("month")["amount"].sum()
        if len(outflow_month) > 0:
            iqr = float(np.percentile(outflow_month.values, 75) - np.percentile(outflow_month.values, 25))
            med = float(np.median(outflow_month.values)) if len(outflow_month)>0 else 0.0
            spend_volatility = 0.0 if med == 0 else iqr / (med + 1e-9)
        else:
            spend_volatility = 1.0
    else:
        spend_volatility = 1.0

    ESSENTIAL = {"BILL_UTILITY"}
    DISCRETIONARY = {"CARD_POS","WALLET_TOPUP","UPI"}
    tx_debit = tx[tx["type"]=="DEBIT"]
    ess = tx_debit[tx_debit["channel"].isin(ESSENTIAL)]["amount"].sum() if not tx_debit.empty else 0.0
    dis = tx_debit[tx_debit["channel"].isin(DISCRETIONARY)]["amount"].sum() if not tx_debit.empty else 0.0
    ess_disc_ratio = float(ess / (dis + 1e-9))

    if "balance_after" in tx and not tx_debit.empty:
        avg_balance = float(tx["balance_after"].astype(float).mean())
        daily_outflow = tx_debit.groupby(tx_debit["timestamp"].dt.date)["amount"].sum().mean()
        buffer_days = float(avg_balance / (daily_outflow + 1e-9)) if daily_outflow and daily_outflow>0 else 0.0
    else:
        buffer_days = 0.0

    emi = tx[tx["channel"]=="EMI_PAYMENT"]
    ontime_rate = 0.0
    if not emi.empty:
        days = emi["timestamp"].dt.day.values
        ontime = np.mean((days>=5)&(days<=9))
        ontime_rate = float(ontime)

    low_thresh = np.quantile(tx["balance_after"], 0.1) if "balance_after" in tx else 0
    low_balance_events = float(np.mean(tx["balance_after"] <= low_thresh)) if "balance_after" in tx else 0.0

    total_debit = tx_debit["amount"].sum() if not tx_debit.empty else 0.0
    card_upi = tx_debit[tx_debit["channel"].isin(["CARD_POS","UPI"])]["amount"].sum() if not tx_debit.empty else 0.0
    digital_share = float(card_upi / (total_debit + 1e-9))

    return {
        "monthly_income_med": monthly_income_med,
        "income_regularity_cv": float(income_regularity_cv),
        "spend_volatility": float(spend_volatility),
        "ess_disc_ratio": float(ess_disc_ratio),
        "buffer_days": float(buffer_days),
        "emi_ontime_rate": float(ontime_rate),
        "low_balance_event_rate": float(low_balance_events),
        "digital_spend_share": float(digital_share),
    }

def features_from_sms(sms_dump: Dict[str, Any]) -> Dict[str, float]:
    msgs = sms_dump.get("messages", [])
    if not msgs:
        return {}
    df = pd.DataFrame(msgs)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    credit = df[df["type"]=="CREDIT_ALERT"]
    debit = df[df["type"]=="DEBIT_ALERT"]
    bill_due = df[df["type"].isin(["BILL_DUE","EMI_DUE"])]
    bill_paid = df[df["type"]=="BILL_PAID"] if "BILL_PAID" in df["type"].unique() else pd.DataFrame(columns=df.columns)

    credit_freq = len(credit)/90.0
    debit_freq = len(debit)/90.0
    due_freq = len(bill_due)/90.0
    paid_freq = len(bill_paid)/90.0 if not bill_paid.empty else 0.0

    income_median_sms = float(np.median(credit["amount"])) if not credit.empty else 0.0
    spend_median_sms = float(np.median(debit["amount"])) if not debit.empty else 0.0

    return {
        "sms_credit_freq": float(credit_freq),
        "sms_debit_freq": float(debit_freq),
        "sms_due_freq": float(due_freq),
        "sms_paid_freq": float(paid_freq),
        "sms_income_median": float(income_median_sms),
        "sms_spend_median": float(spend_median_sms),
    }

def features_from_telco(telecom_meta: Dict[str, Any]) -> Dict[str, float]:
    metrics = telecom_meta.get("metrics", {})
    if not metrics:
        return {}
    mean_recharge = metrics.get("avg_monthly_recharge", 0.0)
    var_recharge = metrics.get("recharge_variance", 0.0)
    reg_index = 0.0 if mean_recharge==0 else float(var_recharge/(mean_recharge+1e-9))
    return {
        "telco_regularity_index": reg_index,
        "telco_unique_contacts": float(metrics.get("unique_contacts_monthly", 0.0)),
        "telco_sim_age_months": float(metrics.get("sim_age_months", 0.0)),
        "telco_data_usage_gb": float(metrics.get("avg_data_usage_gb", 0.0)),
        "telco_home_stability": float(metrics.get("home_location_stability_index", 0.0)),
        "telco_avg_call_duration": float(metrics.get("avg_call_duration_sec", 0.0)),
    }

def assemble_features(payloads: Dict[str, Any]) -> Dict[str, float]:
    feats = {}
    if payloads.get("aa_payload"):
        feats.update(features_from_aa(payloads["aa_payload"]))
    if payloads.get("sms_dump"):
        feats.update(features_from_sms(payloads["sms_dump"]))
    if payloads.get("telecom_meta"):
        feats.update(features_from_telco(payloads["telecom_meta"]))
    return feats