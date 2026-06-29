import csv
import os

# 🩺 Rule-Based Ground Truth Definitions
# This represents the strictly approved clinical mapping for the AI models
VALID_MODELS = {
    "CR": "ChestXray-Triage-v2",
    "CT": "Neuro-Stroke-CT-v4",
    "MR": "Spine-Decompression-v1",
    "US": "Vascular-DeepVein-v2"
}

REPORT_FILE = "clinical_triage_report.csv"

if not os.path.exists(REPORT_FILE):
    print(f"❌ Error: {REPORT_FILE} not found. Run ai_csv_generator.py first!")
    exit()

print("🩺 Starting Dynamic Multi-Modality Validation Audit...")
print("-" * 75)

total_cases = 0
matches = 0
discrepancies = []

with open(REPORT_FILE, mode="r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_cases += 1
        mrn = row["clinical_mrn"]
        modality = row["modality"]
        ai_model = row["ai_model_used"]
        validation_status = row.get("validation_status", "VERIFIED")
        
        # Check if the AI model used matches the required model for this imaging modality
        expected_model = VALID_MODELS.get(modality, "UNKNOWN")
        
        # 🚨 Trap our intentional simulated discrepancy
        if validation_status == "MISMATCH / AUDIT REQUIRED":
            discrepancies.append({
                "mrn": mrn, "modality": modality, "model": ai_model,
                "reason": "AI model under-called a CRITICAL Malignant Mass as standard spinal stenosis."
            })
            print(f"⚠️  {mrn} ({modality}): MISMATCH DETECTED (Simulated Audit Target)")
        elif ai_model == expected_model:
            matches += 1
            print(f"✅ {mrn} ({modality}): Pipeline routing verified successfully.")
        else:
            discrepancies.append({
                "mrn": mrn, "modality": modality, "model": ai_model,
                "reason": f"Routing Error! Modality {modality} should use {expected_model} but used {ai_model}."
            })
            print(f"❌ {mrn} ({modality}): CRITICAL ROUTING FAILURE!")

# --- PERFORMANCE METRICS ---
accuracy = (matches / total_cases) * 100 if total_cases > 0 else 0
error_rate = 100 - accuracy

print("-" * 75)
print("📊 CLINICAL PERFORMANCE METRICS SUMMARY")
print("-" * 75)
print(f"🔹 Total Audited Multi-Modality Cases : {total_cases}")
print(f"🔹 Successful AI Alignments          : {matches}")
print(f"🔹 System Accuracy Rate              : {accuracy:.1f}%")
print(f"🔹 Overall AI Error Rate              : {error_rate:.1f}%")
print("-" * 75)

if discrepancies:
    print("\n🚨 DETAILED CLINICAL DISCREPANCY REPORT:")
    for d in discrepancies:
        print(f"\n• Patient ID: {d['mrn']} [{d['modality']}]")
        print(f"  Current Model: {d['model']}")
        print(f"  Issue:         {d['reason']}")