"""
app.py - Enterprise Clinical AI Triage Dashboard & Multimodal Governance Console
Integrates live vitals telemetry streaming, pre-inference DICOM QA gating,
asymmetric clinical loss evaluation, and downstream FHIR R4 dispatching.
"""

import datetime
import random
import time
from typing import Dict, Any

import pandas as pd
import pydicom
import streamlit as st

from enterprise_engine import EnterpriseHospitalEngine
from qa_evaluator import ClinicalMetricsAuditor

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Enterprise Clinical AI Triage",
    page_icon="🫁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SESSION STATE INITIALIZATION ---
if "enterprise_engine" not in st.session_state:
    st.session_state.enterprise_engine = EnterpriseHospitalEngine()

if "dispatched_fhir_logs" not in st.session_state:
    st.session_state.dispatched_fhir_logs = []

if "quarantined_studies_logs" not in st.session_state:
    st.session_state.quarantined_studies_logs = []

if "clinical_history" not in st.session_state:
    # Seed initial mock data history
    now = datetime.datetime.now(datetime.timezone.utc)
    st.session_state.clinical_history = pd.DataFrame(
        [
            {
                "Timestamp": (now - datetime.timedelta(seconds=i * 20)).isoformat(),
                "Patient ID": f"pat-{random.randint(1000, 9999)}",
                "SpO2 Vitals": f"{random.randint(88, 99)}% (Normal)" if i % 2 == 0 else f"{random.randint(78, 86)}% (Low)",
                "Heart Rate (BPM)": random.randint(65, 110),
                "Triage Urgency": "Emergency" if i % 3 == 0 else ("Urgent" if i % 2 == 0 else "Routine"),
            }
            for i in range(5)
        ]
    )


# --- SIMULATION HELPERS ---
def get_next_stream_packet() -> Dict[str, Any]:
    """Generates a mock incoming bedside telemetry packet."""
    spo2_val = random.randint(76, 100)
    spo2_label = f"{spo2_val}% (Normal)" if spo2_val >= 92 else f"{spo2_val}% (Low)"
    patient_num = random.randint(1000, 9999)
    return {
        "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "Patient ID": f"pat-{patient_num}",
        "SpO2 Vitals": spo2_label,
        "Heart Rate (BPM)": random.randint(60, 125),
        "Triage Urgency": "Emergency" if spo2_val < 85 else ("Urgent" if spo2_val < 92 else "Routine"),
    }


# --- SIDEBAR: ORCHESTRATION ROUTER ---
st.sidebar.title("Orchestration Router")
st.sidebar.success("🌐 Aggregator Layer Online")

st.sidebar.info(
    "Ingesting aggregated clinical bundles. Bedside vitals streams are explicitly mapped "
    "alongside radiology imaging data vectors."
)

if st.sidebar.button("🗑️ Clear Local Log Cache"):
    st.session_state.dispatched_fhir_logs = []
    st.session_state.quarantined_studies_logs = []
    st.rerun()


# --- SIDEBAR: PRE-INFERENCE QA & ANOMALY DETECTION ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Pre-Inference DICOM QA Gate")
uploaded_dcm = st.sidebar.file_uploader(
    "Audit DICOM Acquisition", type=["dcm"], key="qa_dcm_uploader"
)

if uploaded_dcm:
    dcm = pydicom.dcmread(uploaded_dcm)

    # Extract latest live vitals from session state if present
    latest_vitals = {"spo2": 97.0, "patient_id": getattr(dcm, "PatientID", "pat-7577")}
    if not st.session_state.clinical_history.empty:
        latest_row = st.session_state.clinical_history.iloc[0]
        raw_spo2 = str(latest_row.get("SpO2 Vitals", "97")).split("%")[0]
        try:
            latest_vitals["spo2"] = float(raw_spo2)
        except ValueError:
            latest_vitals["spo2"] = 97.0
        latest_vitals["patient_id"] = str(
            latest_row.get("Patient ID", latest_vitals["patient_id"])
        )

    process_result = st.session_state.enterprise_engine.process_clinical_study(
        dcm, latest_vitals
    )
    qa_res = process_result["qa_result"]

    c1, c2 = st.sidebar.columns(2)
    c1.metric(
        "SNR (dB)",
        f"{qa_res.snr_db} dB",
        delta="Optimal" if qa_res.snr_db >= 8.0 else "Low",
    )
    c2.metric("CNR", f"{qa_res.cnr}")

    if process_result["outcome"] == "DISPATCHED":
        st.sidebar.success("✅ QA Passed: Ingestion & Dispatch Compliant")
        if not any(
            d["patient_id"] == process_result["payload"]["patient_id"]
            for d in st.session_state.dispatched_fhir_logs
        ):
            st.session_state.dispatched_fhir_logs.insert(0, process_result["payload"])
    else:
        st.sidebar.error(f"❌ Rejected: {process_result['payload']['rejection_reasons']}")
        if not any(
            q["patient_id"] == process_result["payload"]["patient_id"]
            for q in st.session_state.quarantined_studies_logs
        ):
            st.session_state.quarantined_studies_logs.insert(
                0, process_result["payload"]
            )


# --- SIDEBAR: CLINICAL SAFETY & LOSS CALIBRATION ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Clinical Safety Metric (β=2)")
tier = st.sidebar.radio(
    "Auditing Urgency Tier",
    ["Emergency", "Urgent", "Routine"],
    horizontal=True,
    key="metrics_tier_select",
)

tier_benchmarks = {
    "Emergency": {
        "y_true": [1, 1, 1, 1, 0, 0, 1, 0, 1, 0],
        "y_pred": [1, 1, 1, 0, 0, 0, 1, 0, 1, 1],
        "beta": 2.0,
    },
    "Urgent": {
        "y_true": [1, 1, 0, 0, 1, 0, 1, 0, 0, 1],
        "y_pred": [1, 1, 0, 0, 1, 0, 0, 0, 0, 1],
        "beta": 1.5,
    },
    "Routine": {
        "y_true": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "y_pred": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "beta": 1.0,
    },
}

cohort = tier_benchmarks[tier]
metrics = ClinicalMetricsAuditor.calculate_metrics(
    cohort["y_true"], cohort["y_pred"], tier=tier, beta=cohort["beta"]
)

mc1, mc2 = st.sidebar.columns(2)
mc1.metric("Sensitivity", f"{metrics.sensitivity * 100:.1f}%")
mc2.metric(
    "F2 Safety" if tier == "Emergency" else f"F{cohort['beta']} Score",
    f"{metrics.f2_score:.3f}",
)
st.sidebar.caption(f"Alarm Fatigue: {metrics.alarm_fatigue_rate * 100:.1f}% (FP Rate)")


# --- MAIN VIEW: ENTERPRISE TELEMETRY STREAM & AUDIT DASHBOARD ---
st.title("🫁 Enterprise Clinical AI Triage Dashboard")
st.markdown("#### Aggregated Data Streams & Multimodal Governance Engine")

# --- LIVE TELEMETRY FRAGMENT (AUTO-POLL EVERY 20s) ---
@st.fragment(run_every=20)
def automated_clinical_stream():
    """Polls aggregated clinical bundles every 20 seconds hands-free."""
    new_packet = get_next_stream_packet()
    new_row = pd.DataFrame([new_packet])
    st.session_state.clinical_history = pd.concat(
        [new_row, st.session_state.clinical_history], ignore_index=True
    ).head(30)

    latest = st.session_state.clinical_history.iloc[0]

    # Active Target Vitals Banner
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Active Target Patient ID", str(latest["Patient ID"]))
    col_t2.metric("Current SpO2 Vitals", str(latest["SpO2 Vitals"]))
    col_t3.metric("Assigned Stream Triage", str(latest["Triage Urgency"]))

    st.markdown("---")
    st.subheader("📋 Aggregated Master Clinical Ledger")
    st.dataframe(st.session_state.clinical_history, use_container_width=True)


automated_clinical_stream()

# --- MAIN VIEW: ENTERPRISE AUDIT & DISPATCH CONSOLE ---
st.markdown("---")
st.subheader("🏥 Enterprise Triage & Clinical Governance Logs")
tab1, tab2 = st.tabs(
    ["🚀 Dispatched FHIR R4 DiagnosticReports", "⚠️ Quarantined Dead-Letter Studies"]
)

with tab1:
    if st.session_state.dispatched_fhir_logs:
        df_dispatched = pd.DataFrame(
            [
                {
                    "Timestamp": l["timestamp"],
                    "Patient ID": l["patient_id"],
                    "Modality": l["modality"],
                    "Urgency Tier": l["urgency_tier"],
                    "SNR (dB)": l["snr_db"],
                    "CNR": l["cnr"],
                    "Status": l["status"],
                }
                for l in st.session_state.dispatched_fhir_logs
            ]
        )
        st.dataframe(df_dispatched, use_container_width=True)

        with st.expander("🔍 Inspect Latest Dispatched FHIR R4 JSON Bundle"):
            st.json(st.session_state.dispatched_fhir_logs[0]["fhir_payload"])
    else:
        st.info(
            "No compliant studies dispatched yet. Upload a valid DICOM acquisition in the sidebar to trigger triage."
        )

with tab2:
    if st.session_state.quarantined_studies_logs:
        df_quarantined = pd.DataFrame(
            [
                {
                    "Timestamp": q["timestamp"],
                    "Patient ID": q["patient_id"],
                    "Modality": q["modality"],
                    "Rejection Reasons": q["rejection_reasons"],
                    "Error Code": q["hl7_error_code"],
                    "Status": q["status"],
                }
                for q in st.session_state.quarantined_studies_logs
            ]
        )
        st.dataframe(df_quarantined, use_container_width=True)
    else:
        st.success(
            "Dead-Letter Queue clear: No non-compliant or corrupted acquisitions detected."
        )