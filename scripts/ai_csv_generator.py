import csv
import requests

# 1. Connect to your local Orthanc PACS server
ORTHANC_URL = "http://localhost:8042/patients"

try:
    print("📡 Connecting to Orthanc PACS to fetch active studies...")
    response = requests.get(ORTHANC_URL, auth=('orthanc', 'orthanc')) # Standard default login
    response.raise_for_status()
    patient_ids = response.json()
    
    print(f"✅ Found {len(patient_ids)} active patient(s) on the server.")
    
    # 2. Build our dynamic data list
    dynamic_data = []
    
    for index, orthanc_id in enumerate(patient_ids, start=1):
        # We fetch the specific details for each patient container ID
        patient_details_url = f"http://localhost:8042/patients/{orthanc_id}"
        patient_res = requests.get(patient_details_url, auth=('orthanc', 'orthanc'))
        patient_info = patient_res.json()
        
        # Extract the real DICOM Patient ID attribute safely
        clinical_mrn = patient_info.get("MainDicomTags", {}).get("PatientID", f"UNKNOWN-{index}")
        
        # Simulate an AI model assigning a triage finding based on the scan
        # In a real pipeline, your AI model would analyze the image here
        if index % 2 == 0:
            finding = "Pneumothorax (Collapsed Lung)"
            status = "URGENT"
        else:
            finding = "Normal Lung Scan"
            status = "ROUTINE"
            
        # Structure the payload row
        case_entry = {
            "hospital_case_id": orthanc_id[:17], # Using the unique Orthanc UUID string
            "clinical_mrn": clinical_mrn,
            "ai_model_used": "ChestXray-Triage-v2",
            "finding_detected": finding,
            "confidence_score": f"0.{90 + index if index < 10 else 95}",
            "triage_status": status,
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Normal_posteroanterior_chest_X-ray.jpg"
        }
        dynamic_data.append(case_entry)

    # 3. Write all fetched data automatically to our report file
    if dynamic_data:
        with open("clinical_triage_report.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=dynamic_data[0].keys())
            writer.writeheader()
            writer.writerows(dynamic_data)
        print(f"💾 Success! Written {len(dynamic_data)} live records to clinical_triage_report.csv.")
    else:
        print("⚠️ No data to write. Is your Orthanc server completely empty?")

except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Is your local Orthanc server running right now on port 8042?")
except Exception as e:
    print(f"❌ An error occurred: {e}")