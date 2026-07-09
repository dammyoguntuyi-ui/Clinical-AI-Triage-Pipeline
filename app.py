import random
import os
import json
import glob
from datetime import datetime
import streamlit as st
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation

# --- DIRECTORY CONFIGURATIONS ---
# Point to the root-level directories relative to this file
INTAKE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "streaming_intake"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

# Ensure intake path exists
os.makedirs(INTAKE_DIR, exist_ok=True)


def process_incoming_fhir_stream(raw_patient_payload: str, raw_observation_payload: str) -> dict:
    """
    Ingestion Layer: Validates incoming raw strings against official HL7 FHIR standards,
    extracts vital metrics, and determines downstream clinical triage routing.
    """
    try:
        # Strict schema validation via fhir.resources Pydantic models
        fhir_patient = Patient.parse_raw(raw_patient_payload)
        fhir_observation = Observation.parse_raw(raw_observation_payload)
        
        # Safe programmatic field extraction
        patient_mrn = fhir_patient.id
        family_name = fhir_patient.name[0].family if fhir_patient.name else "UNKNOWN"
        given_name = fhir_patient.name[0].given[0] if fhir_patient.name and fhir_patient.name[0].given else ""
        full_name = f"{given_name} {family_name}".strip()
        
        metric_display = fhir_observation.code.coding[0].display if fhir_observation.code.coding else "Metric"
        metric_value = fhir_observation.valueQuantity.value
        metric_unit = fhir_observation.valueQuantity.unit
        
        # Clinical Triage Safety Bound Evaluation
        if metric_value > 120 or metric_value < 50:
            triage_status = "CRITICAL_RED"
            action_required = "Immediate Clinical Review Triggered"
        elif metric_value > 100 or metric_value < 60:
            triage_status = "URGENT_YELLOW"
            action_required = "Expedited Care Track Allocation"
        else:
            triage_status = "ROUTINE_GREEN"
            action_required = "Standard Queue Placement"
            
        return {
            "status": "PROCESSED_SUCCESS",
            "metadata": {
                "extracted_mrn": patient_mrn,
                "patient_name": full_name,
                "metric_logged": metric_display,
                "value": metric_value,
                "unit": metric_unit,
                "timestamp": datetime.utcnow().isoformat()
            },
            "triage_outcome": {
                "status": triage_status,
                "action": action_required
            }
        }
    except Exception as malformed_schema_error:
        return {
            "status": "PIPELINE_ERROR",
            "reason": "Non-compliant HL7 FHIR structural integrity payload.",
            "details": str(malformed_schema_error)
        }


def check_for_imaging_data_match(mrn: str) -> dict:
    """
    Data Cross-Reference Layer: Scans the local data depository 
    to see if an imaging study or triage report exists matching the given MRN.
    """
    if not os.path.exists(DATA_DIR):
        return {"matched": False, "file_name": None, "type": None}
        
    # Scan files inside the root level data directory
    for file_name in os.listdir(DATA_DIR):
        # STRICT PRODUCTION MATCH RULE: Only match if the streaming MRN is exactly in the filename
        if mrn in file_name:
            return {"matched": True, "file_name": file_name, "type": "Imaging Asset/DICOM File"}
            
        # Check internal record index inside your historical triage report CSV
        if "clinical_triage_report.csv" in file_name:
            try:
                with open(os.path.join(DATA_DIR, file_name), "r") as f:
                    if mrn in f.read():
                        return {"matched": True, "file_name": file_name, "type": "CSV Registry Record"}
            except:
                pass
                
    return {"matched": False, "file_name": None, "type": None}

def run_ai_triage_inference(mrn: str, metric_value: float) -> dict:
    """
    Downstream AI Inference Tier: Simulates routing the matched imaging asset
    and clinical vitals to a deep learning model to predict emergency pathology risk.
    """
    # Simulate a deep learning processing latency delay (or just generate insights)
    ai_confidence_score = round(random.uniform(72.5, 99.1), 1)
    
    # Dynamic clinical logic: if the heart rate is high and an imaging asset is present, flag higher severity
    if metric_value > 100:
        findings = "🚨 POTENTIAL PULMONARY EMBOLISM / TACHYARRHYTHMIA DETECTION TRIGGERED"
        priority_tier = "CRITICAL ACTION REQUIRED"
    else:
        findings = "🧠 No acute intracranial or thoracic abnormalities detected on primary pixel scan."
        priority_tier = "ROUTINE REVIEW STATUS"
        
    return {
        "model_name": "ClinicalResNet-v4.2-Native",
        "confidence": f"{ai_confidence_score}%",
        "findings": findings,
        "priority": priority_tier
    }

# --- STREAMLIT USER INTERFACE CANVAS ---
st.set_page_config(page_title="Clinical AI Triage Pipeline", layout="wide")
st.title("🏥 Enterprise Clinical AI Triage Pipeline")
st.subheader("Real-Time Ingestion & Extraction Layer (HL7 FHIR Native)")

# Sidebar control panel configuration
st.sidebar.header("Pipeline Configuration")
if st.sidebar.button("🗑️ Clear Streaming Intake Queue"):
    files = glob.glob(os.path.join(INTAKE_DIR, "*.json"))
    for f in files:
        os.remove(f)
    st.sidebar.success("Queue wiped clean!")

# Query directory files sorted by newest modified time
incoming_cases = sorted(glob.glob(os.path.join(INTAKE_DIR, "incoming_case_*.json")), key=os.path.getmtime, reverse=True)

if not incoming_cases:
    st.info("⏱️ Awaiting clinical data streams. Make sure your local `mock_streamer.py` script is running inside your split workspace...")
else:
    st.success(f"⚡ Live Connection Established: Detected {len(incoming_cases)} active queue files in buffer folder.")
    
    # Process the most current streaming file packet
    latest_case_path = incoming_cases[0]
    
    with open(latest_case_path, "r") as file_data:
        case_packet = json.load(file_data)
        
    st.markdown(f"### 📥 Active Ingestion Stream: `{case_packet['case_id']}`")
    
    # Execute the primary processing extraction engine run
    pipeline_result = process_incoming_fhir_stream(
        case_packet["patient_json"], 
        case_packet["observation_json"]
    )
    
    if pipeline_result["status"] == "PROCESSED_SUCCESS":
        meta = pipeline_result["metadata"]
        triage = pipeline_result["triage_outcome"]
        
        # Display extracted clinical metrics beautifully
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Patient Identity (MRN)", value=meta["extracted_mrn"])
        with col2:
            st.metric(label=meta["metric_logged"], value=f"{meta['value']} {meta['unit']}")
        with col3:
            if "RED" in triage["status"]:
                st.error(f"🚨 {triage['status']}")
            elif "YELLOW" in triage["status"]:
                st.warning(f"⚠️ {triage['status']}")
            else:
                st.success(f"✅ {triage['status']}")
                
        st.info(f"**Automated Next Step:** {triage['action']}")
        
     # --- THE VISUAL RECONCILIATION MODALITY BLOCK ---
        st.markdown("---")
        st.subheader("🔄 Modality Cross-Reference Engine")
        
        # FIX: Pass meta["extracted_mrn"] directly so it never pulls an old file ID
        match_status = check_for_imaging_data_match(meta["extracted_mrn"])
        
        if match_status["matched"]:
            st.success(
                f"🔗 **RECONCILIATION MATCH DETECTED:** Successfully cross-referenced FHIR Stream MRN **{meta['extracted_mrn']}** "
                f"with local data layer asset: `{match_status['file_name']}` ({match_status['type']})."
            )
            st.caption("🎯 **Status:** Clinical telemetry and imaging data metrics fully synchronized. Safe to deploy downstream AI inferencing.")
            
            # --- NEW: TRIGGER DOWNSTREAM AI INTERFACE ---
            st.markdown("### 🧠 Downstream AI Inference Results")
            with st.spinner("Analyzing matched imaging study pixel matrix..."):
                ai_results = run_ai_triage_inference(meta["extracted_mrn"], meta["value"])
                
                # Display the AI model insights beautifully
                ai_col1, ai_col2 = st.columns([1, 2])
                with ai_col1:
                    st.metric(label="Model Confidence Score", value=ai_results["confidence"])
                    st.caption(f"Engine: `{ai_results['model_name']}`")
                with ai_col2:
                    st.warning(f"**AI Findings:** {ai_results['findings']}")
                    st.info(f"**Recommended Clinical Triage Track:** {ai_results['priority']}")
        else:
            st.warning(
                f"📡 **Scanning Data Deposit...** FHIR Telemetry stream active for MRN **{meta['extracted_mrn']}**, "
                f"but no matching imaging files or historical registry records located yet in the database folder."
            )
            
        # Inspect code compliance components underneath
        with st.expander("👁️ Inspect Raw HL7 FHIR Stream JSON Structural Segments"):
            c1, c2 = st.columns(2)
            c1.markdown("#### Patient Resource Schema Block")
            c1.json(case_packet["patient_json"])
            c2.markdown("#### Observation Resource Schema Block")
            c2.json(case_packet["observation_json"])
            
    else:
        st.error(f"🛑 Pipeline Ingestion Exception: {pipeline_result['reason']}")
        st.code(pipeline_result["details"])

# Auto-refresh control dashboard widgets
st.sidebar.markdown("---")
refresh_rate = st.sidebar.slider("Auto-Refresh Dashboard Interval (Seconds)", 2, 10, 5)
st.sidebar.caption(f"Syncing UI canvas every {refresh_rate}s...")

# Re-execute application loop on a set time delay threshold to follow streamer
st.rerun()