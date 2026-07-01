import os
import datetime
import numpy as np
import random
import subprocess
import requests
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
import random  # 🌟 Added at the top of your execution block

# --- RANDOM COHORT CONFIGURATION ---
output_dir = "./test_images"
os.makedirs(output_dir, exist_ok=True)

# Pools of clinical dummy data
first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "David", "Eva", "Frank", "Grace", "Henry", "Amara", "Tariq"]
last_names = ["Doe", "Smith", "Jones", "Brown", "Green", "Wright", "Martinez", "Miller", "Taylor", "Clark", "Okonkwo", "Al-Sayed"]
modalities = ["CR", "CT", "MR", "US"]

modality_details = {
    "CR": ["Chest X-Ray Left PA", "Chest X-Ray Lateral", "Hand X-Ray 3-Views"],
    "CT": ["Brain CT Unenhanced", "Abdomen/Pelvis CT Contrast", "Chest CT High-Res"],
    "MR": ["Spine Lumbar MR", "Brain MRI Stroke Protocol", "Knee MR Left Non-Contrast"],
    "US": ["Abdomen Ultrasound", "Pelvis Ultrasound", "Carotid Doppler Ultrasound"]
}

# 🌟 CONFIGURE BATCH SIZE HERE: Change this number to generate 10, 50, or 100 patients instantly!
batch_size = 10 
test_cases = []

print(f"🎲 Rolling dice to manufacture {batch_size} randomized clinical records...")

for i in range(1, batch_size + 1):
    p_id = f"PATIENT_{i:03d}"  # Generates PATIENT_001, PATIENT_002, etc.
    p_name = f"{random.choice(last_names)}, {random.choice(first_names)}" # Random name mix
    mod = random.choice(modalities) # Random modality selection
    desc = random.choice(modality_details[mod]) # Selects matching description
    
    test_cases.append((p_id, p_name, desc, mod))

# --- EXECUTION LOOP ---
print("🏭 Manufacturing randomized multi-modality files...")
for p_id, p_name, desc, mod in test_cases:
    file_path = os.path.join(output_dir, f"{p_id}.dcm")
    create_dummy_dicom(file_path, p_id, p_name, desc, mod)
    
    # 🚀 NEW: Read the newly created local file and push it directly to Orthanc PACS
    try:
        with open(file_path, "rb") as dicom_file:
            # Pushing the binary payload directly to Orthanc's native instance ingestion endpoint
            response = requests.post("http://localhost:8042/instances", data=dicom_file.read(), auth=('orthanc', 'orthanc'))
            if response.status_code == 200 or response.status_code == 201:
                print(f"📡 Successfully uploaded {p_id} to Orthanc PACS.")
            else:
                print(f"⚠️ Orthanc rejected {p_id}. Status code: {response.status_code}")
    except Exception as upload_err:
        print(f"❌ Failed to connect or upload to Orthanc server: {upload_err}")

print("✨ Success! 10 completely unique DICOM files generated and uploaded.")