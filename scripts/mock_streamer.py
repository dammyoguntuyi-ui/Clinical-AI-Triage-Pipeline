import datetime
import random
import uuid


def generate_fhir_observation(patient_id="pat-9402", triage_status="normal"):
    """Generates a valid, simplified HL7/FHIR Observation JSON payload."""
    # Simulate a realistic clinical metric: Pulse Oximetry (Oxygen Saturation)
    if triage_status == "critical":
        val = random.randint(78, 89)  # Simulated Hypoxia (Critical)
        interpretation_code = "L"
        interpretation_display = "Low"
    else:
        val = random.randint(95, 100)  # Healthy Range (Normal)
        interpretation_code = "N"
        interpretation_display = "Normal"

    fhir_payload = {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "2708-6",
                    "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.datetime.utcnow().isoformat() + "Z",
        "valueQuantity": {
            "value": val,
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "code": "%",
        },
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": interpretation_code,
                        "display": interpretation_display,
                    }
                ]
            }
        ],
    }
    return fhir_payload


def get_next_stream_packet():
    """Generates and returns a single data packet, occasionally injecting critical anomalies."""
    triage = "critical" if random.random() < 0.15 else "normal"
    # Generate random patient IDs to simulate multiple modalities hitting the dashboard
    rand_id = f"pat-{random.randint(1000, 9999)}"
    return generate_fhir_observation(patient_id=rand_id, triage_status=triage)