import datetime
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

def create_measurement_sr(
    source_dcm: Dataset,
    finding_name: str,
    measurement_val: float,
    unit_code: str = "mm",
    unit_meaning: str = "millimeter",
) -> Dataset:
    """
    Constructs a compliant DICOM Structured Report (TID 1500 subset)
    binding quantitative findings directly to the source image's UID hierarchy.
    """
    sr = Dataset()

    # 1. File Meta Information
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.88.22"  # Enhanced SR Storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    sr.file_meta = file_meta

    # 2. Inherit Patient & Study Context
    sr.PatientID = getattr(source_dcm, "PatientID", "UNKNOWN")
    sr.PatientName = getattr(source_dcm, "PatientName", "ANONYMOUS")
    sr.StudyInstanceUID = source_dcm.StudyInstanceUID
    sr.SeriesInstanceUID = generate_uid()
    sr.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    sr.SOPClassUID = file_meta.MediaStorageSOPClassUID

    # 3. Series / Instance Attributes
    sr.Modality = "SR"
    sr.SeriesNumber = 900
    sr.InstanceNumber = 1
    sr.ContentDate = datetime.date.today().strftime("%Y%m%d")
    sr.ContentTime = datetime.datetime.now().strftime("%H%M%S")

    # 4. Root Container Concept: Imaging Measurement Report (DCM 126000)
    sr.ValueType = "CONTAINER"
    sr.ContinuityOfContent = "SEPARATE"
    
    root_concept = Dataset()
    root_concept.CodeValue = "126000"
    root_concept.CodingSchemeDesignator = "DCM"
    root_concept.CodeMeaning = "Imaging Measurement Report"
    sr.ConceptNameCodeSequence = Sequence([root_concept])

    # 5. Numerical Content Item (The Measurement Payload)
    num_item = Dataset()
    num_item.RelationshipType = "CONTAINS"
    num_item.ValueType = "NUM"

    concept_name = Dataset()
    concept_name.CodeValue = "121206"
    concept_name.CodingSchemeDesignator = "DCM"
    concept_name.CodeMeaning = finding_name
    num_item.ConceptNameCodeSequence = Sequence([concept_name])

    meas_val = Dataset()
    meas_val.NumericValue = f"{measurement_val:.2f}"
    
    unit_ds = Dataset()
    unit_ds.CodeValue = unit_code
    unit_ds.CodingSchemeDesignator = "UCUM"
    unit_ds.CodeMeaning = unit_meaning
    meas_val.MeasurementUnitsCodeSequence = Sequence([unit_ds])

    num_item.MeasuredValueSequence = Sequence([meas_val])

    # Referenced Source SOP Instance (Direct Evidence Binding)
    ref_sop = Dataset()
    ref_sop.ReferencedSOPClassUID = getattr(source_dcm, "SOPClassUID", "1.2.840.10008.5.1.4.1.1.2")
    ref_sop.ReferencedSOPInstanceUID = source_dcm.SOPInstanceUID
    num_item.ContentSequence = Sequence([ref_sop])

    sr.ContentSequence = Sequence([num_item])

    # File format compliance
    # sr.is_little_endian = True
    # sr.is_implicit_VR = False

    return sr