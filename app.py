import os
import sys
import io
import base64
import pydicom
import numpy as np
import pandas as pd
import streamlit as st
import socket

from qa_evaluator import ImageQualityEvaluator, ClinicalMetricsAuditor

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.mock_streamer import get_next_stream_packet
from scripts.ai_triage import evaluate_imaging_finding


# =========================================================
# INFRASTRUCTURE NETWORK RESILIENCY CHECK
# =========================================================
def check_streamer_network_resilience(host="clinical_mock_streamer", port=5000):
    """
    Validates internal container network bridge connection before pulling data stream.
    Prevents port binding timeouts and unhandled infrastructure crashes.
    """
    try:
        host_ip = socket.gethostbyname(host)
        with socket.create_connection((host_ip, port), timeout=2):
            return True
    except (socket.gaierror, socket.timeout, ConnectionRefusedError):
        return False


# --- PAGE SETUP ---
st.set_page_config(
    page_title="Unified Multi-Modality AI Triage",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🫁 Enterprise Multi-Modality AI Clinical Triage Dashboard")
st.subheader("Aggregated Data Stream: Correlating Live FHIR Telemetry & DICOM Imaging Analytics")
st.markdown("---")


# --- UNIFIED PARSING COMPONENT ---
def process_unified_clinical_packet(data):
    """Processes aggregated patient data bundles seamlessly with detailed imaging tracking."""
    try:
        vitals = data["vitals_telemetry"]
        b64_imaging_data = data.get("radiology_exam_b64")

        # Handle binary pydicom parsing layer safely if present
        if b64_imaging_data:
            try:
                dicom_bytes = base64.b64decode(b64_imaging_data)
                dicom_buffer = io.BytesIO(dicom_bytes)
                dicom_obj = pydicom.dcmread(dicom_buffer)

                # Extract real attributes from DICOM object layout
                modality = dicom_obj.get("Modality", "UNKNOWN")
                patient_id = dicom_obj.get("PatientID", "UNKNOWN-ID")
                accession = dicom_obj.get("AccessionNumber", "N/A")

                rows = dicom_obj.get("Rows", 0)
                cols = dicom_obj.get("Columns", 0)
                resolution_str = f"{rows}x{cols}" if rows and cols else "Unknown Matrix"

                has_imaging = "Yes"
                modality_info = f"{modality} ({resolution_str})"

                # Dynamic inference execution from local AI evaluation module
                findings = evaluate_imaging_finding(dicom_obj)
                raw_dump = f"Modality: {modality} | Accession: {accession} | SOP_UID: {dicom_obj.SOPInstanceUID}"
            except Exception as e:
                has_imaging = "Corrupted Payload"
                modality_info = "Parsing Failure"
                findings = "AI Inference Failure"
                raw_dump = f"Parsing Error: {str(e)}"
        else:
            has_imaging = "No"
            modality_info = "None Ordered"
            findings = "N/A"
            raw_dump = "N/A"

        return {
            "Timestamp": data.get("timestamp"),
            "Patient ID": data.get("patient_id"),
            "SpO2 Vitals": f"{vitals['value']}{vitals['unit']} ({vitals['status']})",
            "Has Imaging": has_imaging,
            "Imaging Modality": modality_info,
            "AI Radiology Findings": findings,
            "Triage Level": data.get("triage_status"),
            "Raw Image Dump": raw_dump,
            "Numeric SpO2": int(vitals["value"]),
        }
    except KeyError as e:
        st.error(f"Error parsing aggregated data schema: {e}")
        return None


# --- STATE MANAGEMENT ---
if "clinical_history" not in st.session_state:
    st.session_state.clinical_history = pd.DataFrame(
        columns=[
            "Timestamp",
            "Patient ID",
            "SpO2 Vitals",
            "Has Imaging",
            "Imaging Modality",
            "AI Radiology Findings",
            "Triage Level",
            "Raw Image Dump",
            "Numeric SpO2",
        ]
    )


# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header("Orchestration Router")
st.sidebar.success("🟢 Aggregator Layer Online")
st.sidebar.info("Ingesting aggregated clinical bundles. Bedside vitals streams are now explicitly mapped alongside radiology imaging data vectors.")

if st.sidebar.button("🗑️ Clear Local Log Cache", use_container_width=True):
    st.session_state.clinical_history = pd.DataFrame(
        columns=[
            "Timestamp",
            "Patient ID",
            "SpO2 Vitals",
            "Has Imaging",
            "Imaging Modality",
            "AI Radiology Findings",
            "Triage Level",
            "Raw Image Dump",
            "Numeric SpO2",
        ]
    )
    st.rerun()

# --- PRE-INFERENCE QA & ANOMALY DETECTION ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Pre-Inference DICOM QA Gate")
uploaded_dcm = st.sidebar.file_uploader("Audit DICOM Acquisition", type=["dcm"], key="qa_dcm_uploader")

if uploaded_dcm:
    dcm = pydicom.dcmread(uploaded_dcm)
    evaluator = ImageQualityEvaluator()
    qa_result = evaluator.evaluate_dicom(dcm)

    c1, c2 = st.sidebar.columns(2)
    c1.metric("SNR (dB)", f"{qa_result.snr_db} dB", delta="Optimal" if qa_result.snr_db >= 12 else "Low")
    c2.metric("CNR", f"{qa_result.cnr}")

    if qa_result.is_valid:
        st.sidebar.success("✅ QA Passed: Ingestion Compliant")
    else:
        st.sidebar.error(f"❌ Rejected: {', '.join(qa_result.rejection_reasons)}")

# --- CLINICAL SAFETY & LOSS CALIBRATION ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Clinical Safety Metric (β=2)")
tier = st.sidebar.selectbox("Auditing Urgency Tier", ["Emergency", "Urgent", "Routine"], key="metrics_tier_select")

y_true_mock = [1, 1, 0, 1, 0, 0, 1, 0, 1, 0]
y_pred_mock = [1, 1, 0, 0, 0, 0, 1, 0, 1, 1]

metrics = ClinicalMetricsAuditor.calculate_metrics(y_true=y_true_mock, y_pred=y_pred_mock, tier=tier, beta=2.0)

mc1, mc2 = st.sidebar.columns(2)
mc1.metric("Sensitivity", f"{metrics.sensitivity * 100:.1f}%")
mc2.metric("F2 Safety", f"{metrics.f2_score:.3f}")
st.sidebar.caption(f"Alarm Fatigue: {metrics.alarm_fatigue_rate * 100:.1f}% (FP Rate)")


# --- AUTOMATED MIXED STREAM ENGINE FRAGMENT ---
@st.fragment(run_every=20)
def automated_clinical_stream():
    """Polls aggregated clinical bundles every 20 seconds hands-free."""
    if check_streamer_network_resilience():
        raw_packet = get_next_stream_packet()
        parsed_frame = process_unified_clinical_packet(raw_packet)

        if parsed_frame:
            new_row = pd.DataFrame([parsed_frame])
            st.session_state.clinical_history = pd.concat(
                [new_row, st.session_state.clinical_history], ignore_index=True
            )

        if not st.session_state.clinical_history.empty:
            latest_entry = st.session_state.clinical_history.iloc[0]

            # Display Top Panel Metrics
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(label="Active Target Patient ID", value=latest_entry["Patient ID"])
            with c2:
                st.metric(label="Current Bedside Vitals Stream", value=latest_entry["SpO2 Vitals"])
            with c3:
                is_critical = latest_entry["Triage Level"] == "CRITICAL"
                status_symbol = "💥 HIGH PRIORITY" if is_critical else "🟢 Stable"
                st.metric(
                    label="Encounter Priority State",
                    value=latest_entry["Triage Level"],
                    delta=status_symbol,
                    delta_color="inverse" if is_critical else "normal",
                )

            st.markdown("---")
            left_layout, right_layout = st.columns([4, 3])

            with left_layout:
                st.markdown("### 📋 Aggregated Master Clinical Ledger")
                st.markdown("*Hide technical plotting columns from display grid*")
                display_df = st.session_state.clinical_history.drop(
                    columns=["Raw Image Dump", "Numeric SpO2"]
                )
                st.dataframe(display_df, use_container_width=True)

                st.markdown("### 📈 Continuous Patient Vitals Trend (All Ingested Cases)")
                chart_data = st.session_state.clinical_history.iloc[::-1].reset_index()
                st.line_chart(data=chart_data, x="Timestamp", y="Numeric SpO2")

            with right_layout:
                st.markdown("### 🔬 Diagnostics Inspection Frame")
                if not st.session_state.clinical_history.empty:
                    if latest_entry["Has Imaging"] == "Yes":
                        modality_label = latest_entry["Imaging Modality"].split(" ")[0].replace("(", "").replace(")", "")
                        st.info(f"**RadAI Diagnostics Output:** {latest_entry['AI Radiology Findings']}")

                        is_pathology_detected = any(
                            keyword in latest_entry["AI Radiology Findings"]
                            for keyword in ["Hemorrhage", "Mass", "Fracture", "Abnormality"]
                        )

                        if is_pathology_detected:
                            st.error(f"🚨 PATHOLOGY ALARM: Critical emergency indicators identified within the live {modality_label} capture.")
                            st.image(
                                f"https://placehold.co/400x300/4a0000/ffffff?text=CRITICAL+({modality_label})",
                                caption=f"PACS Frame Instance - Diagnostic {modality_label} Series",
                                use_container_width=True,
                            )
                        else:
                            st.success(f"🟢 RADIOLOGY CLEAR: Routine anatomical parameters mapped on {modality_label}.")
                            st.image(
                                f"https://placehold.co/400x300/004a11/ffffff?text=ROUTINE+({modality_label})",
                                caption=f"PACS Frame Instance - Diagnostic {modality_label} Series",
                                use_container_width=True,
                            )
                    else:
                        st.warning("⚠️ No diagnostic radiology exams were scheduled or ordered for this encounter window. Bedside monitoring remains ongoing.")
        else:
            st.info("Awaiting the initial aggregated multi-modality pipeline packet...")
    else:
        # Graceful UI degradation fallback if container goes unhealthy
        st.error("🚨 Infrastructure Alert: Connection to Modality Telemetry Engine lost")
        st.warning(
            "The background streaming engine ('mock_streamer.py') is currently unreachable. "
            "The system network bridge is attempting automated self-healing. Retrying connection..."
        )
        st.info("Awaiting structural metadata streams to resume triage visualization.")


# --- RUN PIPELINE ---
st.markdown("### 🌐 Live Stream Processing Pipeline")
automated_clinical_stream()