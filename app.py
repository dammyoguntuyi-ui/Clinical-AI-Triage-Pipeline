import os
import sys

# Force Python to look inside the root directory for relative folder paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st
from scripts.mock_streamer import get_next_stream_packet

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Clinical Data Pipeline Ingestion",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏥 Clinical Modality Ingestion Dashboard")
st.subheader("Real-Time HL7/FHIR Data Stream Integration")
st.markdown("---")


# --- DATA PARSING COMPONENT ---
def process_incoming_fhir_data(data):
    """Parses incoming standard healthcare strings into clean dashboard metrics."""
    try:
        if data.get("resourceType") == "Observation":
            return {
                "Observation ID": data.get("id"),
                "Patient ID": data["subject"]["reference"].split("/")[-1],
                "Modality Metric": data["code"]["coding"][0]["display"],
                "Value": data["valueQuantity"]["value"],
                "Unit": data["valueQuantity"]["unit"],
                "Status": data["interpretation"][0]["coding"][0]["display"],
                "Timestamp": data.get("effectiveDateTime"),
            }
    except KeyError as e:
        st.error(f"Structural FHIR mismatch parsing payload on key: {e}")
    return None


# --- STATE MANAGEMENT (SESSION STORE) ---
if "clinical_history" not in st.session_state:
    st.session_state.clinical_history = pd.DataFrame(
        columns=[
            "Timestamp",
            "Patient ID",
            "Modality Metric",
            "Value",
            "Unit",
            "Status",
        ]
    )


# --- SIDEBAR INTERACTION CONTROL ---
st.sidebar.header("Pipeline Stream Engine")
st.sidebar.success("🟢 Live Ambient Monitor Active")
st.sidebar.info(
    "The central interface is now utilizing an automated polling fragment loop. It auto-fetches structured FHIR objects from mock_streamer.py every 20 seconds hands-free."
)

# Clear dashboard data cache button
if st.sidebar.button("🗑️ Clear Local Log Cache", use_container_width=True):
    st.session_state.clinical_history = pd.DataFrame(
        columns=[
            "Timestamp",
            "Patient ID",
            "Modality Metric",
            "Value",
            "Unit",
            "Status",
        ]
    )
    st.rerun()


# --- AUTOMATED LIVE MONITOR FRAGMENT (THE 20S ENGINE) ---
@st.fragment(run_every=20)
def automated_clinical_stream():
    """Automatically polls a new FHIR frame every 20 seconds hands-free."""
    raw_packet = get_next_stream_packet()
    parsed_clinical_frame = process_incoming_fhir_data(raw_packet)

    if parsed_clinical_frame:
        new_row = pd.DataFrame([parsed_clinical_frame])
        display_row = new_row.drop(columns=["Observation ID"])
        st.session_state.clinical_history = pd.concat(
            [display_row, st.session_state.clinical_history], ignore_index=True
        )

    # --- FRONTEND PRESENTATION METRICS RENDER ---
    if not st.session_state.clinical_history.empty:
        latest_entry = st.session_state.clinical_history.iloc[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Active Ingested Patient ID", value=latest_entry["Patient ID"])
        with col2:
            is_critical = latest_entry["Status"] == "Low"
            delta_color_config = "inverse" if is_critical else "normal"
            status_symbol = "⚠️ Critical Alert" if is_critical else "✅ Stable"
            st.metric(
                label=f"🫁 Current {latest_entry['Modality Metric']}",
                value=f"{latest_entry['Value']} {latest_entry['Unit']}",
                delta=f"{status_symbol} ({latest_entry['Status']})",
                delta_color=delta_color_config,
            )
        with col3:
            st.metric(label="Ingestion Protocol Framework", value="HL7/FHIR v4.0.1")

        # 👇 MOVED INSIDE THE FRAGMENT SO THEY UPDATE AUTOMATICALLY 👇
        st.markdown("---")
        st.markdown("### 📋 Historic Modality Log Stream")
        st.dataframe(st.session_state.clinical_history, use_container_width=True)

        st.markdown("### 📈 Live Oxygen Saturation Value Vector Track")
        chart_data = st.session_state.clinical_history.iloc[::-1].reset_index()
        st.line_chart(data=chart_data, x="Timestamp", y="Value")
        
    else:
        st.info("Waiting for the first ambient clinical streaming data packet...")

# --- EXECUTE LIVE MONITORING STREAM ---
st.markdown("### 🕒 Live Modality Stream Tracking Feed")
automated_clinical_stream()

st.markdown("---")

# --- HISTORICAL LEDGER & CHARTS (Updates when Fragment triggers rerun) ---
if not st.session_state.clinical_history.empty:
    # --- HISTORICAL LEDGER DATA TABLE ---
    st.markdown("### 📋 Historic Modality Log Stream")
    st.dataframe(st.session_state.clinical_history, use_container_width=True)

    # --- DATA PROFILE LINE CHART TRACE ---
    st.markdown("### 📈 Live Oxygen Saturation Value Vector Track")
    # Invert history view for line charts so chronologically earlier data graphs left to right
    chart_data = st.session_state.clinical_history.iloc[::-1].reset_index()
    st.line_chart(data=chart_data, x="Timestamp", y="Value")