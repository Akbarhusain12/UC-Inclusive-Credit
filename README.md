# Automated Receipt ETL Pipeline 

**Developed for UC Inclusive Credit**

## 1. Architecture Overview
This repository contains a fully automated, event-driven ETL (Extract, Transform, Load) pipeline. It is designed to monitor an inbox for incoming vendor receipts, extract unstructured visual data, parse it into a strict JSON schema, and load it into a structured database for ageing analysis.

The architecture decouples the vision processing from the language reasoning to maximize accuracy while maintaining sub-second LLM inference speeds.



## 2. Deliverables
* **Demo Video:** [Insert YouTube Unlisted / Loom Link Here]
* **Google Sheet:** https://docs.google.com/spreadsheets/d/1Gpm3dL0u2qr3cGVor4NC4BKGAwDDuHq-1rSFyvgoRv8/edit?usp=sharing
* **Workflow Code:** `n8n_workflow.json` (Included in repo)
* **Vision Script:** `vision_extractor.py` (Included in repo)

## 3. Tech Stack & Engineering Rationale

* **Orchestration Layer (n8n):** Chosen for its visual concurrency management and native webhook/polling triggers. It handles state management (marking emails as read to ensure idempotency) and file system I/O.
* **Vision Processing Layer (Python, OpenCV, Tesseract):** Standard LLMs struggle with spatial reasoning on noisy receipts. I built a dedicated Python preprocessing layer using OpenCV (Gaussian blurring, inversion detection) and Tesseract (specifically tuned to PSM 4 to handle variable-sized column data).
* **Reasoning Layer (Groq API / Llama-3.1-8b-instant):** Chosen for its massive inference speed. The 8B model is heavily constrained using a strict system prompt and JSON-mode forcing to prevent format breaking.
* **Storage Layer (Google Sheets):** Acts as the mock database, calculating invoice ageing dynamically based on the pipeline's standardized date outputs.

## 4. Engineering Resilience & Edge-Case Handling
Pipelines fail when data is dirty. This architecture was explicitly designed to handle edge cases gracefully without crashing the downstream database.

* **The Hallucination Failsafe:** Generative models often hallucinate fake data (e.g., generic "Walmart" receipts) when fed empty or upside-down OCR text. I engineered a strict prompt trap that forces the LLM to output `Vendor: UNKNOWN`, `Amount: 0`, and `Date: null` if the text lacks financial context, safely neutralizing the document for manual review.
* **Localization & Date Normalization:** The SROIE dataset contains Malaysian receipts (`DD/MM/YYYY`). Llama 3 natively expects US formats (`MM/DD/YYYY`). I implemented prompt-level constraints and a robust JavaScript sanitization block that intercepts unparseable dates and defaults to the current timestamp to prevent `null` value crashes in downstream Ageing Day calculations.
* **Concurrency Locks:** To prevent file-overwrite race conditions during batch email ingestion, the pipeline dynamically writes files to disk using n8n's `$execution.id`. This guarantees unique, thread-safe file paths even if multiple invoices arrive at the exact same millisecond.

## 5. Setup & Execution

### Prerequisites
* Python 3.10+
* Tesseract-OCR installed and added to PATH
* n8n installed (local or cloud)
* Groq API Key

### Installation
1. Clone this repository.
2. Install Python dependencies: `pip install opencv-python pytesseract pdfplumber numpy`
3. Import `n8n_workflow.json` into your n8n instance.
4. Update the Groq HTTP Request node with your API credentials.
5. Update the Python execution node path to point to your local `vision_extractor.py` file.