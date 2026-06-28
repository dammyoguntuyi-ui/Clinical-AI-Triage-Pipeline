import os
import datetime
import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

def create_dummy_dicom(filename, patient_id, patient_name, study_description, modality):
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 222
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = '1.2.3.4.5.6.7.8.9'

    ds = FileDataset(filename, {}, file_meta=file_meta)

    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = '19800101'
    ds.PatientSex = 'O'
    ds.StudyDescription = study_description
    ds.StudyDate = datetime.date.today().strftime('%Y%m%d')
    ds.SeriesDate = datetime.date.today().strftime('%Y%m%d')
    ds.ContentDate = datetime.date.today().strftime('%Y%m%d')
    ds.StudyTime = '120000'
    ds.SeriesTime = '120000'
    ds.ContentTime = '120000'
    ds.Modality = modality  # 🌟 Dynamic assignment!
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    pixel_array = np.zeros((512, 512), dtype=np.uint8)
    pixel_array[50:462, 50:462] = 128
    
    ds.Rows = pixel_array.shape[0]
    ds.Columns = pixel_array.shape[1]
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = pixel_array.tobytes()

    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(filename, write_like_original=False)
    print(f"📦 Manufactured dynamic {modality} DICOM: {filename}")

# --- EXECUTION LOOP ---
output_dir = "./test_images"
os.makedirs(output_dir, exist_ok=True)

test_cases = [
    ("PATIENT_001", "John Doe", "Chest X-Ray Left PA", "CR"),
    ("PATIENT_002", "Jane Smith", "Chest X-Ray Frontal PA", "CR"),
    ("PATIENT_003", "Bob Jones", "Brain CT Brain Unenhanced", "CT"),
    ("PATIENT_004", "Alice Brown", "Abdomen Ultrasound", "US"),
    ("PATIENT_005", "Charlie Green", "Spine Lumbar MR", "MR")
]

print("🚀 Re-starting bulk multi-modality generation...")
for p_id, p_name, desc, mod in test_cases:
    file_path = os.path.join(output_dir, f"{p_id}.dcm")
    create_dummy_dicom(file_path, p_id, p_name, desc, mod)

print(f"\n🎉 Success! 5 multi-modality files generated.")