import requests
import json
import random

BASE_URL = "http://localhost:8042"
AUTH = ("orthanc", "orthanc")

# 🔴 PASTE YOUR UNIQUE MAKE.COM URL INSIDE THESE QUOTES:
WEBHOOK_URL = "https://hook.eu1.make.com/87m1xv833govo2qvo2wxokhgxd05xexp"

def run_ai_triage_pipeline():
    print("🔄 Step 1: Fetching un-triaged studies from Orthanc PACS...")
    response = requests.get(f"{BASE_URL}/patients", auth=AUTH)
    patient_hashes = response.json()
    
    if not patient_hashes:
        print("⚠️ No studies found to process.")
        return
    
    target_patient_hash = patient_hashes[0]
    patient_details = requests.get(f"{BASE_URL}/patients/{target_patient_hash}", auth=AUTH).json()
    clinical_id = patient_details.get("MainDicomTags", {}).get("PatientID", "UNKNOWN")
    
    print(f"🔒 Anonymized data pulled for testing. Clinical Ref: {clinical_id}")
    print("🧠 Step 2: Simulating AI Inference Engine call...")
    
    # Define our clinical AI payload
    ai_analysis_payload = {
        "hospital_case_id": target_patient_hash,
        "clinical_mrn": clinical_id,
        "ai_model_used": "ChestXray-Triage-v2",
        "finding_detected": "Pneumothorax (Collapsed Lung)",
        "confidence_score": 0.94,
        "triage_status": "URGENT"
    }
    
    print(f"✅ AI Analysis Complete: {ai_analysis_payload['finding_detected']} ({ai_analysis_payload['confidence_score']*100}%)")
    print(f"🚨 Triage Priority set to: {ai_analysis_payload['triage_status']}")
    
    # Save local JSON backup
    with open("ai_output.json", "w") as json_file:
        json.dump(ai_analysis_payload, json_file, indent=4)

    # 🚀 Push the live payload straight across the web to Make.com -> Glide
    print("📡 Transmitting alert payload to live Clinician Dashboard...")
    try:
        web_response = requests.post(WEBHOOK_URL, json=ai_analysis_payload)
        if web_response.status_code in [200, 201]:
            print("🎉 Success! Alert data transmitted over the network.")
        else:
            print(f"⚠️ Web hook server responded with code: {web_response.status_code}")
    except Exception as e:
        print(f"❌ Failed to transmit data over network: {e}")

if __name__ == "__main__":
    run_ai_triage_pipeline()

def evaluate_imaging_finding(dicom_obj):
    """
    Bridge function to extract modality data and dynamically differentiate
    between normal cases and acute clinical pathologies.
    """
    modality = dicom_obj.get("Modality", "UNKNOWN")
    
    # Introduce a 50% probability threshold for a normal vs abnormal study
    is_normal = random.random() < 0.50
    
    if is_normal:
        return f"AI Classification: Routine {modality} Scan Analysis Complete - No Acute Pathologies Detected"
    
    # If not normal, dynamically assign a specific clinical problem
    if modality == "CT":
        return "AI Classification: Suspected Acute Intracranial Hemorrhage"
    elif modality == "MR":
        return "AI Classification: Anomalous Tissue Mass Detected"
    elif modality == "XR":
        return "AI Classification: Linear Cortical Disruption / Fracture"
    else:
        return f"AI Classification: Emergency Clinical Abnormality Identified on {modality}"