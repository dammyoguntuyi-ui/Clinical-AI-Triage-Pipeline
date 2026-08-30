"""
app.py - Enterprise Clinical AI Triage Dashboard & Multimodal Governance Console
Integrates live vitals telemetry streaming, pre-inference DICOM QA gating,
asymmetric clinical loss evaluation, persistent clinical claim actions, and multi-tier filtering.
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

if "last_poll_time" not in st.session_state:
    st.session_state.last_poll_time = time.time()

if "selected_action_patient" not in st.session_state:
    st.session_state.selected_action_patient = None

if "clinical_history" not in st.session_state:
    now = datetime.datetime.now(datetime.timezone.utc)
    st.session_state.clinical_history = pd.DataFrame(
        [
            {
                "Timestamp": (now - datetime.timedelta(seconds=i * 20)).isoformat(),
                "Patient ID": f"pat-{random.randint(1000, 9999)}",
                "SpO2 Vitals": f"{random.randint(88, 99)}% (Normal)" if i % 2 == 0 else f"{random.randint(78, 86)}% (Low)",
                "Heart Rate (BPM)": random.randint(65, 110),
                "Modality Attached": "None (Pending)",
                "Triage Urgency": "Emergency" if i % 3 == 0 else ("Urgent" if i % 2 == 0 else "Routine"),
                "Integration Status": "STREAMING VITALS",
                "Attending Status": "🔴 Unassigned",
            }
            for i in range(5)
        ]
    )

# --- SIMULATION HELPERS ---
def get_next_stream_packet() -> Dict[str, Any]:
    """Generates a single mock incoming bedside telemetry packet."""
    spo2_val = random.randint(76, 100)
    spo2_label = f"{spo2_val}% (Normal)" if spo2_val >= 92 else f"{spo2_val}% (Low)"
    patient_num = random.randint(1000, 9999)
    return {
        "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "Patient ID": f"pat-{patient_num}",
        "SpO2 Vitals": spo2_label,
        "Heart Rate (BPM)": random.randint(60, 125),
        "Modality Attached": "None (Pending)",
        "Triage Urgency": "Emergency" if spo2_val < 85 else ("Urgent" if spo2_val < 92 else "Routine"),
        "Integration Status": "STREAMING VITALS",
        "Attending Status": "🔴 Unassigned",
    }

# --- SIDEBAR: ORCHESTRATION ROUTER ---
st.sidebar.title("Orchestration Router")
st.sidebar.success("🟢 Aggregator Layer Online")

st.sidebar.info(
    "Ingesting aggregated clinical bundles. Bedside vitals streams are "
    "explicitly mapped alongside radiology imaging data vectors."
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

    current_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    reconciled_patient_id = process_result["payload"].get(
        "patient_id", latest_vitals["patient_id"]
    )
    modality_type = process_result["payload"].get(
        "modality", getattr(dcm, "Modality", "XR")
    )

    if process_result["outcome"] == "DISPATCHED":
        st.sidebar.success("✅ QA Passed: Ingestion & Dispatch Compliant")
        if not any(
            d["patient_id"] == process_result["payload"]["patient_id"]
            for d in st.session_state.dispatched_fhir_logs
        ):
            st.session_state.dispatched_fhir_logs.insert(0, process_result["payload"])

        modality_status = f"{modality_type} (SNR: {qa_res.snr_db:.1f} dB)"
        integration_status = "FHIR DISPATCHED"

    else:
        st.sidebar.error(
            f"❌ Rejected: {process_result['payload']['rejection_reasons']}"
        )
        if not any(
            q["patient_id"] == process_result["payload"]["patient_id"]
            for q in st.session_state.quarantined_studies_logs
        ):
            st.session_state.quarantined_studies_logs.insert(
                0, process_result["payload"]
            )

        modality_status = f"{modality_type} (Quarantined)"
        integration_status = "DEAD-LETTER QA FAIL"

    ledger = st.session_state.clinical_history
    if reconciled_patient_id in ledger["Patient ID"].values:
        idx = ledger.index[ledger["Patient ID"] == reconciled_patient_id].tolist()[0]
        ledger.at[idx, "Modality Attached"] = modality_status
        ledger.at[idx, "Integration Status"] = integration_status
        ledger.at[idx, "Timestamp"] = current_ts
    else:
        new_entry = {
            "Timestamp": current_ts,
            "Patient ID": reconciled_patient_id,
            "SpO2 Vitals": f"{latest_vitals['spo2']}%",
            "Heart Rate (BPM)": random.randint(70, 95),
            "Modality Attached": modality_status,
            "Triage Urgency": process_result["payload"].get("urgency_tier", "Urgent"),
            "Integration Status": integration_status,
            "Attending Status": "🔴 Unassigned",
        }
        st.session_state.clinical_history = pd.concat(
            [pd.DataFrame([new_entry]), ledger], ignore_index=True
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
        "y_true": [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0],
        "y_pred": [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1],
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

# --- LIVE TELEMETRY AUTO-POLL & WORKFLOW FRAGMENT ---
@st.fragment(run_every=10)
def render_live_clinical_console():
    """Polls incoming telemetry smoothly and maintains persistent UI selection state."""
    current_time = time.time()
    elapsed = current_time - st.session_state.last_poll_time

    # Advance queue incrementally (1 packet per cadence cycle)
    if elapsed >= 10.0:
        new_packet = get_next_stream_packet()
        new_row = pd.DataFrame([new_packet])
        st.session_state.clinical_history = pd.concat(
            [new_row, st.session_state.clinical_history], ignore_index=True
        ).head(30)
        st.session_state.last_poll_time = current_time

    latest = st.session_state.clinical_history.iloc[0]

    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Active Target Patient ID", str(latest["Patient ID"]))
    col_t2.metric("Current SpO2 Vitals", str(latest["SpO2 Vitals"]))
    col_t3.metric("Assigned Stream Triage", str(latest["Triage Urgency"]))

    st.markdown("---")
    st.subheader("📋 Aggregated Master Clinical Ledger")

    filter_col1, filter_col2 = st.columns([2, 2])
    with filter_col1:
        selected_urgency_filter = st.multiselect(
            "🔍 Filter Ledger by Urgency Tier",
            options=["Emergency", "Urgent", "Routine"],
            default=["Emergency", "Urgent", "Routine"],
            key="ledger_urgency_filter_key",
        )

    with filter_col2:
        selected_modality_filter = st.selectbox(
            "🩻 Filter by Imaging Status",
            options=["All Studies", "Attached Imaging Only", "Pending Imaging Only"],
            key="ledger_modality_filter_key",
        )

    df_display = st.session_state.clinical_history.copy()
    if selected_urgency_filter:
        df_display = df_display[df_display["Triage Urgency"].isin(selected_urgency_filter)]

    if selected_modality_filter == "Attached Imaging Only":
        df_display = df_display[df_display["Modality Attached"] != "None (Pending)"]
    elif selected_modality_filter == "Pending Imaging Only":
        df_display = df_display[df_display["Modality Attached"] == "None (Pending)"]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # --- CLINICAL ACTION & ATTENDING MD CONSOLE ---
    with st.expander("🩺 Clinical Action & Attending MD Console", expanded=True):
        act_col1, act_col2, act_col3 = st.columns([2, 2, 1])

        patient_options = st.session_state.clinical_history["Patient ID"].tolist()

        if st.session_state.selected_action_patient not in patient_options:
            st.session_state.selected_action_patient = (
                patient_options[0] if patient_options else None
            )

        current_idx = 0
        if st.session_state.selected_action_patient in patient_options:
            current_idx = patient_options.index(st.session_state.selected_action_patient)

        with act_col1:
            chosen_patient = st.selectbox(
                "Select Patient to Action",
                options=patient_options,
                index=current_idx,
                key="ui_action_patient_selector",
            )
            st.session_state.selected_action_patient = chosen_patient

        with act_col2:
            target_status = st.selectbox(
                "Update Review Status",
                options=[
                    "🔴 Unassigned",
                    "🟡 Under MD Review",
                    "🟢 Triaged & Signed Off",
                ],
                key="ui_action_status_selector",
            )

        with act_col3:
            st.write("")
            st.write("")
            if st.button("Apply Status", key="btn_apply_clinical_status"):
                if chosen_patient in st.session_state.clinical_history["Patient ID"].values:
                    p_idx = st.session_state.clinical_history.index[
                        st.session_state.clinical_history["Patient ID"] == chosen_patient
                    ].tolist()[0]
                    st.session_state.clinical_history.at[
                        p_idx, "Attending Status"
                    ] = target_status
                    st.success(f"Updated {chosen_patient} ➔ {target_status}")

render_live_clinical_console()

# --- MAIN VIEW: ENTERPRISE AUDIT & DISPATCH CONSOLE ---
st.markdown("---")
st.subheader("📄 Enterprise Triage & Clinical Governance Logs")
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
        st.dataframe(df_dispatched, use_container_width=True, hide_index=True)

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
        st.dataframe(df_quarantined, use_container_width=True, hide_index=True)
    else:
        st.success(
            "Dead-letter Queue clear: No non-compliant or corrupted acquisitions detected."
        )