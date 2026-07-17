import datetime
import random
import uuid


def generate_vitals(triage_status):
    """Generates real-time numeric vitals parameters."""
    if triage_status == "critical":
        val = random.randint(78, 89)
        code, display = "L", "Low"
    else:
        val = random.randint(95, 100)
        code, display = "N", "Normal"

    return {
        "value": val,
        "unit": "%",
        "interpretation_code": code,
        "interpretation_display": display,
    }


def generate_imaging(triage_status):
    """Generates radiology metadata if an exam was ordered."""
    imaging_profiles = {
        "XR": {
            "bodySite": "Chest",
            "critical_finding": "Pneumothorax (Collapsed Lung)",
            "normal_finding": "Clear lung fields, no acute consolidation",
        },
        "CT": {
            "bodySite": "Head",
            "critical_finding": "Acute Intracranial Hemorrhage (Brain Bleed)",
            "normal_finding": "No acute intracranial ischemia or mass effect",
        },
        "MR": {
            "bodySite": "Spine",
            "critical_finding": "Acute Spinal Cord Compression",
            "normal_finding": "Normal alignment, no disc herniation",
        },
        "US": {
            "bodySite": "Abdomen",
            "critical_finding": "Abdominal Aortic Aneurysm (AAA) Rupture Signs",
            "normal_finding": "Normal caliber aorta, no free fluid",
        },
    }

    modality = random.choice(["XR", "CT", "MR", "US"])
    profile = imaging_profiles[modality]

    if triage_status == "critical":
        finding = profile["critical_finding"]
        confidence = round(random.uniform(0.85, 0.99), 2)
        priority = "CRITICAL"
    else:
        finding = profile["normal_finding"]
        confidence = round(random.uniform(0.01, 0.12), 2)
        priority = "ROUTINE"

    return {
        "modality": modality,
        "bodySite": profile["bodySite"],
        "mock_image_type": f"{triage_status}_{modality.lower()}",
        "model_name": f"RadAI-{modality}Net-v1.5",
        "primary_finding": finding,
        "confidence_score": confidence,
        "triage_priority": priority,
    }


def get_next_stream_packet():
    """Generates a comprehensive patient encounter payload containing mandatory vitals

    and optional multi-modality imaging data mimicking a unified hospital record.
    """
    triage = "critical" if random.random() < 0.25 else "normal"
    rand_id = f"pat-{random.randint(1000, 9999)}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    # 1. Every single patient gets live telemetry tracking mapped
    vitals_data = generate_vitals(triage)

    # 2. Build the core FHIR Observation framework payload
    packet = {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "patient_id": rand_id,
        "triage_status": triage.upper(),
        "vitals_telemetry": {
            "metric": "Oxygen saturation in Arterial blood by Pulse oximetry",
            "value": vitals_data["value"],
            "unit": vitals_data["unit"],
            "status": vitals_data["interpretation_display"],
        },
        "radiology_exam": None,  # Default: No scan ordered for this window
    }

    # 3. Clinical probability choice: 60% of patients also had a radiology scan done
    if random.random() < 0.60:
        packet["radiology_exam"] = generate_imaging(triage)

    return packet

# This keeps the container alive and serving network checks when run directly
if __name__ == "__main__":
    import socket
    import time

    # Bind to an internal port so our Docker health check has something to ping
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("0.0.0.0", 5000))
        server.listen(5)
        print("🟢 Mock Streamer Network Daemon Active on port 5000...")
        
        # Keep the process open indefinitely to listen for health checks
        while True:
            try:
                client_socket, addr = server.accept()
                # Close connection quickly; it's just a health check ping
                client_socket.close() 
            except Exception:
                time.sleep(1)
    except Exception as e:
        print(f"🔴 Daemon error: {e}")
        # Fallback to keep container alive if port is already bound
        while True:
            time.sleep(3600)