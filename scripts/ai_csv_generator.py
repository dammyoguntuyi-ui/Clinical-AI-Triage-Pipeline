import csv

# Define the triage data package
data = [
    {
        "hospital_case_id": "073cef7d-a08dcb58",
        "clinical_mrn": "112516",
        "ai_model_used": "ChestXray-Triage-v2",
        "finding_detected": "Pneumothorax (Collapsed Lung)",
        "confidence_score": "0.94",
        "triage_status": "URGENT"
    },
    {
        "hospital_case_id": "08657946-be35904a",
        "clinical_mrn": "COVID-19-AR-16439216",
        "ai_model_used": "ChestXray-Triage-v2",
        "finding_detected": "Normal Lung Scan",
        "confidence_score": "0.98",
        "triage_status": "ROUTINE"
    }
]

# Write the data to a clean CSV report file
with open("clinical_triage_report.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

print("💾 Success! Generated 'clinical_triage_report.csv' in your workspace folder.")