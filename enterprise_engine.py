"""
enterprise_engine.py - Automated End-to-End Hospital Ingestion, QA Gating, and FHIR Dispatch
"""

from typing import Dict, Any
import datetime
import pydicom
from qa_evaluator import ImageQualityEvaluator, QAEvaluationResult


class EnterpriseHospitalEngine:
    def __init__(self):
        self.qa_evaluator = ImageQualityEvaluator()

    def process_clinical_study(self, dcm: pydicom.Dataset, patient_vitals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full enterprise clinical pipeline:
        1. Pre-Inference QA & Header Audit
        2. Routing / Quarantine
        3. Multimodal Context Synthesis
        4. FHIR R4 DiagnosticReport Generation
        """
        qa_result: QAEvaluationResult = self.qa_evaluator.evaluate_dicom(dcm)
        patient_id = str(getattr(dcm, "PatientID", patient_vitals.get("patient_id", "pat-UNKNOWN")))
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Scenario A: Gating Failure -> PACS Dead-Letter Quarantine
        if not qa_result.is_valid:
            quarantine_event = {
                "timestamp": timestamp,
                "status": "QUARANTINED",
                "patient_id": patient_id,
                "modality": qa_result.modality,
                "rejection_reasons": ", ".join(qa_result.rejection_reasons),
                "snr_db": qa_result.snr_db,
                "cnr": qa_result.cnr,
                "hl7_error_code": "ERR_DICOM_QA_VIOLATION",
            }
            return {"outcome": "QUARANTINED", "payload": quarantine_event, "qa_result": qa_result}

        # Scenario B: QA Passed -> Multimodal Triage Synthesis & FHIR Dispatch
        urgency_tier = self._determine_urgency(patient_vitals, qa_result)
        fhir_report = self._generate_fhir_diagnostic_report(
            patient_id, qa_result, patient_vitals, urgency_tier, timestamp
        )

        dispatched_event = {
            "timestamp": timestamp,
            "status": "DISPATCHED",
            "patient_id": patient_id,
            "modality": qa_result.modality,
            "urgency_tier": urgency_tier,
            "fhir_payload": fhir_report,
            "snr_db": qa_result.snr_db,
            "cnr": qa_result.cnr,
        }
        return {"outcome": "DISPATCHED", "payload": dispatched_event, "qa_result": qa_result}

    def _determine_urgency(self, vitals: Dict[str, Any], qa: QAEvaluationResult) -> str:
        """Synthesizes clinical vitals and imaging study context."""
        spo2 = vitals.get("spo2", 98)
        if spo2 < 85 or (qa.modality in ["CT", "MR"] and qa.slice_thickness_mm and qa.slice_thickness_mm <= 1.0):
            return "Emergency"
        elif spo2 < 92:
            return "Urgent"
        return "Routine"

    def _generate_fhir_diagnostic_report(
        self, patient_id: str, qa: QAEvaluationResult, vitals: Dict[str, Any], tier: str, timestamp: str
    ) -> Dict[str, Any]:
        """Generates standard HL7 FHIR R4 DiagnosticReport resource."""
        return {
            "resourceType": "DiagnosticReport",
            "id": f"diag-rep-{patient_id}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": "RAD",
                            "display": "Radiology",
                        }
                    ]
                }
            ],
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": timestamp,
            "conclusion": f"AI Clinical Triage Tier: {tier.upper()}. Quality Gate Verified (Modality: {qa.modality}, SNR: {qa.snr_db} dB, CNR: {qa.cnr}).",
            "extension": [
                {
                    "url": "http://hospital.org/fhir/StructureDefinition/clinical-urgency",
                    "valueString": tier,
                },
                {
                    "url": "http://hospital.org/fhir/StructureDefinition/bedside-spo2",
                    "valueDecimal": float(vitals.get("spo2", 98.0)),
                },
                {
                    "url": "http://hospital.org/fhir/StructureDefinition/qa-validation-passed",
                    "valueBoolean": True,
                },
            ],
        }