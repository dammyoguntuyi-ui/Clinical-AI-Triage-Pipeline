"""
qa_evaluator.py - Quality Assurance, Anomaly Detection & Clinical Metric Evaluation Layer
Integrates with FastAPI and Streamlit pipelines.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pydicom
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Pydantic Schemas for Validation and API Contracts
# ---------------------------------------------------------

class QAEvaluationResult(BaseModel):
    is_valid: bool
    rejection_reasons: List[str] = Field(default_factory=list)
    snr_db: float
    cnr: float
    slice_thickness_mm: Optional[float] = None
    photometric_interpretation: Optional[str] = None
    ood_detected: bool = False


class ClinicalEvaluationMetrics(BaseModel):
    tier: str
    total_samples: int
    tp: int
    fp: int
    tn: int
    fn: int
    sensitivity: float
    specificity: float
    f1_score: float
    f2_score: float  # F-beta where beta=2 (penalizes FN heavily for clinical safety)
    alarm_fatigue_rate: float  # FP / (TP + FP)


# ---------------------------------------------------------
# 1. Image Quality Assessment (QA) & 2. Anomaly / OOD Checks
# ---------------------------------------------------------

class ImageQualityEvaluator:
    """Evaluates pre-inference DICOM files and pixel arrays for quality and out-of-distribution artifacts."""

    def __init__(
        self,
        min_snr_db: float = 12.0,
        min_slice_thickness: float = 0.5,
        max_slice_thickness: float = 10.0,
        allowed_photometrics: Optional[List[str]] = None,
    ):
        self.min_snr_db = min_snr_db
        self.min_slice_thickness = min_slice_thickness
        self.max_slice_thickness = max_slice_thickness
        self.allowed_photometrics = allowed_photometrics or ["MONOCHROME1", "MONOCHROME2", "RGB"]

    def compute_snr_and_cnr(self, pixel_array: np.ndarray) -> Tuple[float, float]:
        """
        Calculates Signal-to-Noise Ratio (SNR in dB) and Contrast-to-Noise Ratio (CNR).
        Uses central ROI vs periphery noise floor estimation.
        """
        h, w = pixel_array.shape[:2]
        center_roi = pixel_array[int(h * 0.25):int(h * 0.75), int(w * 0.25):int(w * 0.75)]
        background_roi = pixel_array[0:int(h * 0.1), 0:int(w * 0.1)]

        signal_mean = float(np.mean(center_roi))
        noise_std = float(np.std(background_roi)) if float(np.std(background_roi)) > 1e-5 else 1.0
        background_mean = float(np.mean(background_roi))

        snr = signal_mean / noise_std
        snr_db = 20 * np.log10(snr) if snr > 0 else 0.0
        cnr = abs(signal_mean - background_mean) / noise_std

        return round(snr_db, 2), round(cnr, 2)

    def detect_out_of_distribution(self, pixel_array: np.ndarray) -> Tuple[bool, List[str]]:
        """
        Flags corruptions, blank acquisitions, sensor clipping, or extreme intensity shifts.
        """
        ood_flags = []
        
        # Check for zero/flat image (blank scan)
        if np.std(pixel_array) < 1e-3:
            ood_flags.append("Degenerate acquisition: Zero pixel variance detected.")

        # Check for saturation/clipping (>40% pixels at min or max possible value)
        min_val, max_val = np.min(pixel_array), np.max(pixel_array)
        total_pixels = pixel_array.size
        if (np.sum(pixel_array == max_val) / total_pixels) > 0.40:
            ood_flags.append("Sensor clipping: Excessive pixel saturation detected.")
        if (np.sum(pixel_array == min_val) / total_pixels) > 0.60:
            ood_flags.append("Truncation: Majority pixel area contains no tissue signal.")

        return (len(ood_flags) > 0, ood_flags)

    def evaluate_dicom(self, dcm: pydicom.Dataset) -> QAEvaluationResult:
        """Runs full validation suite across DICOM header tags and pixel data."""
        rejection_reasons = []
        
        # 1. Tag & Metadata Auditing
        photo_interp = getattr(dcm, "PhotometricInterpretation", "UNKNOWN")
        if photo_interp not in self.allowed_photometrics:
            rejection_reasons.append(f"Invalid Photometric Interpretation: {photo_interp}")

        slice_thickness = getattr(dcm, "SliceThickness", None)
        if slice_thickness is not None:
            slice_thickness = float(slice_thickness)
            if slice_thickness < self.min_slice_thickness or slice_thickness > self.max_slice_thickness:
                rejection_reasons.append(
                    f"Slice thickness {slice_thickness}mm is out of diagnostic range ({self.min_slice_thickness}-{self.max_slice_thickness}mm)"
                )

        # 2. Pixel Analysis
        try:
            pixel_array = dcm.pixel_array.astype(np.float32)
            snr_db, cnr = self.compute_snr_and_cnr(pixel_array)
            ood_detected, ood_reasons = self.detect_out_of_distribution(pixel_array)

            if snr_db < self.min_snr_db:
                rejection_reasons.append(f"Low SNR ({snr_db} dB < {self.min_snr_db} dB threshold).")
            
            rejection_reasons.extend(ood_reasons)

        except Exception as e:
            return QAEvaluationResult(
                is_valid=False,
                rejection_reasons=[f"Pixel decompression error: {str(e)}"],
                snr_db=0.0,
                cnr=0.0,
                ood_detected=True,
            )

        return QAEvaluationResult(
            is_valid=len(rejection_reasons) == 0,
            rejection_reasons=rejection_reasons,
            snr_db=snr_db,
            cnr=cnr,
            slice_thickness_mm=slice_thickness,
            photometric_interpretation=photo_interp,
            ood_detected=ood_detected,
        )


# ---------------------------------------------------------
# 3. False-Positive/Negative Calibration & Detection Metrics
# ---------------------------------------------------------

class ClinicalMetricsAuditor:
    """
    Computes diagnostic metrics partitioned by clinical urgency tiers.
    Applies asymmetric clinical loss weighting (F-beta with beta=2)
    to penalize False Negatives for life-threatening findings.
    """

    @staticmethod
    def calculate_metrics(
        y_true: List[int],
        y_pred: List[int],
        tier: str = "Emergency",
        beta: float = 2.0,
    ) -> ClinicalEvaluationMetrics:
        """
        Calculates Sensitivity, Specificity, F1, and F-beta (default beta=2 for high recall focus).
        """
        y_t = np.array(y_true)
        y_p = np.array(y_pred)

        tp = int(np.sum((y_t == 1) & (y_p == 1)))
        tn = int(np.sum((y_t == 0) & (y_p == 0)))
        fp = int(np.sum((y_t == 0) & (y_p == 1)))
        fn = int(np.sum((y_t == 1) & (y_p == 0)))

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        # Standard F1-Score
        f1 = (2 * precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0

        # Asymmetric Clinical F-beta Score (beta=2 weights Recall 4x over Precision)
        beta_sq = beta ** 2
        f_beta_denom = (beta_sq * precision) + sensitivity
        f_beta = ((1 + beta_sq) * precision * sensitivity) / f_beta_denom if f_beta_denom > 0 else 0.0

        alarm_fatigue = fp / (tp + fp) if (tp + fp) > 0 else 0.0

        return ClinicalEvaluationMetrics(
            tier=tier,
            total_samples=len(y_true),
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            sensitivity=round(sensitivity, 4),
            specificity=round(specificity, 4),
            f1_score=round(f1, 4),
            f2_score=round(f_beta, 4),
            alarm_fatigue_rate=round(alarm_fatigue, 4),
        )