# End-to-End Clinical PACS Integration & AI Triage Pipeline

## 📌 Project Overview
This project demonstrates an end-to-end clinical data integration architecture designed to bridge the gap between hospital imaging repositories and frontline clinical software. 

The pipeline programmatically queries a local Orthanc PACS server via a REST API, extracts study parameters while filtering out Protected Health Information (PHI) to maintain strict data governance, orchestrates an AI triage JSON payload, and formats the downstream data loop into an actionable, filtered "Red Alert" emergency workflow dashboard built for clinicians.

---

## 🛠️ System Architecture



The data orchestration moves seamlessly across the following architecture layers:
1. **Imaging Infrastructure (PACS):** Local Orthanc instance simulating a standard clinical imaging archive managing DICOM studies.
2. **Data Orchestration Layer (Python):** Custom script handles automated connection testing, REST endpoints interrogation, data anonymization, and diagnostic payload formatting.
3. **Frontend Presentation Layer (Glide UX):** A responsive tracking board interface utilizing server-side data filters to isolate and elevate acute medical findings (`triage_status == URGENT`) directly to the clinical team's primary workspace.

---

## 📂 Repository Structure
* `/scripts/list_patients.py`: Initial diagnostic script verifying stable authentication and integration with local PACS REST pipelines.
* `/scripts/ai_triage.py`: Core logic file handling server queries, data-stripping rules, and JSON payload formatting.
* `/scripts/ai_csv_generator.py`: Custom batch-processing script engineered to format diagnostic outputs into a standardized CSV schema, providing a free, local data-bridge alternative for downstream visualization.
* `/data/clinical_triage_report.csv`: Sample clinical data export representing completed backend pipeline outcomes ready for application synchronization.

---

## 🚀 Technical Highlights & Core Competencies
* **REST API Architecture:** Mastery of Python `requests` patterns to manage network authorization, process status code boundaries, and clean incoming raw responses.
* **Clinical Data Governance:** Implemented strict proxy data handling by isolating `PatientID` attributes and intentionally omitting sensitive patient identity data flags to mimic healthcare privacy standards.
* **Low-Code Integration & UX Design:** Architected an optimized user experience by mapping complex data contracts into clean UI card elements, building real-time data visual hierarchies (e.g., color-coded urgency tags) for emergency room operations.