import pytest
from app import process_unified_clinical_packet

# ==========================================
# 1. FIXTURES: MOCK DATA BUNDLES
# ==========================================
@pytest.fixture
def valid_clinical_packet():
    """Generates a perfectly formed multi-modality patient data bundle."""
    return {
        "timestamp": "2026-07-17 22:00:00",
        "patient_id": "PAT-9999",
        "triage_status": "CRITICAL",
        "vitals_telemetry": {
            "value": "88",
            "unit": "%",
            "status": "LOW"
        },
        "radiology_exam": {
            "modality": "CT",
            "bodySite": "Chest",
            "primary_finding": "Pulmonary Embolism detected",
            "mock_image_type": "DICOM_AXIAL_102"
        }
    }

@pytest.fixture
def malformed_clinical_packet():
    """Generates a corrupted packet missing critical vitals blocks to simulate network corruption."""
    return {
        "timestamp": "2026-07-17 22:01:00",
        "patient_id": "PAT-ERR",
        "triage_status": "UNKNOWN",
        # Missing 'vitals_telemetry' completely to trigger a KeyError
        "radiology_exam": {
            "modality": "XR",
            "bodySite": "Hand",
            "primary_finding": "No fracture",
            "mock_image_type": "DICOM_AP_001"
        }
    }

# ==========================================
# 2. INTEGRATION ASSERTION TEST SUITE
# ==========================================
def test_parsing_valid_packet(valid_clinical_packet):
    """Verifies that a correct payload maps fields accurately to the master schema."""
    result = process_unified_clinical_packet(valid_clinical_packet)
    
    assert result is not None
    assert result["Patient ID"] == "PAT-9999"
    assert result["Triage Level"] == "CRITICAL"
    assert "CT (Chest)" in result["Imaging Modality"]
    assert result["Numeric SpO2"] == 88

def test_parsing_malformed_packet_graceful_failure(malformed_clinical_packet):
    """Ensures the parsing component returns None instead of throwing an unhandled exception."""
    # The function should catch the KeyError internally and return None gracefully
    result = process_unified_clinical_packet(malformed_clinical_packet)
    
    assert result is None

# ==========================================
# 3. POLYMORPHIC DICOM VARIATION SUITE
# ==========================================

def test_parsing_polymorphic_dicom_missing_imaging(valid_clinical_packet):
    """
    Verifies payload processing resilience when 'radiology_exam' is None.
    Simulates situations where only bedside vitals streams are active.
    """
    # Mutate the fixture to simulate a packet with no diagnostic imaging ordered
    polymorphic_packet = valid_clinical_packet.copy()
    polymorphic_packet["radiology_exam"] = None

    result = process_unified_clinical_packet(polymorphic_packet)

    assert result is not None
    assert result["Has Imaging"] == "No"
    assert result["Imaging Modality"] == "None Ordered"
    assert result["AI Radiology Findings"] == "N/A"
    assert result["Numeric SpO2"] == 88


def test_parsing_polymorphic_dicom_schema_shift(valid_clinical_packet):
    """
    Verifies parsing stability if structural imaging tags shift layout,
    ensuring core encounter routing fields remain extractable.
    """
    polymorphic_packet = valid_clinical_packet.copy()
    
    # Simulate a structural shift where metadata tags are truncated or structured differently
    polymorphic_packet["radiology_exam"] = {
        "modality": "MR",
        "bodySite": "Spine",
        "primary_finding": "L4-L5 Disc Herniation",
        "mock_image_type": "DICOM_SAGITTAL_004"
        # Imagine an upstream change dropped or renamed other optional telemetry attributes
    }

    result = process_unified_clinical_packet(polymorphic_packet)

    assert result is not None
    assert result["Imaging Modality"] == "MR (Spine)"
    assert result["AI Radiology Findings"] == "L4-L5 Disc Herniation"
    assert result["Patient ID"] == "PAT-9999"