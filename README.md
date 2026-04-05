# InspectRAIL - Road Damage Detection System

## Description

This project builds a **municipal-style decision-support pipeline** on the **RDD2022** (Road Damage Detection 2022) dataset: a **YOLOv8** detector locates and classifies road damage, a **convolutional autoencoder** scores surface anomaly on “normal” road patches, and a **rule-based urgency module** turns detections plus anomaly into a simple priority label for reporting. The reference implementation is a **Jupyter notebook** designed to run on **CPU** for accessibility (laptops without a GPU).

---

## Problem statement

Road networks need scalable ways to **detect damage types** (cracks, potholes, etc.), **prioritize repairs**, and support **repeatable reporting**. Manual inspection does not scale; purely generic image classifiers miss **multiple defects per image** and **spatial extent**. The goal here is an end-to-end workflow: from **images** to **localized damage labels**, a **compact severity signal**, and **exportable outputs** (figures, tables, optional JSON).

---

## Solution

- **Object detection (YOLOv8n):** Fine-tuned on a **balanced subset** of RDD2022 (train/val/test preserved) using Ultralytics, with configurable image size, epochs, and augmentations tuned for CPU training time.
- **Anomaly proxy (convolutional autoencoder):** Trained on **unlabeled** train images (treated as normal road), on random patches from a **road ROI**; at inference, **reconstruction MSE** summarizes deviation from “normal” appearance.
- **Urgency rules:** Combine class-specific weights, box area, detection count, and a **small** anomaly contribution; **pothole** can trigger an **URGENT** override; **no detections** yields **NORMAL** (anomaly does not override alone).

---

## Project pipeline

1. **Data:** Obtain `RD2022.zip` (or equivalent RDD2022 release), set `ZIP_PATH` / extraction folders, and extract to a layout containing `RDD_SPLIT/train|val|test` with `images/` and `labels/` (YOLO txt).
2. **Exploratory analysis:** Scan the dataset into a DataFrame; plot class distribution, countries, image sizes, labeled vs unlabeled, and sample visualizations.
3. **Subset (optional, recommended on CPU):** Build a **fractional, score-weighted** subset (40%) and write `rdd2022_subset.yaml` for Ultralytics.
4. **YOLO training:** Train `yolov8n.pt` on the subset with your hyperparameters; evaluate on **val** and **test**; save metrics tables and confusion analysis as needed.
5. **Autoencoder:** Select unlabeled train images, rank by simple **road-likeness** heuristics, train the AE on random ROI patches, save weights, and optionally plot reconstructions.
6. **End-to-end demo:** Run YOLO on a **custom image**, compute anomaly score, apply urgency rules, and save an annotated image plus optional JSON report.

---

## Environment and versions

Tested in a setup similar to the following (adjust if your machine differs):

| Component | Version (reference) |
|-----------|---------------------|
| **Python** | **3.11** (3.10+ generally compatible) |
| **PyTorch** | **2.11.x** (CPU wheels) |
| **torchvision** | **0.26.x** (match PyTorch install instructions) |
| **Ultralytics** | **8.4.x** (YOLOv8 API) |
| **OpenCV** | **4.13.x** |
| **Other** | NumPy 2.x, pandas, matplotlib, seaborn, scikit-learn, PyYAML, tqdm, Pillow |

Install GPU builds of PyTorch only if you have a supported NVIDIA setup and want faster training; the notebook is written for **`DEVICE = "cpu"`**.

---

## How to download and run

### 1. Clone or copy the project

```bash
git clone <your-repo-url>
cd <repo-folder>
```

Place **`inspectRAIL-Road-Crack-Detection-System.ipynb`** (and this `README.md`) in the project directory—or open the notebook from wherever you keep it.

### 2. Dataset

- Acquire the **RDD2022** dataset (official source). You should have a zip such as **`RD2022.zip`** whose extraction contains **`RDD_SPLIT`** with `train`, `val`, and `test`, each with **`images`** and **`labels`** (YOLO format: `class_id x_center y_center width height` normalized).

### 3. Python environment (recommended: venv)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

python -m pip install --upgrade pip
pip install opencv-python ultralytics matplotlib seaborn pandas scikit-learn pyyaml tqdm pillow torch torchvision
```

Install **PyTorch** from [https://pytorch.org](https://pytorch.org) if you need a specific CPU/CUDA build.

### 4. Configure paths in the notebook

Open the notebook in **VS Code**, **Cursor**, or **Jupyter**. In the **CONFIG** cell, set at least:

- **`ZIP_PATH`** — absolute path to `RD2022.zip`
- **`EXTRACT_ROOT`**, **`OUTPUT_DIR`** — where data and outputs go (defaults are relative to the notebook’s working directory)

Run the notebook **top to bottom** the first time so imports, extraction, helpers, and `yaml_path` exist before training.

### 5. Run order (high level)

1. Install / import cells  
2. CONFIG + extract + helpers  
3. EDA cells (optional but useful)  
4. Subset + **`rdd2022_subset.yaml`**  
5. **YOLO `train`** (long on CPU)  
6. Evaluation / metrics / confusion (as needed)  
7. Autoencoder data prep + training  
8. Custom image + urgency demo cell (**set `CUSTOM_IMAGE_PATH`**)

**Working directory:** Start Jupyter or your IDE from the folder you want as the root so relative paths like `RDD2022_EXTRACTED/` and `runs/detect/` resolve consistently.

---

## Outputs (typical)

Under your chosen output directory (e.g. `rdd2022_outputs/`):

- **Figures:** distributions, samples, YOLO curves, AE loss / reconstructions  
- **Models:** YOLO run under `project/name` (Ultralytics), AE weights e.g. `conv_autoencoder.pth`  
- **Reports:** CSV inventories, optional `final_metrics_table.csv`, custom prediction JSON  

---

## Notes and limitations

- Training on **CPU** is feasible only with a **subset** and modest `imgsz` / epochs; increase data or epochs when you have time or a GPU.
- **Urgency** is **hand-crafted** for interpretability—not learned from labels.
- Fix any **path** or **`runs/detect/...`** locations if your Ultralytics **working directory** differs from the notebook’s assumptions.

---

## References

- **RDD2022** — Road Damage Detection 2022 dataset (use the citation required by the dataset license in academic work).
- **Ultralytics YOLOv8** — [https://github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics)

---

## License

Add your license (e.g. MIT) and respect the **RDD2022** dataset terms. This README describes an educational / project workflow; adapt paths and versions to your machine.
