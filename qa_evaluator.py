"""
qa_evaluator.py - Modality-Aware Quality Assurance, Anomaly Gating & Clinical Metric Layer
Supports dynamic evaluation rules tailored for CT, MR, DX/CR, US, and SEG (Segmentation Objects).
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pydicom
from pydantic import BaseModel, Field


class QAEvaluationResult(BaseModel):
    modality: str
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
    f2_score: float  # Asymmetric loss (beta=2) heavily penalizing False Negatives
    alarm_fatigue_rate: float


class ImageQualityEvaluator:
    """
    Automated modality-aware DICOM QA evaluator.
    Applies custom tag constraints, photometric profiles, and pixel calibration
    based on acquisition modality.
    """

    # Modality-specific rule configurations
    MODALITY_RULES: Dict[str, Dict[str, Any]] = {
        "CT": {
            "min_snr_db": 10.0,
            "min_slice_thickness": 0.5,
            "max_slice_thickness": 10.0,
            "allowed_photometrics": ["MONOCHROME1", "MONOCHROME2"],
            "requires_slice_thickness": True,
            "apply_rescale": True,
            "is_derived_mask": False,
        },
        "MR": {
            "min_snr_db": 8.0,
            "min_slice_thickness": 0.5,
            "max_slice_thickness": 10.0,
            "allowed_photometrics": ["MONOCHROME1", "MONOCHROME2"],
            "requires_slice_thickness": True,
            "apply_rescale": False,
            "is_derived_mask": False,
        },
        "DX": {  # Digital Radiography / XR
            "min_snr_db": 12.0,
            "min_slice_thickness": None,
            "max_slice_thickness": None,
            "allowed_photometrics": ["MONOCHROME1", "MONOCHROME2"],
            "requires_slice_thickness": False,
            "apply_rescale": False,
            "is_derived_mask": False,
        },
        "CR": {  # Computed Radiography
            "min_snr_db": 12.0,
            "min_slice_thickness": None,
            "max_slice_thickness": None,
            "allowed_photometrics": ["MONOCHROME1", "MONOCHROME2"],
            "requires_slice_thickness": False,
            "apply_rescale": False,
            "is_derived_mask": False,
        },
        "US": {  # Ultrasound (supports Doppler & JPEG2000 color transforms)
            "min_snr_db": 6.0,
            "min_slice_thickness": None,
            "max_slice_thickness": None,
            "allowed_photometrics": [
                "MONOCHROME2",
                "RGB",
                "YBR_FULL",
                "YBR_FULL_422",
                "YBR_ICT",
                "YBR_RCT",
            ],
            "requires_slice_thickness": False,
            "apply_rescale": False,
            "is_derived_mask": False,
        },
        "SEG": {  # Segmentation / Binary ROI Mask Objects
            "min_snr_db": None,
            "min_slice_thickness": None,
            "max_slice_thickness": None,
            "allowed_photometrics": ["MONOCHROME2", "BINARY"],
            "requires_slice_thickness": False,
            "apply_rescale": False,
            "is_derived_mask": True,
        },
    }

    def _normalize_pixel_data(self, dcm: pydicom.Dataset, modality: str) -> np.ndarray:
        """Extracts pixel array and applies Hounsfield Unit rescaling for CT if available."""
        pixels = dcm.pixel_array.astype(np.float32)

        # Apply Hounsfield Unit rescaling (HU = pixel * slope + intercept)
        if modality == "CT" and hasattr(dcm, "RescaleSlope") and hasattr(dcm, "RescaleIntercept"):
            slope = float(dcm.RescaleSlope)
            intercept = float(dcm.RescaleIntercept)
            pixels = (pixels * slope) + intercept

        # Convert multi-channel (e.g. RGB/YBR Ultrasound) to luminance for SNR/CNR analysis
        if pixels.ndim == 3 and pixels.shape[-1] in (3, 4):
            pixels = 0.2989 * pixels[:, :, 0] + 0.5870 * pixels[:, :, 1] + 0.1140 * pixels[:, :, 2]

        return pixels

    def compute_snr_and_cnr(self, pixel_array: np.ndarray) -> Tuple[float, float]:
        """Calculates central ROI vs background noise metrics."""
        h, w = pixel_array.shape[:2]
        center_roi = pixel_array[int(h * 0.25):int(h * 0.75), int(w * 0.25):int(w * 0.75)]
        background_roi = pixel_array[0:int(h * 0.1), 0:int(w * 0.1)]

        signal_mean = float(np.mean(center_roi))
        noise_std = float(np.std(background_roi)) if float(np.std(background_roi)) > 1e-5 else 1.0
        background_mean = float(np.mean(background_roi))

        snr = signal_mean / noise_std
        snr_db = 20 * np.log10(abs(snr)) if abs(snr) > 0 else 0.0
        cnr = abs(signal_mean - background_mean) / noise_std

        return round(float(snr_db), 2), round(float(cnr), 2)

    def detect_out_of_distribution(self, pixel_array: np.ndarray) -> Tuple[bool, List[str]]:
        """Flags degenerate acquisitions, saturated sensors, and extreme clipping."""
        ood_flags = []
        if np.std(pixel_array) < 1e-3:
            ood_flags.append("Degenerate acquisition: Zero pixel variance detected.")

        min_val, max_val = np.min(pixel_array), np.max(pixel_array)
        total_pixels = pixel_array.size
        if (np.sum(pixel_array == max_val) / total_pixels) > 0.40:
            ood_flags.append("Sensor clipping: Excessive pixel saturation detected.")
        if (np.sum(pixel_array == min_val) / total_pixels) > 0.65:
            ood_flags.append("Truncation: Majority pixel area contains no tissue signal.")

        return (len(ood_flags) > 0, ood_flags)

    def evaluate_dicom(self, dcm: pydicom.Dataset) -> QAEvaluationResult:
        """Dynamically routes validation logic based on DICOM Modality tag."""
        rejection_reasons = []
        modality = getattr(dcm, "Modality", "UNKNOWN").upper()

        rules = self.MODALITY_RULES.get(
            modality,
            {
                "min_snr_db": 8.0,
                "min_slice_thickness": None,
                "max_slice_thickness": None,
                "allowed_photometrics": ["MONOCHROME1", "MONOCHROME2", "RGB", "YBR_FULL", "YBR_ICT"],
                "requires_slice_thickness": False,
                "is_derived_mask": False,
            },
        )

        # 1. Photometric Validation
        photo_interp = getattr(dcm, "PhotometricInterpretation", "UNKNOWN")
        if photo_interp not in rules["allowed_photometrics"]:
            rejection_reasons.append(
                f"Invalid Photometric Interpretation '{photo_interp}' for modality {modality}."
            )

        # 2. Slice Thickness Check (Cross-sectional only)
        slice_thickness = getattr(dcm, "SliceThickness", None)
        if rules["requires_slice_thickness"]:
            if slice_thickness is None:
                rejection_reasons.append(f"Missing mandatory SliceThickness header for {modality}.")
            else:
                slice_thickness = float(slice_thickness)
                min_th, max_th = rules["min_slice_thickness"], rules["max_slice_thickness"]
                if slice_thickness < min_th or slice_thickness > max_th:
                    rejection_reasons.append(
                        f"Slice thickness {slice_thickness}mm out of range ({min_th}-{max_th}mm) for {modality}."
                    )

        # 3. Derived Masks / SEG Objects Bypass Acoustic Noise & HU Audits
        if rules.get("is_derived_mask", False):
            return QAEvaluationResult(
                modality=modality,
                is_valid=len(rejection_reasons) == 0,
                rejection_reasons=rejection_reasons,
                snr_db=0.0,
                cnr=0.0,
                slice_thickness_mm=float(slice_thickness) if slice_thickness else None,
                photometric_interpretation=photo_interp,
                ood_detected=False,
            )

        # 4. Pixel Calibration & Acoustic/Signal Analysis
        try:
            pixel_array = self._normalize_pixel_data(dcm, modality)
            snr_db, cnr = self.compute_snr_and_cnr(pixel_array)
            ood_detected, ood_reasons = self.detect_out_of_distribution(pixel_array)

            if rules["min_snr_db"] is not None and snr_db < rules["min_snr_db"]:
                rejection_reasons.append(
                    f"Low SNR ({snr_db} dB < {rules['min_snr_db']} dB threshold for {modality})."
                )

            rejection_reasons.extend(ood_reasons)

        except Exception as e:
            rejection_reasons.append(f"Pixel decompression error: {str(e)}")
            return QAEvaluationResult(
                modality=modality,
                is_valid=False,
                rejection_reasons=rejection_reasons,
                snr_db=0.0,
                cnr=0.0,
                slice_thickness_mm=float(slice_thickness) if slice_thickness else None,
                photometric_interpretation=photo_interp,
                ood_detected=True,
            )

        return QAEvaluationResult(
            modality=modality,
            is_valid=len(rejection_reasons) == 0,
            rejection_reasons=rejection_reasons,
            snr_db=snr_db,
            cnr=cnr,
            slice_thickness_mm=float(slice_thickness) if slice_thickness else None,
            photometric_interpretation=photo_interp,
            ood_detected=ood_detected,
        )


class ClinicalMetricsAuditor:
    """Asymmetric Clinical Evaluation Metrics Auditor."""

    @staticmethod
    def calculate_metrics(
        y_true: List[int],
        y_pred: List[int],
        tier: str = "Emergency",
        beta: float = 2.0,
    ) -> ClinicalEvaluationMetrics:
        y_t = np.array(y_true)
        y_p = np.array(y_pred)

        tp = int(np.sum((y_t == 1) & (y_p == 1)))
        tn = int(np.sum((y_t == 0) & (y_p == 0)))
        fp = int(np.sum((y_t == 0) & (y_p == 1)))
        fn = int(np.sum((y_t == 1) & (y_p == 0)))

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        f1 = (2 * precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0

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