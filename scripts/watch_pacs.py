import os
import time
import sqlite3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pydicom
import random

# Define paths relative to project root
WATCH_DIR = os.path.join(".", "test_images")
DB_PATH = os.path.join(".", "data", "triage.db")

def simulate_ai_inference(mrn, modality):
    """Simulates a rapid multi-modality AI evaluation payload."""
    # Hardcoded ground-truth validation exception for Patient 005
    if mrn == "PATIENT_005":
        return {
            "model_used": "ChestXray-Triage-v2",
            "finding": "Pneumothorax (Collapsed Lung)",
            "confidence": 0.96,
            "triage": "URGENT"
        }
        
    findings_pool = {
        "CR": [("Normal Chest", 0.95, "ROUTINE"), ("Pneumothorax", 0.89, "URGENT"), ("Cardiomegaly", 0.87, "ROUTINE")],
        "CT": [("No Acute Intracranial Path", 0.98, "ROUTINE"), ("Intracranial Hemorrhage", 0.94, "URGENT")],
        "MR": [("Unremarkable Brain", 0.92, "ROUTINE"), ("Acute Ischemic Stroke", 0.91, "URGENT")],
        "US": [("Normal Abdomen", 0.96, "ROUTINE"), ("Acute Cholecystitis", 0.88, "URGENT")]
    }
    
    pool = findings_pool.get(modality, [("Inconclusive Study", 0.50, "ROUTINE")])
    selected = random.choice(pool)
    
    return {
        "model_used": f"{modality}-Triage-Engine-v1",
        "finding": selected[0],
        "confidence": selected[1],
        "triage": selected[2]
    }
class DicomTriageHandler(FileSystemEventHandler):
    def __init__(self):
        self.processed_files = set()

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.dcm'):
            return
            
        file_path = event.src_path
        if file_path in self.processed_files:
            return

        print(f"📦 New DICOM Intercepted: {os.path.basename(file_path)}")
        self.processed_files.add(file_path)
        
        # Settle time for file write stability
        time.sleep(1)
        self.process_dicom(file_path)

    def process_dicom(self, file_path):
        try:
            # 1. Parse clinical metadata tags via pydicom
            ds = pydicom.dcmread(file_path)
            mrn = getattr(ds, "PatientID", "UNKNOWN_MRN")
            modality = getattr(ds, "Modality", "UNKNOWN")
            case_id = getattr(ds, "StudyInstanceUID", os.path.basename(file_path))
            
            # 2. Run our existing multi-modality AI simulation logic
            ai_results = simulate_ai_inference(mrn, modality)
            
            # 3. Commit the telemetry payload straight to SQLite
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO triage_queue (
                    hospital_case_id, clinical_mrn, modality, 
                    ai_model_used, finding_detected, confidence_score, triage_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hospital_case_id) DO UPDATE SET
                    finding_detected=excluded.finding_detected,
                    confidence_score=excluded.confidence_score,
                    triage_status=excluded.triage_status
            ''', (
                str(case_id), mrn, modality,
                ai_results["model_used"], ai_results["finding"],
                ai_results["confidence"], ai_results["triage"]
            ))
            
            conn.commit()
            conn.close()
            print(f"✅ Data routed safely to Database row for MRN: {mrn}")
            
        except Exception as e:
            print(f"❌ Error processing DICOM data stream: {e}")

def start_listener():
    os.makedirs(WATCH_DIR, exist_ok=True)
    event_handler = DicomTriageHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIR, recursive=False)
    
    print(f"🚀 Asynchronous DICOM Pipeline Active. Monitoring folder: {WATCH_DIR}")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_listener()