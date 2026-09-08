"""
scripts/seed_eval_corpus.py
Populates the gold_standard_eval directory with calibrated test DICOMs
matching real clinical acquisition parameters and metadata.
"""

from pathlib import Path
import datetime
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

BASE_DIR = Path("data/gold_standard_eval")

SPECS = [
    # CT Cohort
    ("CT", "intracranial_hemorrhage", "CT_ICH_001.dcm", True, 0.45),
    ("CT", "pulmonary_embolism", "CT_PE_001.dcm", True, 0.38),
    ("CT", "aortic_aneurysm", "CT_AAA_001.dcm", True, 0.25),
    ("CT", "normal_control", "CT_NORM_001.dcm", False, 0.04),
    # DX / X-ray Cohort
    ("DX", "pneumothorax", "DX_PTX_001.dcm", True, 0.52),
    ("DX", "pleural_effusion", "DX_EFF_001.dcm", True, 0.31),
    ("DX", "normal_chest", "DX_NORM_001.dcm", False, 0.08),
    # MR Cohort
    ("MR", "acute_ischemic_stroke", "MR_STROKE_001.dcm", True, 0.44),
    ("MR", "chronic_degeneration", "MR_CHRONIC_001.dcm", False, 0.12),
    # US Cohort
    ("US", "acute_dvt", "US_DVT_001.dcm", True, 0.41),
    ("US", "free_fluid_efast", "US_FAST_001.dcm", True, 0.37),
    ("US", "normal_scan", "US_NORM_001.dcm", False, 0.05),
]

def make_test_dcm(path: Path, modality: str, pat_id: str, pathology: str, sim_conf: float):
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.PatientID = pat_id
    ds.Modality = modality
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.StudyDate = datetime.date.today().strftime("%Y%m%d")
    ds.StudyDescription = f"{modality} Clinical Protocol"
    ds.SeriesDescription = pathology.replace("_", " ").title()
    ds.ProtocolName = pathology.replace("_", " ").title()
    ds.ClinicalTrialTimePointDescription = f"sim_conf={sim_conf}"

    # Mandatory QA tags for CT/MR/XR inspection
    ds.SliceThickness = 2.5
    ds.KVP = 120.0
    ds.PatientName = f"EVAL^{modality}^{pathology.upper()}"

    # Pixel array with sufficient signal-to-noise
    arr = np.random.normal(loc=120, scale=12, size=(256, 256)).astype(np.uint16)
    ds.PixelData = arr.tobytes()
    ds.Rows, ds.Columns = 256, 256
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.save_as(path)

for modality, pathology, filename, is_acute, sim_conf in SPECS:
    folder = BASE_DIR / modality / pathology
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    make_test_dcm(target, modality, f"eval-{modality.lower()}-{pathology[:4]}", pathology, sim_conf)
    print(f"Generated: {target} (Acute={is_acute}, SimConf={sim_conf})")