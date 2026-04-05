# 🛣️ InspectRAIL — Road Analysis & Inspection Logic

> **An end-to-end road damage detection and reporting pipeline** powered by YOLOv8, a Convolutional Autoencoder, and a rule-based urgency system — trained on RDD2022 and deployed as a live inspection app with a real-time city dashboard.

[![Live App](https://img.shields.io/badge/🚧_Live_App-Streamlit-FF4B4B?style=flat-square)](https://road-damage-detection-system.streamlit.app/)
[![Dashboard](https://img.shields.io/badge/📊_Dashboard-Vercel-000000?style=flat-square)](https://inspect-rail.vercel.app/)
[![Dataset](https://img.shields.io/badge/📦_Dataset-Kaggle-20BEFF?style=flat-square)](https://www.kaggle.com/datasets/aliabdelmenam/rdd-2022)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square)](https://www.python.org/)

---

## 🌐 Live Deployments

| Component | URL | Description |
|---|---|---|
| **InspectRAIL App** | [road-damage-detection-system.streamlit.app](https://road-damage-detection-system.streamlit.app/) | Upload or capture road images for instant AI analysis |
| **City Dashboard** | [inspect-rail.vercel.app](https://inspect-rail.vercel.app/) | Live map, analytics, and report management for submitted inspections |

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [System Architecture](#-system-architecture)
3. [Dataset](#-dataset)
4. [Repository Structure](#-repository-structure)
5. [Setup & Installation](#-setup--installation)
6. [Training the Models](#-training-the-models)
7. [Running Inference](#-running-inference)
8. [Streamlit App](#-streamlit-app)
9. [Dashboard (Next.js)](#-dashboard-nextjs)
10. [Deployment](#-deployment)
11. [Model Details](#-model-details)
12. [Results](#-results)
13. [References](#-references)

---

## 🔍 Project Overview

InspectRAIL is a **municipal-style decision-support pipeline** that:

1. **Detects and classifies** road damage (cracks, potholes) in images using a fine-tuned **YOLOv8n** object detector
2. **Scores road surface anomaly** using a **Convolutional Autoencoder** trained on unlabeled normal road patches
3. **Assigns urgency levels** (NORMAL → LOW → MEDIUM → HIGH → URGENT) using a rule-based system combining class severity, detection count, box area, and anomaly score
4. **Reports findings** to a live **Next.js dashboard** with GPS mapping, analytics charts, and filterable report history

### Damage Classes

| Class ID | Name | Description |
|---|---|---|
| 0 | Longitudinal Crack | Cracks running parallel to road direction |
| 1 | Transverse Crack | Cracks running perpendicular to road direction |
| 2 | Alligator Crack | Interconnected cracking pattern resembling alligator skin |
| 3 | Other Corruption | Misc surface degradation |
| 4 | Pothole | Structural holes — always triggers **URGENT** |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    InspectRAIL Pipeline                  │
├──────────────┬──────────────────────┬────────────────────┤
│   Input      │     AI Models        │     Output         │
│              │                      │                    │
│  Road Image  │  YOLOv8n Detector   │  Bounding Boxes    │
│  (upload /   │  ──────────────────  │  Damage Classes    │
│   camera)    │  Conv Autoencoder   │  Urgency Level     │
│              │  ──────────────────  │  Anomaly Score     │
│  GPS Coords  │  Rule-Based Urgency │  JSON Report       │
│  (optional)  │                      │  → Supabase DB     │
└──────────────┴──────────────────────┴────────────────────┘
                                              │
                          ┌───────────────────▼──────────────┐
                          │     City Dashboard (Next.js)      │
                          │  Map View · Analytics · Reports   │
                          └──────────────────────────────────┘
```

---

## 📦 Dataset

**RDD2022 — Road Damage Detection 2022**

- **Source:** [Kaggle — RDD 2022](https://www.kaggle.com/datasets/aliabdelmenam/rdd-2022)
- **Countries:** Japan, India, Norway, United States, Czech Republic, China (Drone + Motorbike)
- **Total images:** ~38,385 across train/val/test splits
- **Classes:** 5 damage types (see above)
- **Format:** YOLO `.txt` labels (normalized `class x_center y_center width height`)

### Dataset Statistics

| Split | Images |
|---|---|
| Train | 26,869 |
| Val | 5,758 |
| Test | 5,758 |

> **Note:** Due to CPU training constraints, a **balanced subset (~40%)** is used. The subset preserves class distribution using score-weighted sampling.

---


## ⚙️ Setup & Installation

### Prerequisites

- Python **3.11** (recommended)
- Node.js **18+** (for the dashboard only)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/aitezazshah/road-damage-detection-system.git
cd road-damage-detection-system
```

### 2. Download the Dataset

Download from Kaggle:

```bash
# Option A — Kaggle CLI
pip install kaggle
kaggle datasets download -d aliabdelmenam/rdd-2022
unzip rdd-2022.zip -d RDD2022_EXTRACTED

# Option B — Manual
# Go to https://www.kaggle.com/datasets/aliabdelmenam/rdd-2022
# Click Download, extract to RDD2022_EXTRACTED/
```

The extracted folder should contain:
```
RDD2022_EXTRACTED/
└── RDD_SPLIT/
    ├── train/
    │   ├── images/
    │   └── labels/
    ├── val/
    │   ├── images/
    │   └── labels/
    └── test/
        ├── images/
        └── labels/
```

### 3. Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**`requirements.txt`:**
```txt
streamlit==1.43.2
ultralytics>=8.3.0
torch>=2.4.0
torchvision>=0.19.0
numpy==1.26.4
pandas>=2.2.0
pillow>=10.4.0
matplotlib>=3.10.0
opencv-python-headless==4.10.0.84
pyyaml>=6.0.2
supabase
streamlit-js-eval
```

> **GPU users:** Replace `torch==2.11.0` with the appropriate CUDA build from [pytorch.org](https://pytorch.org/get-started/locally/).

---

## 🏋️ Training the Models

Open the notebook in Jupyter, VS Code, or Cursor:

```bash
jupyter notebook inspectRAIL-Road-Crack-Detection-System.ipynb
```

### Step 1 — Configure Paths

In the **CONFIG cell** at the top of the notebook, set:

```python
ZIP_PATH    = r"C:\path\to\RD2022.zip"       # Path to downloaded zip
EXTRACT_ROOT = "RDD2022_EXTRACTED"            # Where to extract
OUTPUT_DIR  = "rdd2022_outputs"               # Where outputs go
```

### Step 2 — Run Cells in Order

| Step | Cell Section | Description |
|---|---|---|
| 1 | **Imports & Config** | Install checks, path setup |
| 2 | **Extract & EDA** | Extract dataset, visualize class distributions |
| 3 | **Build Subset** | Create balanced ~40% subset, write YAML |
| 4 | **YOLO Training** | Fine-tune YOLOv8n on subset (30 epochs) |
| 5 | **Evaluation** | Confusion matrix, precision/recall/mAP on test set |
| 6 | **Autoencoder** | Build clean road dataset, train ConvAE |
| 7 | **Demo** | Run on a custom image, compute urgency |

### Step 3 — YOLO Training

```python
# Configured in notebook — key hyperparameters
YOLO_EPOCHS  = 30
YOLO_IMGSZ   = 512
YOLO_BATCH   = 4       # Increase if you have more RAM
DEVICE       = "cpu"   # Change to "cuda" or "mps" if available
```

Training logs are saved to `runs/detect/yolo_cpu_subset/`. Expected time on CPU: **~40 hours** for 30 epochs. Use a GPU or reduce epochs for faster iteration.

### Step 4 — Autoencoder Training

```python
AE_EPOCHS     = 12
AE_BATCH_SIZE = 32
AE_LR         = 1e-3
AE_PATCH_SIZE = 128
```

The AE trains only on **unlabeled, road-scored images** — ensuring it learns normal road surface texture, not vehicles or sky.


---

## 🔬 Running Inference

### Option A — Notebook (single image)

```python
CUSTOM_IMAGE_PATH = Path(r"C:\path\to\your\road_image.jpg")

pred    = best_model.predict(source=str(CUSTOM_IMAGE_PATH), imgsz=512, conf=0.25)[0]
anomaly = compute_anomaly_score(CUSTOM_IMAGE_PATH, ae_model, patch_size=128)
urgency, score = compute_urgency_from_detection(pred, anomaly)

print(f"Urgency: {urgency} | Score: {score:.4f} | Anomaly: {anomaly:.5f}")
```

### Option B — Streamlit App (local)

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Option C — Live App

Visit [road-damage-detection-system.streamlit.app](https://road-damage-detection-system.streamlit.app/)

---

## 🖥️ Streamlit App

The inspection app (`app.py`) provides:

- **Upload Image** or **Camera Capture** modes
- **Real-time YOLO detection** with annotated bounding boxes
- **Anomaly scoring** using the Convolutional Autoencoder
- **Urgency classification**: NORMAL / LOW / MEDIUM / HIGH / URGENT
- **GPS input** (latitude/longitude) for location tagging
- **Submit to Dashboard** — sends report + images to Supabase

### Running Locally

```bash
# Set Supabase credentials as environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"

streamlit run app.py
```

Or create a `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

---

## 📊 Dashboard (Next.js)

The city dashboard (`dashboard/`) provides:

- **Reports tab** — filterable, sortable list of all submitted inspections with images
- **Map tab** — GPS pins color-coded by urgency level using Leaflet
- **Analytics tab** — urgency distribution pie chart, damage frequency bar chart, timeline line chart
- **Auto-refresh** every 30 seconds
- **JSON export** of all reports

### Running Dashboard Locally

```bash
cd dashboard
npm install

# Create .env.local
echo "NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co" >> .env.local
echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key" >> .env.local

npm run dev
```

Open `http://localhost:3000`.

### Supabase Setup

1. Create a free project at [supabase.com](https://supabase.com)
2. Run this SQL in the **SQL Editor**:

```sql
create table if not exists public.reports (
  id bigint generated by default as identity primary key,
  created_at timestamptz not null default now(),
  urgency text not null,
  score double precision,
  anomaly double precision,
  detected jsonb default '[]'::jsonb,
  num_det integer default 0,
  latitude double precision,
  longitude double precision,
  location_str text,
  source text,
  image_url text,
  annot_url text
);
```

3. Go to **Storage** → Create bucket named `inspectRAIL-images` → set to **Public**
4. Copy **Project URL** and **anon key** from **Settings → API**

---

## 🚀 Deployment

### Streamlit App (Streamlit Cloud)

1. Push your repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New App**
3. Select your repo, branch `main`, main file `app.py`
4. Add secrets under **Settings → Secrets**:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```
5. Click **Deploy**

### Dashboard (Vercel)

1. Go to [vercel.com](https://vercel.com) → **Import Project** → select your GitHub repo
2. Vercel auto-detects `vercel.json` and builds the `dashboard/` folder
3. Add **Environment Variables**:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Click **Deploy**

---

## 🤖 Model Details

### YOLOv8n Detector

| Property | Value |
|---|---|
| Base model | `yolov8n.pt` (pretrained COCO) |
| Parameters | 3.0M |
| Input size | 512×512 |
| Epochs | 30 |
| Optimizer | AdamW (lr=0.001) |
| Augmentations | Mosaic, mixup, HSV, scale, rotate |
| Training device | CPU |

### Convolutional Autoencoder

| Property | Value |
|---|---|
| Architecture | 3-layer Conv encoder + 3-layer ConvTranspose decoder |
| Bottleneck | 64 channels at 16×16 |
| Patch size | 128×128 |
| Training data | Top 1000 road-scored unlabeled images |
| Loss | MSE |
| Epochs | 12 |

### Urgency Rules

```
if pothole detected           → URGENT  (always, regardless of score)
if final_score ≥ 0.67         → HIGH
if final_score ≥ 0.34         → MEDIUM
if final_score ≥ 0.10         → LOW
if no detections              → NORMAL
```

Where `final_score = 0.45 × severity + 0.30 × area + 0.15 × count + 0.10 × anomaly`

---

## 📈 Results

### Detection Performance (Test Set)

| Split | Precision | Recall | F1 | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|
| Validation | 0.5606 | 0.4867 | 0.5216 | 0.4951 | 0.2352 |
| Test | 0.5651 | 0.4836 | 0.5212 | 0.4947 | 0.236 |

> **Note:** Precision/Recall for the training set is not computed by YOLO — only losses are tracked during training. The val/test metrics above are the standard evaluation metrics for object detection.

---

## 📚 References

- **RDD2022 Dataset** — Arya, D. et al. *"RDD2022: A multi-national image dataset for automatic Road Damage Detection"*, 2022. [Kaggle](https://www.kaggle.com/datasets/aliabdelmenam/rdd-2022)
- **Ultralytics YOLOv8** — [github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics)
- **Streamlit** — [streamlit.io](https://streamlit.io)
- **Supabase** — [supabase.com](https://supabase.com)
- **Next.js** — [nextjs.org](https://nextjs.org)

---


<div align="center">
  Built with by Syed Aitezaz Imtiaz
</div>
