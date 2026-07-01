import streamlit as st
import pandas as pd
import os
import time

# 1. Page Configuration & Styling
st.set_page_config(
    page_title="Clinical AI Triage Dashboard",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Clinical AI Triage Dashboard")
st.subheader("Real-time PACS Extraction & Streamlined Review Queue")

# 2. Path Resolution (Resolves from terminal's root context)
CSV_PATH = os.path.join(".", "data", "clinical_triage_report.csv")

# 3. Helper Function to Load Data safely
def load_triage_data(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        st.error(f"Error reading triage report: {e}")
        return pd.DataFrame()

# Load current state
df_report = load_triage_data(CSV_PATH)

# Sidebar Control Setup
st.sidebar.header("Pipeline Controls")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (5s)", value=True)

# 4. KPI Metrics Layer
if not df_report.empty:
    total_studies = len(df_report)
    
    # Force triage checks
    is_urgent = df_report['triage_status'].str.upper().str.contains("URGENT", na=False) if 'triage_status' in df_report.columns else False
    has_mismatch = df_report['validation_status'].str.upper().str.contains("MISMATCH", na=False) if 'validation_status' in df_report.columns else False
    
    anomalies = df_report[is_urgent | has_mismatch]
    critical_count = len(anomalies)
    audit_count = len(df_report[has_mismatch])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Studies Processed", value=total_studies)
    with col2:
        st.metric(label="🔴 Critical Alerts (Anomalies)", value=critical_count, delta=f"{critical_count} Urgent" if critical_count > 0 else "0 Urgent", delta_color="inverse")
    with col3:
        st.metric(label="⚠️ Validation Mismatches", value=audit_count, delta=f"{audit_count} Audit Required" if audit_count > 0 else "0 Pending", delta_color="inverse")

    # 5. High-Visibility Alert Banners
    if audit_count > 0:
        st.warning(f"🔒 **GROUND TRUTH AUDIT NOTICE:** Discrepancy detected via cross-reference validation.")
        with st.expander("🔍 Inspect Integrity Audit Trail (Patient 005)", expanded=True):
            st.dataframe(df_report[has_mismatch], use_container_width=True)
            
    if critical_count > 0:
        st.error(f"🚨 **CRITICAL NOTICE:** Urgent clinical findings require immediate radiologist validation.")
            
    # 6. Interactive Main Queue
    st.write("---")
    st.markdown("### 📋 Main Triage Queue")
    
    search_query = st.text_input("🔍 Search Queue by Patient ID, Modality, or Metadata:")
    if search_query:
        mask = df_report.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        filtered_df = df_report[mask]
    else:
        filtered_df = df_report

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

else:
    st.info("Waiting for data... Ensure `watch_pacs.py` or your simulator is pushing reports into `data/clinical_triage_report.csv`.")

# 7. Auto-Refresh Loop
if auto_refresh:
    time.sleep(5)
    st.rerun()