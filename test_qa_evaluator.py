"""
test_qa_evaluator.py - Automated Unit & Integration Tests for Clinical QA & Evaluation Layer
Tested with pytest for GitHub Actions CI/CD workflows.
"""

import numpy as np
import pytest
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage

from qa_evaluator import ImageQualityEvaluator, ClinicalMetricsAuditor, QAEvaluationResult


# ---------------------------------------------------------
# Fixtures: Helper functions to create in-memory DICOMs
# ---------------------------------------------------------

@pytest.fixture
def evaluator():
    return ImageQualityEvaluator(
        min_snr_db=12.0,
        min_slice_thickness=0.5,
        max_slice_thickness=10.0,
        allowed_photometrics=["MONOCHROME1", "MONOCHROME2", "RGB"]
    )


def create_synthetic_dicom(
    pixel_array: np.ndarray,
    modality: str = "CT",
    photometric: str = "MONOCHROME2",
    slice_thickness: float = 2.5
) -> Dataset:
    """Generates an in-memory pydicom Dataset for deterministic testing."""
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.8.498.1"
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.Modality = modality
    ds.PhotometricInterpretation = photometric
    ds.SliceThickness = slice_thickness
    ds.Rows, ds.Columns = pixel_array.shape[:2]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1

    ds.PixelData = pixel_array.astype(np.uint16).tobytes()
    return ds


# ---------------------------------------------------------
# 1. Clinical Loss & Metric Auditor Tests ($F_2$, Sensitivity, Alarm Fatigue)
# ---------------------------------------------------------

def test_clinical_metrics_perfect_scores():
    y_true = [1, 1, 0, 0, 1]
    y_pred = [1, 1, 0, 0, 1]
    
    metrics = ClinicalMetricsAuditor.calculate_metrics(y_true, y_pred, tier="Emergency", beta=2.0)
    
    assert metrics.sensitivity == 1.0
    assert metrics.specificity == 1.0
    assert metrics.f1_score == 1.0
    assert metrics.f2_score == 1.0
    assert metrics.alarm_fatigue_rate == 0.0


def test_clinical_f2_penalizes_false_negatives_heavily():
    """Validates that F2 score is more severely impacted by False Negatives than Precision/F1."""
    y_true = [1, 1, 1, 1, 0]
    y_pred = [1, 1, 0, 0, 0]  # 2 False Negatives, 0 False Positives
    
    metrics = ClinicalMetricsAuditor.calculate_metrics(y_true, y_pred, tier="Emergency", beta=2.0)
    
    assert metrics.tp == 2
    assert metrics.fn == 2
    assert metrics.fp == 0
    assert metrics.sensitivity == 0.5
    # F2 should drop significantly due to high recall weighting
    assert metrics.f2_score <= metrics.f1_score


def test_alarm_fatigue_calculation():
    y_true = [0, 0, 0, 1]
    y_pred = [1, 1, 0, 1]  # 2 False Positives, 1 True Positive
    
    metrics = ClinicalMetricsAuditor.calculate_metrics(y_true, y_pred, tier="Urgent", beta=2.0)
    
    # Alarm fatigue = FP / (TP + FP) = 2 / 3 ≈ 0.6667
    assert metrics.fp == 2
    assert metrics.alarm_fatigue_rate == pytest.approx(0.6667, abs=1e-3)


# ---------------------------------------------------------
# 2. Image QA & SNR/CNR Tests
# ---------------------------------------------------------

def test_snr_and_cnr_calculation(evaluator):
    # Create image with high signal center and clean background
    img = np.zeros((100, 100), dtype=np.float32) + 10.0
    img[25:75, 25:75] = 200.0  # Bright center ROI
    
    snr_db, cnr = evaluator.compute_snr_and_cnr(img)
    
    assert snr_db > 12.0
    assert cnr > 0.0


def test_valid_dicom_passes_qa(evaluator):
    # Simulated valid diagnostic image
    img = np.random.normal(loc=150, scale=10, size=(100, 100)).clip(10, 250)
    dcm = create_synthetic_dicom(img, photometric="MONOCHROME2", slice_thickness=1.5)
    
    result: QAEvaluationResult = evaluator.evaluate_dicom(dcm)
    
    assert result.is_valid is True
    assert len(result.rejection_reasons) == 0
    assert result.ood_detected is False


# ---------------------------------------------------------
# 3. Anomaly & Out-of-Distribution (OOD) Gate Tests
# ---------------------------------------------------------

def test_blank_scan_rejection(evaluator):
    """Degenerate zero-variance acquisitions must fail the gate."""
    img = np.zeros((100, 100), dtype=np.float32)
    dcm = create_synthetic_dicom(img)
    
    result = evaluator.evaluate_dicom(dcm)
    
    assert result.is_valid is False
    assert result.ood_detected is True
    assert any("Zero pixel variance" in reason for reason in result.rejection_reasons)


def test_slice_thickness_out_of_bounds(evaluator):
    """Unrealistic or non-diagnostic slice thickness must be rejected."""
    img = np.random.normal(loc=100, scale=5, size=(100, 100)).clip(10, 200)
    dcm = create_synthetic_dicom(img, slice_thickness=25.0)  # Exceeds max 10.0mm
    
    result = evaluator.evaluate_dicom(dcm)
    
    assert result.is_valid is False
    assert any("out of diagnostic range" in reason for reason in result.rejection_reasons)


def test_invalid_photometric_interpretation(evaluator):
    img = np.random.normal(loc=100, scale=5, size=(100, 100)).clip(10, 200)
    dcm = create_synthetic_dicom(img, photometric="YBR_FULL_422")
    
    result = evaluator.evaluate_dicom(dcm)
    
    assert result.is_valid is False
    assert any("Invalid Photometric Interpretation" in reason for reason in result.rejection_reasons)