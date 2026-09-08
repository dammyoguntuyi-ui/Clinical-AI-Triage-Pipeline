"""
scripts/evaluate_gold_standard.py
Executes end-to-end evaluation across the gold-standard corpus using the enterprise engine.
"""

from pathlib import Path
import pandas as pd
import pydicom
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from enterprise_engine import EnterpriseHospitalEngine

def run_corpus_evaluation(corpus_dir: str = "data/gold_standard_eval") -> pd.DataFrame:
    engine = EnterpriseHospitalEngine()
    results = []

    for dcm_file in Path(corpus_dir).rglob("*.dcm"):
        modality = dcm_file.parent.parent.name
        pathology = dcm_file.parent.name
        is_acute = not pathology.startswith("normal")

        # Read DICOM file
        ds = pydicom.dcmread(dcm_file)

        # Retrieve simulated AI confidence or default to acute flag
        sim_conf = 0.88 if is_acute else 0.05
        if hasattr(ds, "ClinicalTrialTimePointDescription") and "sim_conf=" in ds.ClinicalTrialTimePointDescription:
            sim_conf = float(ds.ClinicalTrialTimePointDescription.split("=")[1])

        # Ingest through full QA and triage pipeline
        vitals = {
            "spo2": 92.0 if is_acute else 98.0,
            "heart_rate": 115 if is_acute else 72,
            "ai_confidence": sim_conf
        }
        payload = engine.process_clinical_study(ds, patient_vitals=vitals)

        inner_payload = payload.get("payload", {})
        assigned_tier = inner_payload.get("urgency_tier", "Unknown")
        outcome = payload.get("outcome", "Unknown")
        risk_score = inner_payload.get("composite_risk_score", 0.0)

        # Emergency or Expedited Manual Review indicates flagged acute triage
        is_flagged = assigned_tier in ["Emergency", "Expedited Manual Review"]

        # Determine diagnostic category
        if is_flagged and is_acute:
            cat = "TP"
        elif not is_flagged and not is_acute:
            cat = "TN"
        elif is_flagged and not is_acute:
            cat = "FP"
        else:
            cat = "FN"

        results.append({
            "File": dcm_file.name,
            "Modality": modality,
            "Pathology": pathology,
            "True Acute": is_acute,
            "Risk Score": round(risk_score, 3),
            "Assigned Tier": assigned_tier,
            "Engine Outcome": outcome,
            "Classification": cat
        })

    return pd.DataFrame(results)

if __name__ == "__main__":
    df = run_corpus_evaluation()
    print("\n==========================================")
    print("      GOLD-STANDARD EVALUATION REPORT     ")
    print("==========================================")
    print(df[["Modality", "Pathology", "True Acute", "Risk Score", "Assigned Tier", "Classification"]].to_string(index=False))
    
    tp = (df["Classification"] == "TP").sum()
    fn = (df["Classification"] == "FN").sum()
    tn = (df["Classification"] == "TN").sum()
    fp = (df["Classification"] == "FP").sum()
    
    sensitivity = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
    specificity = (tn / (tn + fp)) * 100 if (tn + fp) > 0 else 0.0
    
    print("\n---------------- Metrics -----------------")
    print(f"Cohort Size:  {len(df)}")
    print(f"Sensitivity:  {sensitivity:.1f}% ({tp}/{tp + fn})")
    print(f"Specificity:  {specificity:.1f}% ({tn}/{tn + fp})")
    print(f"False Negatives: {fn}")
    print("==========================================\n")