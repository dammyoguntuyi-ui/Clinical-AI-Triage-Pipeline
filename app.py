import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st
from scripts.mock_streamer import get_next_stream_packet

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Unified Multi-Modality AI Triage",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏥 Enterprise Multi-Modality AI Clinical Triage Dashboard")
st.subheader("Aggregated Data Stream: Correlating Live FHIR Telemetry & DICOM Imaging Analytics")
st.markdown("---")


# --- UNIFIED PARSING COMPONENT ---
def process_unified_clinical_packet(data):
    """Processes aggregated patient data bundles seamlessly with detailed imaging tracking."""
    try:
        vitals = data["vitals_telemetry"]
        imaging = data["radiology_exam"]

        # 🛠️ ENHANCED: Combine Modality and Body Site for full visibility
        has_imaging = "Yes" if imaging else "No"
        if imaging:
            modality_info = f"{imaging['modality']} ({imaging['bodySite']})"  # e.g., "CT (Head)", "MR (Spine)"
            findings = imaging["primary_finding"]
            raw_dump = imaging["mock_image_type"]
        else:
            modality_info = "None Ordered"
            findings = "N/A"
            raw_dump = "N/A"

        return {
            "Timestamp": data.get("timestamp"),
            "Patient ID": data.get("patient_id"),
            "SpO2 Vitals": f"{vitals['value']}{vitals['unit']} ({vitals['status']})",
            "Has Imaging": has_imaging,
            "Imaging Modality": modality_info,  # Displays detailed text in the table
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
st.sidebar.info(
    "Ingesting aggregated clinical bundles. Bedside vitals streams are now explicitly mapped alongside radiology imaging data vectors."
)

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


# --- AUTOMATED MIXED STREAM ENGINE FRAGMENT ---
@st.fragment(run_every=20)
def automated_clinical_stream():
    """Polls aggregated clinical bundles every 20 seconds hands-free."""
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
            status_symbol = "🚨 HIGH PRIORITY" if is_critical else "✅ Stable"
            st.metric(
                label="Encounter Priority State",
                value=status_symbol,
                delta=latest_entry["Triage Level"],
                delta_color="inverse" if is_critical else "normal",
            )

        st.markdown("---")
        left_layout, right_layout = st.columns([4, 3])

        with left_layout:
            st.markdown("### 📋 Aggregated Master Clinical Ledger")
            # Hide technical plotting columns from display grid
            display_df = st.session_state.clinical_history.drop(columns=["Raw Image Dump", "Numeric SpO2"])
            st.dataframe(display_df, use_container_width=True)

            st.markdown("### 📈 Continuous Patient Vitals Trend (All Ingested Cases)")
            chart_data = st.session_state.clinical_history.iloc[::-1].reset_index()
            st.line_chart(data=chart_data, x="Timestamp", y="Numeric SpO2")

        with right_layout:
            st.markdown("### 🔍 Diagnostics Inspection Frame")

            if latest_entry["Has Imaging"] == "Yes":
                st.info(f"🤖 **RadAI Diagnostics Output:** {latest_entry['AI Radiology Findings']}")
                modality_label = latest_entry["Imaging Modality"].split(" ")[-1].replace("(", "").replace(")", "")

                if "CRITICAL" in latest_entry["Triage Level"]:
                    st.error(f"⚠️ PATHOLOGY ALARM: Critical emergency indicators identified within the live {modality_label} capture.")
                    st.image(
                        f"https://placehold.co/400x300/4a0000/ffffff?text=CRITICAL+{modality_label}",
                        caption=f"PACS Frame Instance - Diagnostic {modality_label} Series",
                        use_container_width=True
                    )
                else:
                    st.success(f"🟢 RADIOLOGY CLEAR: Routine anatomical parameters mapped on {modality_label}.")
                    st.image(
                        f"https://placehold.co/400x300/004a11/ffffff?text=ROUTINE+{modality_label}",
                        caption=f"PACS Frame Instance - Diagnostic {modality_label} Series",
                        use_container_width=True
                    )
            else:
                st.warning("ℹ️ No diagnostic radiology exams were scheduled or ordered for this encounter window. Bedside monitoring remains active.")

    else:
        st.info("Awaiting the initial aggregated multi-modality pipeline packet...")


# --- RUN PIPELINE ---
st.markdown("### 🕒 Live Stream Processing Pipeline")
automated_clinical_stream()