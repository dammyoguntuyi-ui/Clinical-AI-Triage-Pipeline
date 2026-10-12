import os
import sqlite3
from pathlib import Path
import pydicom

# Paths
INPUT_DIR = Path("test_samples/dicom_inbound")
DB_PATH = Path("data/clinical_ledger.db")

def init_db():
    """Ensure audit table exists with multi-modality schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinical_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            patient_id TEXT,
            modality TEXT,
            study_uid TEXT,
            sop_uid TEXT,
            transfer_syntax TEXT,
            file_size_kb REAL,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def validate_and_process_dicom(file_path):
    """Parses real DICOM headers and writes audit log to SQLite ledger with deduplication."""
    try:
        # Read dataset without loading massive pixel arrays immediately
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        
        # Header Tag Extraction
        patient_id = str(getattr(ds, "PatientID", "ANONYMIZED"))
        modality = str(getattr(ds, "Modality", "UNKNOWN"))
        study_uid = str(getattr(ds, "StudyInstanceUID", "UNKNOWN_STUDY_UID"))
        sop_uid = str(getattr(ds, "SOPInstanceUID", "UNKNOWN_SOP_UID"))
        
        # Transfer Syntax Extraction from File Meta
        transfer_syntax = "UNKNOWN"
        if hasattr(ds, "file_meta") and "TransferSyntaxUID" in ds.file_meta:
            transfer_syntax = str(ds.file_meta.TransferSyntaxUID.name or ds.file_meta.TransferSyntaxUID)
            
        file_size_kb = round(os.path.getsize(file_path) / 1024.0, 2)

        # Connect to SQLite Ledger
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Deduplication Check: Skip if filename or SOP Instance UID already logged
        cursor.execute("SELECT id FROM clinical_ledger WHERE filename = ? OR sop_uid = ?", (file_path.name, sop_uid))
        existing = cursor.fetchone()
        
        if existing:
            print(f" [SKIP] {file_path.name[:35]:<35} | Already exists in ledger.")
            conn.close()
            return

        # Insert new unique record
        cursor.execute("""
            INSERT INTO clinical_ledger (filename, patient_id, modality, study_uid, sop_uid, transfer_syntax, file_size_kb, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_path.name, patient_id, modality, study_uid, sop_uid, transfer_syntax, file_size_kb, "REAL_DCM_INGESTED"))
        
        conn.commit()
        conn.close()

        print(f" [PASS] {file_path.name[:35]:<35} | Modality: {modality:<3} | Size: {file_size_kb:>8.1f} KB")

    except Exception as e:
        print(f" [FAIL] {file_path.name[:35]:<35} | Error: {e}")

def run_batch_ingestion():
    init_db()
    if not INPUT_DIR.exists():
        print(f"[!] Directory {INPUT_DIR} not found. Please create it and add .dcm files.")
        return

    # Use set() to eliminate duplicate path matches from mixed casing on Windows
    dicom_files = sorted(list(set(list(INPUT_DIR.glob("*.dcm")) + list(INPUT_DIR.glob("*.DCM")))))
    if not dicom_files:
        print(f"[!] No .dcm files found in {INPUT_DIR}")
        return

    print("=" * 80)
    print(f"STARTING INGESTION TEST: {len(dicom_files)} UNIQUE REAL DICOM PAYLOADS")
    print("=" * 80)

    for file_path in dicom_files:
        validate_and_process_dicom(file_path)

    print("=" * 80)
    print("INGESTION COMPLETE — DEDUPLICATION APPLIED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    run_batch_ingestion()