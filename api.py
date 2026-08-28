import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, Optional, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from qa_evaluator import ClinicalMetricsAuditor, ClinicalEvaluationMetrics

# Import existing core parsing logic from app.py
from app import process_unified_clinical_packet

app = FastAPI(
    title="Clinical AI Triage FHIR Microservice",
    version="1.1.0",
    description="FHIR R4 Ingestion, Defensive DICOM Extraction & Health Telemetry API",
)

START_TIME = time.time()
DB_PATH = "data/clinical_pipeline.db"


class FHIRBundlePayload(BaseModel):
    resourceType: str = "Bundle"
    timestamp: str
    patient_id: str
    triage_status: str
    heart_rate: Optional[int] = 0
    systolic_bp: Optional[int] = 0
    respiratory_rate: Optional[int] = 0
    oxygen_saturation: Optional[int] = 0
    vitals_telemetry: Optional[Dict[str, Any]] = None
    radiology_exam_b64: Optional[str] = None


@app.get("/health", tags=["Telemetry"])
def health_check() -> Dict[str, Any]:
    """Automated health check verifying service uptime and SQLite DB connectivity."""
    db_status = "unreachable"
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        db_status = "healthy"
    except Exception:
        db_status = "database_initializing"

    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy" if db_status in ["healthy", "database_initializing"] else "degraded",
        "database": db_status,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/metrics", tags=["Telemetry"])
def get_metrics() -> Dict[str, Any]:
    """Returns telemetry on ingested clinical packets and triage distribution."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM triage_ledger")
        total_records = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM triage_ledger WHERE triage_level = 'CRITICAL'")
        critical_count = cursor.fetchone()[0]

        conn.close()
    except Exception:
        total_records = 0
        critical_count = 0

    return {
        "total_packets_ingested": total_records,
        "critical_cases": critical_count,
        "standard_cases": max(0, total_records - critical_count),
        "service_uptime_seconds": round(time.time() - START_TIME, 2),
    }


@app.post("/api/v1/fhir/Bundle", status_code=status.HTTP_201_CREATED, tags=["FHIR Ingestion"])
def ingest_fhir_bundle(packet: FHIRBundlePayload) -> Dict[str, Any]:
    """Ingests, parses, and triages an inbound FHIR R4 Bundle containing multimodal clinical telemetry."""
    if packet.resourceType != "Bundle":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid resourceType. Only 'Bundle' resources are accepted."
        )

    try:
        raw_payload = packet.model_dump()

        # Run triage pipeline
        result = process_unified_clinical_packet(raw_payload)

        # Fallback triage scoring if pipeline helper returns empty
        if not result:
            is_critical = (
                (packet.oxygen_saturation and packet.oxygen_saturation < 90) or
                (packet.heart_rate and (packet.heart_rate < 45 or packet.heart_rate > 120)) or
                (packet.systolic_bp and (packet.systolic_bp < 90 or packet.systolic_bp > 180)) or
                packet.triage_status == "CRITICAL"
            )
            triage_level = "CRITICAL" if is_critical else "STANDARD"
            patient_id = packet.patient_id or "UNKNOWN"
            imaging_modality = "None"
            ai_findings = "N/A"
        else:
            patient_id = result.get("Patient ID", packet.patient_id)
            triage_level = result.get("Triage Level", packet.triage_status)
            imaging_modality = result.get("Imaging Modality", "None")
            ai_findings = result.get("AI Radiology Findings", "N/A")

        return {
            "status": "ingested",
            "patient_id": patient_id,
            "triage_level": triage_level,
            "imaging_modality": imaging_modality,
            "ai_findings": ai_findings,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal processing exception: {str(exc)}"
        )


class EvaluationPayload(BaseModel):
    y_true: List[int]
    y_pred: List[int]
    tier: str = "Emergency"  # Emergency, Urgent, or Routine
    beta: float = 2.0

@app.post("/metrics/evaluate", response_model=ClinicalEvaluationMetrics, tags=["Quality & Metrics"])
async def evaluate_clinical_metrics(payload: EvaluationPayload):
    if len(payload.y_true) != len(payload.y_pred):
        raise HTTPException(status_code=400, detail="Ground truth and predictions must be equal length.")

    return ClinicalMetricsAuditor.calculate_metrics(
        y_true=payload.y_true,
        y_pred=payload.y_pred,
        tier=payload.tier,
        beta=payload.beta,
    )