# 🏥 Enterprise Clinical AI Triage Pipeline

An asynchronous, containerized data architecture that simulates real-time hospital ingestion, dataset reconciliation, and automated clinical triage. This pipeline highlights the bridge between frontline healthcare workflows (Radiography/PACS) and production-grade health-tech engineering.

---

## 🏗️ System Architecture

The pipeline runs entirely inside an isolated, multi-container environment orchestrated via Docker Compose:

1. **Ingestion Tier (`streamer` container):** Simulates an Electronic Medical Record (EMR) telemetry feed, generating schema-validated healthcare metrics (heart rates) using the international **HL7 FHIR standard** (via Pydantic).
2. **Reconciliation Tier (`dashboard` container):** A Streamlit analytical dashboard that pulls live telemetries and runs a strict folder-polling engine to cross-reference patient MRNs against local PACS/modality assets.
3. **AI Inference Tier:** Triggers automatically upon successful patient data reconciliation, routing the synchronized datasets to a mockup deep-learning diagnostic classifier (`ClinicalResNet-v4.2-Native`).

---

## 🛠️ Technology Stack

* **Language Environment:** Python 3.11-slim
* **Healthcare Interoperability:** HL7 FHIR (`fhir.resources` Pydantic models)
* **Frontend Web Canvas:** Streamlit (Dynamic Auto-Refresh UI)
* **Infrastructure Orchestration:** Docker & Docker Compose
* **Data Processing Management:** File-system I/O volumes, Queue Flushing mechanisms

---

## 📂 Repository Structure

```text
CLINICAL-AI-TRIAGE-PIPELINE/
├── data/                    # Local PACS Storage Repository (DICOM / Assets)
├── scripts/
│   └── mock_streamer.py     # Background FHIR simulation engine
├── streaming_intake/        # Shared Docker volume buffer queue
├── app.py                   # Main pipeline interface & reconciliation engine
├── Dockerfile               # Linux blueprint containerization layers
├── docker-compose.yml       # Multi-service network orchestration config
└── requirements.txt         # Package dependencies
```

## 🚀 Deployment Instructions

### Prerequisite
Ensure you have Docker Desktop installed and running on your local machine.

1. Launch the Cluster
Clone the repository, open your terminal inside the root folder, and execute a fresh service build:

```bash
docker compose up --build
```

This command automatically installs dependencies inside the isolated containers, mounts the shared folder volumes, and fires up both systems.

2. Access the Engine
Open your web browser and navigate to:

```Plaintext
http://localhost:8501
```

3. Simulating Live Modality Reconciliation (PACS Demo)
The dashboard sidebar updates on a pacing delay (configured to a comfortable demonstration interval).

Note the active Patient Identity (MRN) on the dashboard (e.g., pat-8150).

To simulate a matching imaging study arriving from the radiography department, create or rename a file inside your local ./data folder using that exact tag: pat-8150_chest_xray.dcm.

The Modality Cross-Reference Engine will instantly flip from a scanning state (Yellow) to a synchronized state (Green), deploying the Downstream AI Inference Engine cluster live on screen.

### 🧠 Clinical Engineering Rationale
In real medical environments, imaging datasets cannot be accurately analyzed by downstream AI networks without corresponding clinical telemetry validation. This project proves a production-level understanding of handling data latency, preventing queue backpressure, verifying rigid medical messaging models, and securely matching data paths before invoking diagnostic software layers.

---

## 👥 Author & Developer

* **Adedamola Oguntuyi** * [LinkedIn Profile](https://www.linkedin.com/in/adedamola-oguntuyi-80347a332/)
  * [GitHub Portfolio](https://github.com/dammyoguntuyi-ui)
  * *Clinical Radiographer specializing in Medical Data Science & Healthcare AI Ingestion Pipelines.*