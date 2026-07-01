# 🏥 Multi-Modality Clinical AI Triage Pipeline & Dashboard

An end-to-end, containerized clinical data pipeline designed for real-time PACS extraction, automated multi-modality AI triage simulation, and clinician-in-the-loop validation. 

This system bridges hospital imaging workflows with interactive, real-time analytics to prioritize critical anomalies (e.g., Pneumothorax, Hemorrhage) safely.

## 🏗️ Architecture Overview

The system is split into three decoupled microservices running inside an isolated Docker network:
1. **Orthanc PACS (`orthanc-pacs`)**: Production-grade DICOM server hosting image instances.
2. **Asynchronous File Listener (`triage-listener`)**: Python background daemon executing filesystem tracking.
3. **Streamlit UI Interface (`triage-dashboard`)**: A database-driven, live-updating dashboard featuring a 5-second asynchronous auto-polling engine.

## ⚡ Key Engineering Features

* **Multi-Container Orchestration**: Microservices communicate dynamically using internal Docker DNS bridges.
* **Persistent SQL State Management**: Replaced static memory tables with a structured SQLite database (`triage.db`) to handle case triage transitions natively (`PENDING` -> `CLEARED`).
* **Automated API Backfilling**: Integrated direct HTTP REST extraction with Orthanc to ingest metadata tags and inject telemetry payload states inline.
* **Clinician-in-the-Loop Action Keys**: Implemented unique dynamic column action loops to clear reviewed cases without state collision.
* **Ground-Truth Audit Exception Handlers**: Hardcoded data-integrity notice rules for specific mismatch audits (e.g., `PATIENT_005`).

## 🚀 Quick Start & Deployment

### 1. Launch the Stack Environment
Build the images from blueprint configurations and initialize the isolated network cluster:

```bash
docker compose down -v
docker compose up --build
```

### 2. Database Schema Initialization
In a separate terminal window, initialize your local storage tables:

```bash
python scripts/init_db.py
```

### 3. Stream Simulated Modality Studies
Simulate a rapid batch of 10 multi-modality DICOM files uploading to the PACS network:

```bash
python scripts/generate_test_dicoms.py
```

Open your browser to http://localhost:8501 to view live queue metrics and triage alerts seamlessly refreshing in real time.

## ⚖️ Intellectual Property, Governance & Compliance

* **Synthetic Data Safeguards**: No real patient health information (PHI) or identifiable clinical data is utilized within this repository. 
* **Regulatory Compliance**: All DICOM instances used for simulation are entirely synthetic and procedurally manufactured inline, satisfying **HIPAA Safe Harbor** methods and **GDPR** anonymization principles for software development and demonstration.
* **Ethics & Security**: By leveraging isolated container networks and decoupled mock environments, this architecture demonstrates how clinical AI orchestration models can be stress-tested without breaching hospital data-sharing agreements or touching live production environments.

Developer: Adedamola Domain Focus: Clinical Data Orchestration, Imaging Middleware & Interoperable Healthcare Systems