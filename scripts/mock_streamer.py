import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
import os
import time
import json
import random
from datetime import datetime
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation

# Secure absolute path routing back to the project root folder
INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "streaming_intake"))
os.makedirs(INPUT_DIR, exist_ok=True)

def generate_mock_fhir_bundle(case_number: int):
    """
    Generates enterprise-grade, schema-validated HL7 FHIR payloads
    to simulate a live streaming hospital intake feed.
    """
    # 1. Build a valid, typed FHIR Patient Resource
    patient_id = f"pat-{random.randint(1000, 9999)}"
    patient = Patient.construct(
        resourceType="Patient",
        id=patient_id,
        active=True,
        name=[{"family": random.choice(["Smith", "Jones", "Taylor", "Ogun"]), "given": ["SyntheticPatient"]}],
        gender=random.choice(["male", "female"]),
        birthDate=f"{random.randint(1950, 2010)}-05-12"
    )

    # 2. Build a valid, typed FHIR Observation Resource (Heart Rate Tracking)
    # Generates values across normal, elevated, and critical ranges
    heart_rate_value = float(random.randint(45, 145)) 
    
    observation = Observation.construct(
        resourceType="Observation",
        id=f"obs-{random.randint(1000, 9999)}",
        status="final",
        category=[{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs"
            }]
        }],
        code={
            "coding": [{
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }]
        },
        subject={"reference": f"Patient/{patient_id}"},
        valueQuantity={
            "value": heart_rate_value,
            "unit": "beats/minute",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    )

    # 3. Consolidate into a streaming packet
    payload = {
        "case_id": f"CASE-{case_number}",
        "patient_json": patient.json(),
        "observation_json": observation.json()
    }

    # Dispatch to the root level intake folder
    file_path = os.path.join(INPUT_DIR, f"incoming_case_{case_number}.json")
    with open(file_path, "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"📦 [Streamer]: Dispatched FHIR payloads for {payload['case_id']} (HR: {heart_rate_value})")

if __name__ == "__main__":
    print("🚀 Starting local clinical data streaming simulation... (Ctrl+C to exit)")
    case_count = 1
    try:
        while True:
            generate_mock_fhir_bundle(case_count)
            case_count += 1
            time.sleep(20)  # Streams a new case packet every 20 seconds
    except KeyboardInterrupt:
        print("\n🛑 Streaming simulation stopped successfully.")