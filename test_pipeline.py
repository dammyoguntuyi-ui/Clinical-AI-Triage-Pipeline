import io
import base64
import pytest
import pydicom
from fastapi.testclient import TestClient

from app import process_unified_clinical_packet
from scripts.mock_streamer import generate_synthetic_dicom_in_memory
from api import app

api_client = TestClient(app)


@pytest.fixture
def base_test_packet():
    """Generates a baseline streaming packet structure matching our enterprise format."""
    return {
        "resourceType": "Bundle",
        "timestamp": "2026-08-17T12:00:00Z",
        "patient_id": "PAT-9999",
        "triage_status": "CRITICAL",
        "vitals_telemetry": {
            "metric": "Oxygen saturation",
            "value": 88,
            "unit": "%",
            "status": "LOW"
        },
        "heart_rate": 115,
        "systolic_bp": 85,
        "respiratory_rate": 28,
        "oxygen_saturation": 88,
        "radiology_exam_b64": None
    }


def test_parsing_valid_packet(base_test_packet):
    """Verifies that a valid packet containing an in-memory pydicom matrix maps fields accurately."""
    # 1. Synthesize a real pydicom matrix in memory for CT
    dicom_obj = generate_synthetic_dicom_in_memory("CT", "PAT-9999")

    # 2. Serialize to bytes and Base64 encode it into the test packet
    buffer = io.BytesIO()
    pydicom.dcmwrite(buffer, dicom_obj)
    buffer.seek(0)
    base_test_packet["radiology_exam_b64"] = base64.b64encode(buffer.read()).decode("utf-8")

    # 3. Parse and assert
    result = process_unified_clinical_packet(base_test_packet)

    assert result is not None
    assert result["Patient ID"] == "PAT-9999"
    assert result["Triage Level"] == "CRITICAL"
    assert "CT" in result["Imaging Modality"]
    assert result["Has Imaging"] == "Yes"
    assert "AI Classification" in result["AI Radiology Findings"] or result["AI Radiology Findings"] != "Pending AI Evaluation"


def test_parsing_polymorphic_dicom_schema_shift(base_test_packet):
    """Verifies parsing stability when the modality shifts polymorphically to an MR profile."""
    # 1. Synthesize an MR pydicom matrix
    dicom_obj = generate_synthetic_dicom_in_memory("MR", "PAT-9999")

    # 2. Base64 serialize into the payload
    buffer = io.BytesIO()
    pydicom.dcmwrite(buffer, dicom_obj)
    buffer.seek(0)
    base_test_packet["radiology_exam_b64"] = base64.b64encode(buffer.read()).decode("utf-8")

    # 3. Parse and assert
    result = process_unified_clinical_packet(base_test_packet)

    assert result["Has Imaging"] == "Yes"
    assert "MR" in result["Imaging Modality"]


def test_parsing_malformed_packet_graceful_failure():
    """Confirms that a completely stripped or empty packet defaults cleanly without crashing."""
    malformed_packet = {}
    result = process_unified_clinical_packet(malformed_packet)

    # System should safely trap the KeyError and return None to prevent crash loops
    assert result is None


# ==========================================
# FastAPI REST & Telemetry Integration Tests
# ==========================================

def test_api_health_endpoint():
    """Verifies that the /health telemetry endpoint returns HTTP 200 and healthy status."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "uptime_seconds" in data


def test_api_metrics_endpoint():
    """Verifies that the /metrics telemetry endpoint returns correct packet counts."""
    response = api_client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_packets_ingested" in data


def test_api_fhir_bundle_ingestion(base_test_packet):
    """Verifies end-to-end ingestion and triage scoring via the FHIR REST API."""
    response = api_client.post("/api/v1/fhir/Bundle", json=base_test_packet)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "PAT-9999"
    assert data["triage_level"] == "CRITICAL"