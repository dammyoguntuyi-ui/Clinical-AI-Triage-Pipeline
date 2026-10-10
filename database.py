import sqlite3
import json
import datetime
from pathlib import Path
import pandas as pd

DB_PATH = Path("clinical_audit.db")

def init_db():
    """Initializes the SQLite database with indexing and quarantine support."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Master Clinical Ledger
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinical_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            spo2_vitals TEXT,
            heart_rate INTEGER,
            modality_attached TEXT,
            triage_urgency TEXT,
            integration_status TEXT,
            attending_status TEXT
        )
    """)
    
    # 2. Quarantine / Dead-Letter Queue (DLQ) Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarantine_dlq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            patient_id TEXT,
            modality TEXT,
            error_code TEXT NOT NULL,
            rejection_reasons TEXT NOT NULL,
            raw_payload TEXT,
            resolution_status TEXT DEFAULT '🔴 UNRESOLVED'
        )
    """)
    
    # Database Indexes for VNA/PACS Query Performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_id ON clinical_ledger (patient_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_urgency ON clinical_ledger (triage_urgency);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON clinical_ledger (timestamp DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dlq_status ON quarantine_dlq (resolution_status);")
    
    conn.commit()
    conn.close()

def log_packet(packet: dict):
    """Inserts a single streaming or evaluated patient packet into the SQL database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clinical_ledger (
            timestamp, patient_id, spo2_vitals, heart_rate, 
            modality_attached, triage_urgency, integration_status, attending_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        packet.get("Timestamp"),
        packet.get("Patient ID"),
        packet.get("SpO2 Vitals"),
        packet.get("Heart Rate (BPM)"),
        packet.get("Modality Attached"),
        packet.get("Triage Urgency"),
        packet.get("Integration Status"),
        packet.get("Attending Status", "🔴 Unassigned")
    ))
    conn.commit()
    conn.close()

def update_or_insert_ledger_record(patient_id: str, modality_status: str, integration_status: str, current_ts: str, urgency: str, spo2: str, hr: int):
    """Updates an existing patient record or inserts a new one atomically using SQL."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM clinical_ledger WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("""
            UPDATE clinical_ledger 
            SET modality_attached = ?, integration_status = ?, timestamp = ?, triage_urgency = ?
            WHERE patient_id = ?
        """, (modality_status, integration_status, current_ts, urgency, patient_id))
    else:
        cursor.execute("""
            INSERT INTO clinical_ledger (
                timestamp, patient_id, spo2_vitals, heart_rate, 
                modality_attached, triage_urgency, integration_status, attending_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (current_ts, patient_id, spo2, hr, modality_status, urgency, integration_status, "🔴 Unassigned"))
        
    conn.commit()
    conn.close()

def log_quarantine_event(patient_id: str, modality: str, error_code: str, reasons: str, raw_payload: str = ""):
    """Logs failed HL7/DICOM acquisitions to the persistent Dead-Letter Queue."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quarantine_dlq (
            timestamp, patient_id, modality, error_code, rejection_reasons, raw_payload
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        patient_id,
        modality,
        error_code,
        reasons,
        raw_payload
    ))
    conn.commit()
    conn.close()

def update_attending_status(patient_id: str, new_status: str):
    """Updates the attending clinician review status via SQL."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clinical_ledger SET attending_status = ? WHERE patient_id = ?
    """, (new_status, patient_id))
    conn.commit()
    conn.close()

def fetch_ledger_records(urgency_filters: list = None, modality_filter: str = "All Studies", limit: int = 50) -> pd.DataFrame:
    """Executes parameterized SQL queries to retrieve filtered audit records."""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT timestamp as Timestamp, patient_id as 'Patient ID', spo2_vitals as 'SpO2 Vitals', heart_rate as 'Heart Rate (BPM)', modality_attached as 'Modality Attached', triage_urgency as 'Triage Urgency', integration_status as 'Integration Status', attending_status as 'Attending Status' FROM clinical_ledger WHERE 1=1"
    params = []
    
    if urgency_filters:
        placeholders = ','.join(['?'] * len(urgency_filters))
        query += f" AND triage_urgency IN ({placeholders})"
        params.extend(urgency_filters)
        
    if modality_filter == "Attached Imaging Only":
        query += " AND modality_attached != 'None (Pending)'"
    elif modality_filter == "Pending Imaging Only":
        query += " AND modality_attached = 'None (Pending)'"
        
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def fetch_dlq_records() -> pd.DataFrame:
    """Retrieves all Dead-Letter Queue entries from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT id as 'DLQ ID', timestamp as Timestamp, patient_id as 'Patient ID', modality as Modality, error_code as 'Error Code', rejection_reasons as 'Rejection Reasons', resolution_status as 'Status' FROM quarantine_dlq ORDER BY id DESC", conn)
    conn.close()
    return df

def get_all_patient_ids() -> list:
    """Retrieves all unique patient IDs from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT patient_id FROM clinical_ledger ORDER BY timestamp DESC")
    patients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return patients

def execute_raw_sql_query(query_str: str) -> pd.DataFrame:
    """Allows read-only diagnostic SQL queries from the PACS Admin Inspector."""
    conn = sqlite3.connect(DB_PATH)
    # Basic guardrail for read-only execution
    if not query_str.strip().upper().startswith("SELECT"):
        conn.close()
        raise ValueError("Security Guardrail: Only SELECT queries are permitted in diagnostic mode.")
    df = pd.read_sql_query(query_str, conn)
    conn.close()
    return df

def archive_and_tier_historical_data(retention_count: int = 50) -> dict:
    """SimulatesPACS long-term VNA tiering by archiving older ledger records to JSON cold storage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM clinical_ledger")
    total_records = cursor.fetchone()[0]
    
    if total_records <= retention_count:
        conn.close()
        return {"status": "NO_ACTION", "message": f"Ledger size ({total_records}) is within warm storage threshold ({retention_count})."}
    
    # Query records older than retention limit
    cursor.execute("SELECT * FROM clinical_ledger ORDER BY timestamp ASC LIMIT ?", (total_records - retention_count,))
    archived_rows = cursor.fetchall()
    
    archive_dir = Path("vna_cold_archive")
    archive_dir.mkdir(exist_ok=True)
    archive_file = archive_dir / f"vna_archive_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(archive_file, "w") as f:
        json.dump(archived_rows, f, indent=2)
        
    conn.close()
    return {"status": "SUCCESS", "message": f"Successfully migrated {len(archived_rows)} historical records to cold storage: `{archive_file.name}`"}