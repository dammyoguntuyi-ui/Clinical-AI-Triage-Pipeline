# Multi-Modality Clinical AI Triage Pipeline & Safety Auditor

An interoperable, end-to-end medical imaging data orchestration pipeline that ingests DICOM studies from a local PACS server, dynamically routes cases across multi-modality AI models based on metadata evaluation, and acts as an automated clinical safety gatekeeper by auditing discrepancies against expert human ground truth.

## 🏗️ Architecture Overview

The system establishes a robust middleware framework bridging clinical infrastructure, data governance, and analytics interfaces:

* **Infrastructure Layer:** An Orthanc PACS container serving local instances of multi-modality DICOM medical images.
* **Data Orchestration Middleware (`ai_csv_generator.py`):** Navigates the complex DICOM data hierarchy down to the Study/Series level via RESTful API queries to extract data, strip sensitive PHI fields, and dynamically evaluate the `Modality` tag.
* **AI Routing Engine:** Mimics multi-modality diagnostic tools by dynamically triaging cases (`CR`, `CT`, `MR`, `US`) into target streams, assigning specialized abnormality findings, and building a secure data payload (`clinical_triage_report.csv`).
* **Clinical Safety Layer (`validate_ai.py`):** Audits real-time pipeline predictions against an expert human baseline. Calculates system accuracy, maps operational error rates, and generates critical clinical discrepancy warnings.
* **Visualization Layer (Glide):** A live mobile/web tracking interface with data-driven conditional visibility rules that dynamically maps diagnostic findings and flags unaligned or missed high-risk diagnoses with stark warning badges.

---

## 🛠️ Tech Stack & Protocols

* **Medical Imaging Protocol:** DICOM (Digital Imaging and Communications in Medicine)
* **PACS Node:** Orthanc server architecture
* **Data Layer / Language:** Python 3 (Libraries: `pydicom`, `requests`, `numpy`, `csv`)
* **Frontend Analytics:** Glide Engine (Low-Code Data Mapping & Cloud Synchronization)

---

## 🚀 Deployment & Sandbox Execution

### 1. Initialize & Populate the PACS Node
Generate an explicit VR little endian multi-modality test batch containing distinct diagnostic imaging sequences (Chest X-Rays, Brain CT, Abdominal Ultrasound, Spine MRI) and upload them to the Orthanc instance:
```bash
python scripts/generate_test_dicoms.py