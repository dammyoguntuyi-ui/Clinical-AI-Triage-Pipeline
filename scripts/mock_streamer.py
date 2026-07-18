import io
import os
import sys
import time
import uuid
import random
import socket
import datetime
import base64

# pydicom specific imports for in-memory dataset structural manipulation
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


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

def generate_synthetic_dicom_in_memory(modality: str, patient_id: str) -> pydicom.Dataset:
    """
    Generates a fully compliant, 100% synthetic in-memory DICOM object 
    for XR, CT, MR, or US modalities. Completely free of PII for HIPAA/GDPR.
    """
    modality = modality.upper()
    if modality not in ["CT", "MR", "XR", "US"]:
        raise ValueError("Unsupported modality. Choose from CT, MR, XR, or US.")

    # 1. Initialize Mandatory DICOM File Meta Information
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 0
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = generate_uid()
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    # 2. Create the FileDataset instance (In-Memory Sandbox)
    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # 3. Inject Compliant Anonymous Patient/Study Demographics
    ds.PatientName = "ANONYMOUS^PATIENT"
    ds.PatientID = patient_id  # Tied cleanly to your FHIR pipeline ID
    ds.PatientBirthDate = ""    # Empty string to explicitly remove age data
    ds.PatientSex = random.choice(["M", "F", "O"])
    
    # Study Metadata
    now = datetime.datetime.now()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.AccessionNumber = f"ACC-{random.randint(10000, 99999)}"
    ds.Modality = modality
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    # 4. Configure Modality-Specific Pixel Geometries
    if modality == "XR":
        rows, cols = 1024, 1024
        samples_per_pixel = 1
        photometric = "MONOCHROME2"
        bits_allocated = 16
    elif modality in ["CT", "MR"]:
        rows, cols = 512, 512
        samples_per_pixel = 1
        photometric = "MONOCHROME2"
        bits_allocated = 16
    elif modality == "US":
        rows, cols = 640, 480
        samples_per_pixel = 3  # RGB Matrix for Doppler mapping
        photometric = "RGB"
        bits_allocated = 8

    # 5. Apply Image Plane Framework Tags
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = samples_per_pixel
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated = bits_allocated
    ds.BitsStored = bits_allocated
    ds.HighBit = bits_allocated - 1
    ds.PixelRepresentation = 0 if modality == "US" else 1  # 0=Unsigned, 1=Signed

    # 6. Synthesize the Pixel Matrix Payload (Using pure numeric patterns)
    total_pixels = rows * cols * samples_per_pixel
    if bits_allocated == 16:
        # Create a simple geometric gradient or noise matrix
        pixel_data = bytes([random.randint(0, 255) for _ in range(total_pixels * 2)])
    else:
        # 8-bit array for Ultrasound
        pixel_data = bytes([random.randint(0, 255) for _ in range(total_pixels)])
        
    ds.PixelData = pixel_data

    return ds

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
        "radiology_exam_b64": None,  # Updated to look for the base64 string
    }

    # # 3. Clinical probability choice: 60% of patients also had a radiology scan done
    if random.random() < 0.60:
        modalities = ["CT", "MR", "XR", "US"]
        chosen_mod = random.choice(modalities)
        
        # Generate the safe, synthetic in-memory pydicom object
        dicom_dataset = generate_synthetic_dicom_in_memory(chosen_mod, rand_id)
        
        # Serialize the pydicom object to a binary memory buffer
        buffer = io.BytesIO()
        pydicom.dcmwrite(buffer, dicom_dataset)
        buffer.seek(0)
        
        # Encode binary buffer to a safe UTF-8 Base64 string for the JSON payload
        b64_string = base64.b64encode(buffer.read()).decode('utf-8')
        packet["radiology_exam_b64"] = b64_string

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