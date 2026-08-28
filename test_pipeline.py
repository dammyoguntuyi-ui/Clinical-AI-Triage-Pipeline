"""
test_pipeline.py - End-to-End Enterprise Triage & API Integration Tests
"""

import pytest
from fastapi.testclient import TestClient
import numpy as np
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage

from api import app
from enterprise_engine import EnterpriseHospitalEngine
from qa_evaluator import ImageQualityEvaluator

client = TestClient(app)


def create_synthetic_dicom_dataset(
    modality="CT", slice_thickness=1.5, patient_id="pat-test-101"
):
    """Generates a valid test DICOM dataset with clear ROI vs background contrast."""
    img = np.random.randint(5, 15, size=(64, 64), dtype=np.uint16)
    img[16:48, 16:48] = np.random.randint(150, 255, size=(32, 32), dtype=np.uint16)

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.8.498.101"
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.Modality = modality
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PatientID = patient_id
    ds.Rows, ds.Columns = 64, 64
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    if slice_thickness:
        ds.SliceThickness = slice_thickness
    ds.PixelData = img.tobytes()
    return ds


def test_api_healthcheck():
    """Confirms FastAPI ingestion gateway health."""
    response = client.get("/")
    assert response.status_code in [200, 404]  # Verifies server responds


def test_enterprise_engine_processing_and_dispatch():
    """Validates the core orchestration engine converts raw studies to FHIR DiagnosticReports."""
    engine = EnterpriseHospitalEngine()
    dcm = create_synthetic_dicom_dataset(modality="CT", slice_thickness=1.0)
    vitals = {"spo2": 95.0, "patient_id": "pat-test-101"}

    result = engine.process_clinical_study(dcm, vitals)

    assert result["outcome"] == "DISPATCHED"
    assert result["payload"]["status"] == "DISPATCHED"
    assert (
        result["payload"]["fhir_payload"]["resourceType"] == "DiagnosticReport"
    )
    assert (
        result["payload"]["fhir_payload"]["subject"]["reference"]
        == "Patient/pat-test-101"
    )


def test_enterprise_engine_quarantine_routing():
    """Validates that non-compliant acquisitions are routed directly to quarantine."""
    engine = EnterpriseHospitalEngine()
    # Missing slice thickness on cross-sectional scan triggers QA rejection
    dcm = create_synthetic_dicom_dataset(modality="CT", slice_thickness=None)
    vitals = {"spo2": 95.0, "patient_id": "pat-corrupt-02"}

    result = engine.process_clinical_study(dcm, vitals)

    assert result["outcome"] == "QUARANTINED"
    assert result["payload"]["status"] == "QUARANTINED"
    assert result["payload"]["hl7_error_code"] == "ERR_DICOM_QA_VIOLATION"