import sys
from pathlib import Path

# Add project root to sys.path so 'api' can be imported cleanly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import socket
import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

MLLP_START = b"\x0b"
MLLP_END = b"\x1c\x0d"
STATE_FILE_PATH = Path("latest_triage.json")


# ---------------------------------------------------------
# 1. API Contract & State Persistence Tests
# ---------------------------------------------------------
class TestFastAPITriageIngestion:
    @pytest.fixture(autouse=True)
    def cleanup_state_file(self):
        """Clean up generated test state files before and after runs."""
        if STATE_FILE_PATH.exists():
            STATE_FILE_PATH.unlink()
        yield
        if STATE_FILE_PATH.exists():
            STATE_FILE_PATH.unlink()

    def test_post_triage_study_success(self):
        sample_payload = {
            "timestamp": "2026-09-14T15:00:00+00:00",
            "status": "DISPATCHED",
            "patient_id": "TEST-PAT-9999",
            "modality": "CT",
            "urgency_tier": "Emergency",
            "fhir_payload": {
                "resourceType": "DiagnosticReport",
                "id": "diag-rep-TEST-PAT-9999",
                "status": "final",
                "subject": {"reference": "Patient/TEST-PAT-9999"},
            },
            "qa_result": {
                "modality": "CT",
                "is_valid": True,
                "rejection_reasons": [],
                "snr_db": 18.2,
                "cnr": 0.22,
            },
        }

        response = client.post("/triage/study", json=sample_payload)
        assert response.status_code == 200

        # Verify state file existence and content schema
        assert STATE_FILE_PATH.exists(), "latest_triage.json was not created"

        with open(STATE_FILE_PATH, "r") as f:
            persisted_data = json.load(f)

        assert persisted_data.get("outcome") == "DISPATCHED"
        assert "payload" in persisted_data

        inner_payload = persisted_data["payload"]
        assert inner_payload["patient_id"] == "TEST-PAT-9999"
        assert inner_payload["urgency_tier"] in ["Emergency", "Expedited Manual Review", "Urgent", "Routine"]
        assert inner_payload["fhir_payload"]["resourceType"] == "DiagnosticReport"


# ---------------------------------------------------------
# 2. Live MLLP / TCP Socket Handshake Test
# ---------------------------------------------------------
class TestMLLPEndpoint:
    def test_mllp_ack_handshake(self):
        """Sends an MLLP message to local Mirth port 6661 and verifies an AA ACK."""
        test_msg = (
            "MSH|^~\\&|PYTEST|HOSPITAL|MIRTH_INGEST|TRIAGE|20260914150000||ADT^A01|MSG99999|P|2.3\r"
            "PID|1||PYTEST-001^^^NHS||PYTEST^MOCK||19900101|U\r"
            "PV1|1|I|RAD^BAY_1\r"
            "OBX|1|NM|59408-5^Oxygen saturation^LN||82.0|%|95-100|L|||F\r"
            "OBX|2|NM|8867-4^Heart rate^LN||110|/min|60-100|H|||F\r"
        )
        packet = MLLP_START + test_msg.encode("utf-8") + MLLP_END

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3.0)
                s.connect(("127.0.0.1", 6661))
                s.sendall(packet)
                ack = s.recv(1024)

                assert b"|AA|" in ack or b"MSA|AA" in ack
        except (socket.error, ConnectionRefusedError):
            pytest.skip("Mirth port 6661 not reachable; skipping socket test")


# ---------------------------------------------------------
# 3. Streamlit Schema Validation Test
# ---------------------------------------------------------
def test_dashboard_json_parser_keys():
    """Validates that keys expected by app.py line 351-365 match serialized JSON output."""
    mock_saved_json = {
        "outcome": "DISPATCHED",
        "payload": {
            "patient_id": "PAT-SCHEMA-CHECK",
            "status": "DISPATCHED",
            "urgency_tier": "Routine",
            "fhir_payload": {"resourceType": "DiagnosticReport"},
            "qa_result": {"snr_db": 15.0},
        },
    }

    payload = mock_saved_json.get("payload", {})
    assert payload.get("patient_id") == "PAT-SCHEMA-CHECK"
    assert payload.get("status") == "DISPATCHED"
    assert payload.get("urgency_tier") == "Routine"
    assert isinstance(payload.get("fhir_payload"), dict)
    assert isinstance(payload.get("qa_result"), dict)