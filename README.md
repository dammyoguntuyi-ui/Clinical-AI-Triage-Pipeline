# Multi-Modality Clinical AI Triage Ingestion Pipeline

An end-to-end, containerized microservice pipeline engineered to simulate real-time hospital PACS data extraction, asynchronous tracking, and interactive clinical triage prioritization.

## 🏗️ System Architecture & Service Mesh
The ecosystem is completely decoupled into three independent microservices orchestrated via a virtual Docker network mesh using internal container-to-container DNS hostname routing:

1. **`orthanc-pacs`**: An open-source PACS server node acting as the centralized imaging repository running native DICOM REST endpoints.
2. **`triage-listener`**: An asynchronous Python background daemon tracking filesystem ingestion loops and extracting header metadata.
3. **`triage-dashboard`**: A real-time Streamlit analytics web app acting as the clinician-in-the-loop review interface.

## 🚀 Key Engineering Features
* **Persistent State Machine**: Migrated from an unstable, stateless file-watching setup to a centralized **SQLite database matrix**. State mutations (`PENDING` ➔ `CLEARED`) utilize atomic transaction keys via UI action buttons to prevent multi-container race conditions.
* **REST Data Ingestion**: Re-engineered UI data synchronization by dropping filesystem dependencies and utilizing asynchronous HTTP REST API requests directly to the Orthanc PACS server.
* **Regulatory Compliance**: Built around 100% synthetic patient DICOM files to guarantee complete data privacy, explicitly adhering to **HIPAA Safe Harbor** methods and **GDPR** anonymization principles.

## 🛠️ Tech Stack & Requirements
* **Language:** Python 3.11+ (Streamlit, Pydicom, Requests)
* **Infrastructure:** Docker, Docker Compose
* **Database:** SQLite 3

## ⚡ Quick Start (Local Deployment)
To spin up the entire isolated network infrastructure locally, clone this repository and execute:

```bash
# Initialize a pristine database instance
python scripts/init_db.py

# Build and launch the containerized cluster
docker compose up --build
```

The dashboard will instantly spin up and auto-poll the pipeline state live at http://localhost:8501.

Developer: Adedamola Domain Focus: Clinical Data Orchestration, Imaging Middleware & Interoperable Healthcare Systems