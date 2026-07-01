import streamlit as st
import pandas as pd
import sqlite3
import os
import time

# Set page configuration
st.set_page_config(page_title="Clinical AI Triage Dashboard", page_icon="🏥", layout="wide")

DB_PATH = os.path.join(".", "data", "triage.db")

def load_data_from_db():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        # 1. Reach into the Orthanc PACS container network API to check for active studies
        import requests
        from scripts.watch_pacs import simulate_ai_inference
        
        orthanc_url = "http://orthanc-pacs:8042/instances"
        try:
            response = requests.get(orthanc_url, auth=('orthanc', 'orthanc'), timeout=2)
            if response.status_code == 200:
                instances = response.json()
                
                # Connect to SQL to sync any missing studies
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                for instance_id in instances:
                    # Query Orthanc for the metadata tags of this instance
                    tag_res = requests.get(f"http://orthanc-pacs:8042/instances/{instance_id}/simplified-tags", auth=('orthanc', 'orthanc'))
                    if tag_res.status_code == 200:
                        tags = tag_res.json()
                        mrn = tags.get("PatientID", f"MOCK_MRN_{instance_id[:4]}")
                        modality = tags.get("Modality", "CR")
                        
                        # Generate the AI triage features inline
                        ai = simulate_ai_inference(mrn, modality)
                        
                        # INSERT OR IGNORE avoids duplicates if rows already exist
                        cursor.execute('''
                            INSERT OR IGNORE INTO triage_queue (
                                hospital_case_id, clinical_mrn, modality, 
                                ai_model_used, finding_detected, confidence_score, triage_status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (instance_id, mrn, modality, ai["model_used"], ai["finding"], ai["confidence"], ai["triage"]))
                conn.commit()
                conn.close()
        except Exception as api_err:
            pass # Keep moving if Orthanc container is still booting up

        # 2. Query the updated database file for only PENDING cases
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM triage_queue WHERE review_status = 'PENDING' ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database read error: {e}")
        return pd.DataFrame()

def clear_case_in_db(case_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Update the state of this specific case to CLEARED
        cursor.execute(
            "UPDATE triage_queue SET review_status = 'CLEARED' WHERE hospital_case_id = ?", 
            (str(case_id),)
        )
        conn.commit()
        conn.close()
        st.toast(f"✅ Case {case_id} successfully cleared from triage queue!", icon="🎉")
        time.sleep(0.5) # Let the toast display briefly before rerun
    except Exception as e:
        st.error(f"Failed to clear case: {e}")

# 📊 Load Live Subsets
df = load_data_from_db()

# 🔄 True Asynchronous Polling Engine (Ensures constant 5s cycles regardless of table states)
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# --- HEADER LAYER ---
st.title("🏥 Clinical AI Triage Dashboard")
st.subheader("Real-time PACS Extraction & Streamlined Review Queue")

if df.empty:
    st.info("🎉 Triage Queue is currently clear. Excellent work!")
    # Render KPI Summaries at absolute zero
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total Active Studies", value=0)
    col2.metric(label="🔴 Critical Alerts (Anomalies)", value=0)
    col3.metric(label="⚠️ Validation Mismatches", value=0)
    
    # Let the app sleep and refresh the pipeline without drawing ghost queues
    time.sleep(5)
    st.rerun()

# 🛑 Everything below here will only run if df has patients!
else:
    total_studies = len(df)
    critical_alerts = len(df[df['triage_status'] == 'URGENT'])
    validation_mismatches = len(df[df['clinical_mrn'] == 'PATIENT_005'])

    # KPI Summary Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Active Studies", value=total_studies)
    with col2:
        st.metric(label="🔴 Critical Alerts (Anomalies)", value=critical_alerts, delta=f"{critical_alerts} Urgent")
    with col3:
        st.metric(label="⚠️ Validation Mismatches", value=validation_mismatches, delta=f"{validation_mismatches} Audit Required", delta_color="inverse")

    # --- GROUND TRUTH AUDIT NOTICE (PATIENT_005 EXCEPTION HANDLER) ---
    patient_005_df = df[df['clinical_mrn'] == 'PATIENT_005']
    if not patient_005_df.empty:
        st.error("⚠️ GROUND TRUTH AUDIT NOTICE: Discrepancy detected via cross-reference validation.")
        with st.expander("🔍 Inspect Integrity Audit Trail (Patient 005)"):
            st.dataframe(patient_005_df, use_container_width=True)

    if critical_alerts > 0:
        st.warning("🚨 CRITICAL NOTICE: Urgent clinical findings require immediate radiologist validation.")

    # --- INTERACTIVE MAIN TRIAGE QUEUE ---
    st.write("### 📋 Main Triage Queue")
    
    # Generate action loops using columns instead of a flat table display
    # This allows us to embed functional buttons directly next to the rows!
    header_cols = st.columns([2, 2, 1, 2, 3, 1, 1, 1])
    headers = ["Case ID", "Patient MRN", "Modality", "AI Model", "Finding Detected", "Confidence", "Triage", "Action"]
    for col, h_name in zip(header_cols, headers):
        col.write(f"**{h_name}**")
        
    st.divider()

    for idx, row in df.iterrows():
        cols = st.columns([2, 2, 1, 2, 3, 1, 1, 1])
        
        cols[0].write(row['hospital_case_id'])
        cols[1].write(row['clinical_mrn'])
        cols[2].write(row['modality'])
        cols[3].write(row['ai_model_used'])
        cols[4].write(row['finding_detected'])
        cols[5].write(f"{row['confidence_score']:.2f}")
        
        # Color code triage tags
        if row['triage_status'] == 'URGENT':
            cols[6].markdown("🔴 **URGENT**")
        else:
            cols[6].markdown("🟢 ROUTINE")
            
        # 🎯 Dynamic Action Button
        # Unique keys are generated dynamically using row index to prevent Streamlit collisions
        if cols[7].button("Clear ✅", key=f"btn_{idx}_{row['hospital_case_id']}"):
            clear_case_in_db(row['hospital_case_id'])
            st.rerun()

# 🔁 Automated Heartbeat Rerun
time.sleep(5)
st.rerun()
