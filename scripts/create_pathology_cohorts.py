import datetime
from pathlib import Path
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

BASE_DIR = Path("data/eval_cohorts")

COHORTS = [
    {
        "folder": "intracranial_hemorrhage/CT_axial_ncct",
        "modality": "CT",
        "desc": "CT Head Non-Contrast - Acute Intracranial Hemorrhage",
        "sop_class": "1.2.840.10008.5.1.4.1.1.2",
        "base_hu": 1050,  # Hyperdense acute blood simulation
    },
    {
        "folder": "intracranial_hemorrhage/MR_gradient_echo_swi",
        "modality": "MR",
        "desc": "MR Brain T2* SWI - Microhemorrhage Bloom",
        "sop_class": "1.2.840.10008.5.1.4.1.1.4",
        "base_hu": 600,
    },
    {
        "folder": "pneumothorax/DX_erect_pa",
        "modality": "DX",
        "desc": "Chest PA - Tension Pneumothorax with Mediastinal Shift",
        "sop_class": "1.2.840.10008.5.1.4.1.1.1",
        "base_hu": 2100,
    },
    {
        "folder": "pneumothorax/DX_supine_ap",
        "modality": "DX",
        "desc": "Chest AP Portable - Deep Sulcus Sign Pneumothorax",
        "sop_class": "1.2.840.10008.5.1.4.1.1.1",
        "base_hu": 1950,
    },
    {
        "folder": "aortic_aneurysm_dissection/CT_angio_chest_abdo",
        "modality": "CT",
        "desc": "CTA Thoracic/Abdominal Aorta - Type A Dissection Flap",
        "sop_class": "1.2.840.10008.5.1.4.1.1.2",
        "base_hu": 1300,
    },
    {
        "folder": "aortic_aneurysm_dissection/US_abdominal_aorta",
        "modality": "US",
        "desc": "US Abdominal Aorta - Ectatic 5.5cm Fusiform Aneurysm",
        "sop_class": "1.2.840.10008.5.1.4.1.1.6.1",
        "base_hu": 800,
    },
    {
        "folder": "confirmed_normals/CT_head_normal",
        "modality": "CT",
        "desc": "CT Head - Unremarkable Non-Contrast",
        "sop_class": "1.2.840.10008.5.1.4.1.1.2",
        "base_hu": 1000,
    },
    {
        "folder": "confirmed_normals/DX_chest_normal",
        "modality": "DX",
        "desc": "Chest Radiograph PA - Clear Lung Fields",
        "sop_class": "1.2.840.10008.5.1.4.1.1.1",
        "base_hu": 2000,
    },
]

def make_sample_dicom(dest_path: Path, modality: str, study_desc: str, sop_class_uid: str, patient_num: int, base_val: int):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = sop_class_uid
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta

    # Patient Context
    cohort_tag = dest_path.parent.name
    ds.PatientID = f"COHORT-{modality}-{patient_num:03d}"
    ds.PatientName = f"CASE^{cohort_tag}_{patient_num:02d}"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = sop_class_uid
    ds.Modality = modality
    ds.StudyDescription = study_desc
    ds.SeriesDescription = f"{study_desc} [Synthetic Cohort]"

    # Temporal Metadata
    now = datetime.datetime.now(datetime.timezone.utc)
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.ContentDate = ds.StudyDate
    ds.ContentTime = ds.StudyTime

    # Image Geometry & Tag Compliance
    rows, cols = 512, 512
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"

    # Mandatory Clinical Geometry Headers for QA Gate
    if modality in ["CT", "MR"]:
        ds.SliceThickness = "1.0"           # Sub-millimeter slice for CT/CTA
        ds.PixelSpacing = ["0.75", "0.75"]  # Spatial resolution in mm
        ds.ImagePositionPatient = ["0.0", "0.0", f"{patient_num * 1.0}"]
        ds.ImageOrientationPatient = ["1.0", "0.0", "0.0", "0.0", "1.0", "0.0"]
        if modality == "CT":
            ds.KVP = "120"
    elif modality in ["DX", "CR"]:
        ds.ImagerPixelSpacing = ["0.14", "0.14"]
        ds.ViewPosition = "PA"
    
    # Rescale tags for Hounsfield Units / Pixel Scaling
    ds.RescaleIntercept = "0"
    ds.RescaleSlope = "1"
    
    # Calibrated Synthetic Pixel Array with clinical noise floor
    noise = np.random.normal(0, 25, (rows, cols))
    pixels = np.clip(base_val + noise, 0, 4095).astype(np.uint16)
    ds.PixelData = pixels.tobytes()

    ds.save_as(str(dest_path), write_like_original=False)

def build_all_cohorts():
    total_created = 0
    for cohort in COHORTS:
        folder_path = BASE_DIR / cohort["folder"]
        for i in range(1, 4):  # Creates 3 distinct patient studies per cohort
            file_name = folder_path / f"study_{i:02d}.dcm"
            make_sample_dicom(
                dest_path=file_name,
                modality=cohort["modality"],
                study_desc=cohort["desc"],
                sop_class_uid=cohort["sop_class"],
                patient_num=i,
                base_val=cohort["base_hu"]
            )
            total_created += 1
            print(f"Generated -> {file_name}")

    print(f"\nSuccessfully generated {total_created} calibrated DICOM studies under {BASE_DIR.resolve()}")

if __name__ == "__main__":
    build_all_cohorts()