"""
api.py - FastAPI Enterprise Ingestion Gateway & Triage Microservice
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage
import numpy as np

from enterprise_engine import EnterpriseHospitalEngine
from qa_evaluator import ImageQualityEvaluator

app = FastAPI(
    title="Clinical AI Triage Gateway",
    description="Enterprise DICOM QA Gating and HL7 FHIR R4 Ingestion Microservice",
    version="2.0.0",
)

engine = EnterpriseHospitalEngine()


class StudyPayload(BaseModel):
    patient_id: str
    modality: str = "CT"
    slice_thickness: Optional[float] = 1.0
    spo2: float = 98.0


@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Clinical AI Triage Gateway",
        "version": "2.0.0",
    }


@app.post("/triage/study")
def triage_study(payload: StudyPayload):
    """Synthetic gateway endpoint to audit and triage incoming studies."""
    try:
        # Generate in-memory dataset to evaluate
        img = np.random.randint(100, 200, size=(64, 64), dtype=np.uint16)
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
        file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.8.498.88"
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        ds = Dataset()
        ds.file_meta = file_meta
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        ds.Modality = payload.modality
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PatientID = payload.patient_id
        ds.Rows, ds.Columns = 64, 64
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        if payload.slice_thickness is not None:
            ds.SliceThickness = payload.slice_thickness
        ds.PixelData = img.tobytes()

        vitals = {"spo2": payload.spo2, "patient_id": payload.patient_id}
        result = engine.process_clinical_study(ds, vitals)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))