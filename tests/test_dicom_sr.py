import pytest
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
from src.dicom_sr import create_measurement_sr

@pytest.fixture
def mock_source_dcm():
    ds = Dataset()
    ds.PatientID = "PAT_TEST_001"
    ds.PatientName = "DOE^JANE"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = generate_uid()
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
    return ds

def test_dicom_sr_generation(mock_source_dcm):
    sr = create_measurement_sr(
        source_dcm=mock_source_dcm,
        finding_name="Maximum Long-Axis Nodule Diameter",
        measurement_val=15.42
    )

    # Validate Core Identification & UIDs
    assert sr.Modality == "SR"
    assert sr.SOPClassUID == "1.2.840.10008.5.1.4.1.1.88.22"
    assert sr.StudyInstanceUID == mock_source_dcm.StudyInstanceUID
    assert sr.ValueType == "CONTAINER"

    # Validate Root Container
    assert sr.ConceptNameCodeSequence[0].CodeValue == "126000"

    # Validate Measurement Payload
    meas = sr.ContentSequence[0]
    assert meas.ValueType == "NUM"
    assert meas.ConceptNameCodeSequence[0].CodeMeaning == "Maximum Long-Axis Nodule Diameter"
    assert meas.MeasuredValueSequence[0].NumericValue == "15.42"
    assert meas.MeasuredValueSequence[0].MeasurementUnitsCodeSequence[0].CodeValue == "mm"

    # Validate Evidence Binding to Parent Image
    ref_evidence = meas.ContentSequence[0]
    assert ref_evidence.ReferencedSOPInstanceUID == mock_source_dcm.SOPInstanceUID