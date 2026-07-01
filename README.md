# Multi-Modality Clinical AI Triage Pipeline & Safety Auditor

An interoperable, end-to-end medical imaging data orchestration pipeline that ingests DICOM studies from a local PACS server, dynamically routes cases across multi-modality AI models based on metadata evaluation, and acts as an automated clinical safety gatekeeper by auditing discrepancies against expert human ground truth.

## 🏗️ Architecture Overview

The system establishes a robust middleware framework bridging clinical infrastructure, data governance, and analytics interfaces:

* **Infrastructure Layer (`orthanc-pacs` container)**: A production-grade Orthanc PACS microservice serving multi-modality DICOM medical instances over containerized RESTful API endpoints.
* **Data Orchestration Middleware (`triage-listener` container)**: An event-driven background daemon utilizing the `watchdog` framework to catch filesystem changes natively, strip sensitive PHI fields, and handle multi-modality AI routing schemas.
* **Clinical Safety & Audit Layer**: Integrated rules-based validation filters that isolate discrepancies (such as the simulated `PATIENT_005` cross-reference validation conflict) directly into an elevated administrative review state.
* **Visualization Layer (`triage-dashboard` container)**: A reactive frontend interface running on a continuous 5-second polling loop to hot-reload changing clinical queues, priority counters, and safety audit trails in real time.

## ⚙️ Event-Driven Ingestion Engine (Watchdog Middleware)

To transition this pipeline from a manual batch script into a real-time, production-ready healthcare sandbox, the system utilizes an asynchronous, event-driven architecture powered by a background filesystem listener (`scripts/watch_pacs.py`).

### 🔄 Asynchronous Data Flow & Race Condition Mitigation

In a live hospital environment, imaging modalities stream data streams sequentially. To replicate this safely without causing system chokes or cascading database writes, the middleware implements a **Thread-Locked Batch Accumulator Pattern**:

1. **OS-Level Hooking:** The background listener binds directly to the absolute filesystem storage layer using the `watchdog` framework, trapping both file creation and modification loops natively.
2. **Mutex Thread Locking (`threading.Lock`):** To prevent rapid-fire sequential DICOM file writes from spawning racing background processes, a persistent mutex lock isolates the core evaluation state.
3. **Delayed Batch Accumulation:** Instead of executing the pipeline on every individual image alert, the handler sets a rolling countdown timer. Every subsequent write resets the window. The core orchestration engine (`ai_csv_generator.py`) is triggered **exactly once** only after the ingestion directory achieves a quiet window of silence.

```text
 📥 Sequential DICOM Writes 
 (PATIENT_001.dcm -> PATIENT_010.dcm)
               │
               ▼
   [ 🕵️‍♂️ watch_pacs.py Active Listener ]
               │
      [ 🔒 Threading Lock ] ──► (Queues concurrent OS bursts)
               │
      [ ⏳ 5s Countdown Timer ] ◄── (Resets continuously on new activity)
               │
       (Ingestion Quiet Window Achieved)
               │
               ▼
 [ 🚀 EXECUTE SINGLE BATCH RUN: ai_csv_generator.py ]
```
 
---

## 🛠️ Tech Stack & Protocols

* **Medical Imaging Protocol:** DICOM (Digital Imaging and Communications in Medicine)
* **PACS Node:** Orthanc server architecture
* **Data Layer / Language:** Python 3 (Libraries: `pydicom`, `requests`, `numpy`, `csv`, `random`)
* **Frontend Analytics:** Glide Engine (Low-Code Data Mapping & Cloud Synchronization)
* **Frontend Analytics**: Streamlit Engine (Containerized web application with live data polling)
* **Containerization & Orchestration**: Docker, Docker Compose, Linux Virtualization Subsystem (WSL2)

---

## 🚀 Deployment & Sandbox Execution

### 🚀 Single-Command Sandbox Deployment

Thanks to the containerized ecosystem architecture, you do not need to configure local Python virtual environments, paths, or web endpoints manually. 

#### 1. Spin Up the Microservice Cluster

Open your terminal in the repository root and launch the composition:

```bash
docker compose up --build
```

This single orchestrator pulls the official Orthanc distribution, assembles your Python background environments, binds shared data volumes, and maps your local network ports automatically.

#### 2. Access the Ecosystem Endpoints

* **Clinical Triage Dashboard: http://localhost:8501

* **Orthanc PACS Explorer Node: http://localhost:8042

#### 3. Run the Production Modality Simulator
To simulate real-time workflows pouring new clinical imaging files into your active container network, open a separate terminal window on your host computer and run the mock generator:

```bash
python scripts/generate_test_dicoms.py
```

## 📊 Live Simulation Metrics & Edge-Case Trapping

The safety framework is stress-tested using a dynamic validator that tracks performance across scaling workloads while successfully isolating targeted clinical blind spots (such as under-called critical spinal masses).

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
```

## 🛡️ Intellectual Property, Governance & Compliance

Data Privacy (HIPAA/GDPR Alignment): The custom Python routing framework isolates PACS internal instance handles from operational worklists, creating anonymized clinical_mrn hooks to eliminate the accidental spread of Protected Health Information (PHI).

IP Defense: This technical framework is legally stamped under the author's jurisdiction. The dynamic method of cross-level REST tag resolution to validate third-party diagnostic algorithms establishes documented "Prior Art" on this repository.

Developer: Adedamola
Domain Focus: Clinical Data Orchestration, Imaging Middleware & Interoperable Healthcare Systems
