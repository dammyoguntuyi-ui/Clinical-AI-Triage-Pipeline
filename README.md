# Multi-Modality Clinical AI Triage Pipeline & Safety Auditor

An interoperable, end-to-end medical imaging data orchestration pipeline that ingests DICOM studies from a local PACS server, dynamically routes cases across multi-modality AI models based on metadata evaluation, and acts as an automated clinical safety gatekeeper by auditing discrepancies against expert human ground truth.

## 🏗️ Architecture Overview

The system establishes a robust middleware framework bridging clinical infrastructure, data governance, and analytics interfaces:

* **Infrastructure Layer:** An Orthanc PACS container serving local instances of multi-modality DICOM medical images.
* **Data Orchestration Middleware (`ai_csv_generator.py`):** Navigates the complex DICOM data hierarchy down to the Study/Series level via RESTful API queries to extract data, strip sensitive PHI fields, and dynamically evaluate the `Modality` tag.
* **AI Routing Engine:** Mimics multi-modality diagnostic tools by dynamically triaging cases (`CR`, `CT`, `MR`, `US`) into target streams, assigning specialized abnormality findings, and building a secure data payload (`clinical_triage_report.csv`).
* **Clinical Safety Layer (`validate_ai.py`):** Audits real-time pipeline predictions using dynamic, rules-based validation. Calculates system accuracy, maps operational error rates, and isolates clinical discrepancy warnings across variable cohort sizes.
* **Visualization Layer (Glide):** A live mobile/web tracking interface with data-driven conditional visibility rules that dynamically maps diagnostic findings and flags unaligned or missed high-risk diagnoses with stark warning badges.

---

## 🛠️ Tech Stack & Protocols

* **Medical Imaging Protocol:** DICOM (Digital Imaging and Communications in Medicine)
* **PACS Node:** Orthanc server architecture
* **Data Layer / Language:** Python 3 (Libraries: `pydicom`, `requests`, `numpy`, `csv`, `random`)
* **Frontend Analytics:** Glide Engine (Low-Code Data Mapping & Cloud Synchronization)

---

## 🚀 Deployment & Sandbox Execution

### 1. Initialize & Populate the PACS Node (Randomized Simulation)
Generate a completely randomized, scale-configurable test batch of explicit VR little endian DICOM files across multiple imaging sequences (Chest X-Rays, Brain CTs, Abdominal Ultrasounds, Spine MRIs) to simulate realistic variable hospital intake:
```bash
python scripts/generate_test_dicoms.py

Upload the freshly manufactured .dcm cohort folder into http://localhost:8042/app/explorer.html#upload.

---

### 2. Run the Data Orchestration Engine
Extract metadata fields from the root PACS API, dynamically query the study level to parse modality attributes, and resolve routing schemas:

```bash
python scripts/ai_csv_generator.py

---

### 3. Execute the Dynamic Clinical Safety Audit
Intercept the output payload and evaluate system routing accuracy and discrepancy rates on the fly:

```bash
python scripts/validate_ai.py

---

## 📊 Live Simulation Metrics & Edge-Case Trapping

The safety framework is stress-tested using a dynamic validator that tracks performance across scaling workloads while successfully isolating targeted clinical blind spots (such as under-called critical spinal masses).

---

### Example Output Log (10-Patient Randomized Batch):

```Plaintext
🩺 Starting Dynamic Multi-Modality Validation Audit...
---------------------------------------------------------------------------
✅ PATIENT_001 (US): Pipeline routing verified successfully.
✅ PATIENT_002 (CT): Pipeline routing verified successfully.
✅ PATIENT_003 (US): Pipeline routing verified successfully.
✅ PATIENT_004 (CT): Pipeline routing verified successfully.
⚠️  PATIENT_005 (MR): MISMATCH DETECTED (Simulated Audit Target)
...
✅ PATIENT_010 (MR): Pipeline routing verified successfully.
---------------------------------------------------------------------------
📊 CLINICAL PERFORMANCE METRICS SUMMARY
---------------------------------------------------------------------------
🔹 Total Audited Multi-Modality Cases : 10
🔹 Successful AI Alignments          : 9
🔹 System Accuracy Rate              : 90.0%
🔹 Overall AI Error Rate              : 10.0%
---------------------------------------------------------------------------

🚨 DETAILED CLINICAL DISCREPANCY REPORT:
• Patient ID: PATIENT_005 [MR]
  Current Model: Spine-Decompression-v1
  Issue:         AI model under-called a CRITICAL Malignant Mass as standard spinal stenosis.

---

## 🛡️ Intellectual Property, Governance & Compliance

Data Privacy (HIPAA/GDPR Alignment): The custom Python routing framework isolates PACS internal instance handles from operational worklists, creating anonymized clinical_mrn hooks to eliminate the accidental spread of Protected Health Information (PHI).

IP Defense: This technical framework is legally stamped under the author's jurisdiction. The dynamic method of cross-level REST tag resolution to validate third-party diagnostic algorithms establishes documented "Prior Art" on this repository.

Developer: Adedamola
Domain Focus: Clinical Data Orchestration, Imaging Middleware & Interoperable Healthcare Systems
