import csv
import os

# 🩺 The Human Specialist "Ground Truth" Baseline
# This represents the definitive diagnosis from senior radiologists.
GROUND_TRUTH = {
    "PATIENT_001": {"modality": "CR", "status": "URGENT", "finding": "Pneumothorax (Collapsed Lung)"},
    "PATIENT_002": {"modality": "CR", "status": "URGENT", "finding": "Pneumothorax (Collapsed Lung)"},
    "PATIENT_003": {"modality": "CT", "status": "URGENT", "finding": "Acute Intracranial Hemorrhage"},
    "PATIENT_004": {"modality": "US", "status": "ROUTINE", "finding": "Deep Vein Thrombosis (DVT) Cleared"},
    # 💥 SIMULATED DISCREPANCY: The human specialist found a massive tumor, 
    # but our mock AI is going to label it as a spinal stenosis.
    "PATIENT_005": {"modality": "MR", "status": "CRITICAL", "finding": "Malignant Spinal Cord Mass"}
}

REPORT_FILE = "clinical_triage_report.csv"

if not os.path.exists(REPORT_FILE):
    print(f"❌ Error: {REPORT_FILE} not found. Run ai_csv_generator.py first!")
    exit()

print("🩺 Starting Multi-Modality Clinical AI Validation Audit...")
print("-" * 70)

total_cases = 0
matches = 0
discrepancies = []

with open(REPORT_FILE, mode="r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        mrn = row["clinical_mrn"]
        ai_status = row["triage_status"]
        ai_finding = row["finding_detected"]
        ai_model = row["ai_model_used"]
        
        if mrn in GROUND_TRUTH:
            total_cases += 1
            true_status = GROUND_TRUTH[mrn]["status"]
            true_finding = GROUND_TRUTH[mrn]["finding"]
            
            # Audit the AI's triage status priority against human ground truth
            if ai_status == true_status:
                matches += 1
                print(f"✅ {mrn} ({row['modality']}): AI matched human baseline ({ai_status}).")
            else:
                discrepancies.append({
                    "mrn": mrn,
                    "modality": row["modality"],
                    "model": ai_model,
                    "ai_status": ai_status,
                    "true_status": true_status,
                    "ai_finding": ai_finding,
                    "true_finding": true_finding
                })
                print(f"⚠️  {mrn} ({row['modality']}): MISMATCH DETECTED!")

# --- PERFORMANCE METRICS ---
accuracy = (matches / total_cases) * 100 if total_cases > 0 else 0
error_rate = 100 - accuracy

print("-" * 70)
print("📊 CLINICAL PERFORMANCE METRICS SUMMARY")
print("-" * 70)
print(f"🔹 Total Audited Multi-Modality Cases : {total_cases}")
print(f"🔹 Successful AI Alignments          : {matches}")
print(f"🔹 System Accuracy Rate              : {accuracy:.1f}%")
print(f"🔹 Overall AI Error Rate              : {error_rate:.1f}%")
print("-" * 70)

if discrepancies:
    print("\n🚨 DETAILED CLINICAL DISCREPANCY REPORT:")
    for d in discrepancies:
        print(f"\n• Patient ID: {d['mrn']} [{d['modality']}]")
        print(f"  AI Model:   {d['model']}")
        print(f"  [AI Output]      Triage: {d['ai_status']} | Finding: {d['ai_finding']}")
        print(f"  [Ground Truth]   Triage: {d['true_status']} | Finding: {d['true_finding']}")
        print(f"  Clinical Risk:   AI downgraded a CRITICAL mass to URGENT stenosis. Potential delay in oncology review!")
else:
    print("\n🌟 No clinical discrepancies found in this run.")