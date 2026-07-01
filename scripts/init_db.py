import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "triage.db")

def initialize_database():
    print(f"Initializing database at: {DB_PATH}")
    
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the central triage queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS triage_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_case_id TEXT UNIQUE,
            clinical_mrn TEXT,
            modality TEXT,
            ai_model_used TEXT,
            finding_detected TEXT,
            confidence_score REAL,
            triage_status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            review_status TEXT DEFAULT 'PENDING'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully with 'review_status' tracking!")

if __name__ == "__main__":
    initialize_database()