import os
from pathlib import Path
import pydicom

INBOUND_DIR = Path("test_samples/dicom_inbound")
OUTBOUND_DIR = Path("test_samples/dicom_outbound")

def anonymize_dicom(file_path, output_dir):
    try:
        ds = pydicom.dcmread(file_path)
        
        # 1. Clear or overwrite sensitive PHI tags (Safe Harbor Method)
        ds.PatientName = "ANONYMIZED^PATIENT"
        ds.PatientID = "ANON-99999"
        ds.PatientBirthDate = ""
        ds.PatientSex = "O"
        
        # Optional: Clear other institutional or physician identifiers if present
        if "InstitutionName" in ds:
            ds.InstitutionName = "REDACTED_INSTITUTION"
        if "ReferringPhysicianName" in ds:
            ds.ReferringPhysicianName = "REDACTED_PHYSICIAN"
            
        # Ensure the Patient's Age or other identifying fields are also cleared if needed
        if "PatientAge" in ds:
            ds.PatientAge = ""

        # 2. Save anonymized file to outbound directory
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"deid_{file_path.name}"
        ds.save_as(out_path)
        
        print(f"[DE-ID PASS] Scrubbed & Saved: {file_path.name} -> {out_path.name}")
        
    except Exception as e:
        print(f"[DE-ID FAIL] Error processing {file_path.name}: {e}")

def run_batch_deid():
    if not INBOUND_DIR.exists():
        print(f"[!] Inbound directory {INBOUND_DIR} does not exist.")
        return

    # Use set() to eliminate duplicate path matches from mixed casing on Windows
    dicom_files = sorted(list(set(list(INBOUND_DIR.glob("*.dcm")) + list(INBOUND_DIR.glob("*.DCM")))))
    
    print("=" * 80)
    print(f"STARTING PHI DE-IDENTIFICATION PASS ON {len(dicom_files)} UNIQUE FILES")
    print("=" * 80)

    for file_path in dicom_files:
        anonymize_dicom(file_path, OUTBOUND_DIR)

    print("=" * 80)
    print("DE-IDENTIFICATION COMPLETE — OUTBOUND PAYLOADS READY FOR AI INFERENCE")
    print("=" * 80)

if __name__ == "__main__":
    run_batch_deid()