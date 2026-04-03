# ===========================
# app.py — Road Damage Detection Streamlit App
# Save this file and run: streamlit run app.py
# ===========================

import streamlit as st
import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from pathlib import Path
import tempfile
import time

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(
    page_title="Road Damage Detection",
    page_icon="🚧",
    layout="wide"
)

# ===========================
# STYLING
# ===========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .main { background-color: #0f1117; }

    .title-block {
        background: linear-gradient(135deg, #1a1f2e 0%, #0f1117 100%);
        border-left: 4px solid #f0a500;
        padding: 2rem 2.5rem;
        border-radius: 0 12px 12px 0;
        margin-bottom: 2rem;
    }
    .title-block h1 {
        font-family: 'IBM Plex Mono', monospace;
        color: #f0f0f0;
        font-size: 2rem;
        margin: 0 0 0.3rem 0;
    }
    .title-block p {
        color: #8a9bb0;
        margin: 0;
        font-size: 0.95rem;
    }

    .result-card {
        background: #1a1f2e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #2a3044;
    }
    .result-card h4 {
        color: #8a9bb0;
        font-size: 0.75rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 0.5rem 0;
        font-family: 'IBM Plex Mono', monospace;
    }
    .result-card .value {
        color: #f0f0f0;
        font-size: 1.4rem;
        font-weight: 600;
    }

    .urgency-NORMAL   { color: #4ade80 !important; }
    .urgency-LOW      { color: #facc15 !important; }
    .urgency-MEDIUM   { color: #fb923c !important; }
    .urgency-HIGH     { color: #f87171 !important; }
    .urgency-URGENT   { color: #ff3b3b !important; font-size: 1.8rem !important; }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 0.2rem;
        font-family: 'IBM Plex Mono', monospace;
    }
    .badge-crack    { background: #1e3a5f; color: #60a5fa; }
    .badge-pothole  { background: #3b1f1f; color: #f87171; }
    .badge-other    { background: #2a2a1f; color: #fbbf24; }

    .anomaly-bar-bg {
        background: #2a3044;
        border-radius: 999px;
        height: 10px;
        margin-top: 0.5rem;
        overflow: hidden;
    }
    .anomaly-bar-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #4ade80, #facc15, #f87171);
    }

    .upload-zone {
        border: 2px dashed #2a3044;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        color: #8a9bb0;
        background: #1a1f2e;
    }
    .stButton > button {
        background: #f0a500;
        color: #0f1117;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.9rem;
        letter-spacing: 0.05em;
        width: 100%;
    }
    .stButton > button:hover { background: #ffc107; }

    .divider {
        border: none;
        border-top: 1px solid #2a3044;
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ===========================
# MODEL DEFINITIONS
# ===========================
class ConvAutoencoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1), nn.ReLU(),
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1), nn.ReLU(),
            nn.ConvTranspose2d(16,  3, 3, stride=2, padding=1, output_padding=1), nn.Sigmoid()
        )
    def forward(self, x):
        return self.decoder(self.encoder(x))

# ===========================
# CONSTANTS
# ===========================
CLASS_NAMES = [
    'Longitudinal Crack',
    'Transverse Crack',
    'Alligator Crack',
    'Other Corruption',
    'Pothole'
]

SEVERITY_WEIGHTS   = {0: 0.50, 1: 0.65, 2: 0.85, 3: 0.40, 4: 1.00}
POTHOLE_CLASS_IDX  = 4
DEVICE             = "cpu"
AE_PATCH_SIZE      = 128
YOLO_IMGSZ         = 512

# ===========================
# LOAD MODELS (cached)
# ===========================
@st.cache_resource
def load_models():
    from ultralytics import YOLO
    import functools

    # ✅ Patch torch.load to always use weights_only=False
    original_load = torch.load
    torch.load = functools.partial(original_load, weights_only=False)
    # ── adjust these paths to your saved models ──
    YOLO_PATH = Path("models/best.pt")
    AE_PATH   = Path("models/conv_autoencoder.pth")

    yolo_model = YOLO(str(YOLO_PATH))

    ae_model = ConvAutoencoder()
    ae_model.load_state_dict(
        torch.load(str(AE_PATH), map_location=DEVICE, weights_only=False)
    )
    ae_model.eval()

    # Restore original torch.load after models are loaded
    torch.load = original_load

    return yolo_model, ae_model
# ===========================
# INFERENCE FUNCTIONS
# ===========================
def compute_anomaly_score(img_bgr, model, patch_size=128, num_patches=4):
    img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]

    # Road ROI
    y1, y2 = int(0.45 * h), int(0.95 * h)
    x1, x2 = int(0.10 * w), int(0.90 * w)
    roi = img[y1:y2, x1:x2]
    h, w = roi.shape[:2]

    if h < patch_size or w < patch_size:
        roi  = cv2.resize(roi, (max(patch_size, w), max(patch_size, h)))
        h, w = roi.shape[:2]

    criterion = nn.MSELoss()
    losses = []
    for _ in range(num_patches):
        y = np.random.randint(0, h - patch_size + 1)
        x = np.random.randint(0, w - patch_size + 1)
        patch   = roi[y:y+patch_size, x:x+patch_size].astype(np.float32) / 255.0
        patch_t = torch.tensor(np.transpose(patch, (2,0,1)),
                            dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            recon = model(patch_t)
            losses.append(criterion(recon, patch_t).item())

    return float(np.mean(losses))


def compute_urgency(result, anomaly_score):
    if result.boxes is None or len(result.boxes) == 0:
        return "NORMAL", 0.0, []

    classes = [int(b.cls.item())    for b in result.boxes]
    confs   = [float(b.conf.item()) for b in result.boxes]
    xyxy    = result.boxes.xyxy.cpu().numpy()

    # Pothole → always URGENT
    if POTHOLE_CLASS_IDX in classes:
        detected = list({CLASS_NAMES[c] for c in classes})
        return "URGENT", 1.0, detected

    area_score = severity_score = 0.0
    count_score = min(1.0, len(classes) / 5.0)
    img_h, img_w = result.orig_shape
    image_area   = img_h * img_w

    for c, box, conf in zip(classes, xyxy, confs):
        x1, y1, x2, y2 = box
        area_ratio  = max(1.0, (x2-x1)*(y2-y1)) / image_area
        area_score     += min(1.0, area_ratio * 8.0)
        severity_score += SEVERITY_WEIGHTS.get(c, 0.4) * conf

    severity_score = min(1.0, severity_score / max(1, len(classes)))
    area_score     = min(1.0, area_score)
    anomaly_norm   = min(1.0, anomaly_score / 0.03)

    final_score = (
        0.45 * severity_score +
        0.30 * area_score +
        0.15 * count_score +
        0.10 * anomaly_norm
    )

    detected = list({CLASS_NAMES[c] for c in classes})

    if final_score >= 0.67:   return "HIGH",   final_score, detected
    elif final_score >= 0.34: return "MEDIUM", final_score, detected
    elif final_score >= 0.10: return "LOW",    final_score, detected
    else:                     return "NORMAL", final_score, detected


def get_badge_class(name):
    n = name.lower()
    if "pothole"   in n: return "badge-pothole"
    if "crack"     in n: return "badge-crack"
    return "badge-other"

# ===========================
# UI
# ===========================
st.markdown("""
<div class="title-block">
    <h1>🚧 Road Damage Detection</h1>
    <p>Upload a road image — the system detects damage type, severity, and urgency level.</p>
</div>
""", unsafe_allow_html=True)

# Load models
with st.spinner("Loading models..."):
    try:
        yolo_model, ae_model = load_models()
        st.success("Models loaded.", icon="✅")
    except Exception as e:
        st.error(f"Failed to load models: {e}")
        st.stop()

# Upload
uploaded = st.file_uploader(
    "Upload a road image",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed"
)

if uploaded:
    # Save to temp file
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = Path(tmp.name)

    img_bgr = cv2.imread(str(tmp_path))

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("#### Original Image")
        st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), use_column_width=True)

    # Run inference
    with st.spinner("Analysing..."):
        time.sleep(0.3)
        pred    = yolo_model.predict(
            source=str(tmp_path),
            imgsz=YOLO_IMGSZ,
            conf=0.25,
            device=DEVICE,
            verbose=False
        )[0]
        anomaly = compute_anomaly_score(img_bgr, ae_model, patch_size=AE_PATCH_SIZE)
        urgency, score, detected = compute_urgency(pred, anomaly)

    with col2:
        st.markdown("#### Annotated Result")
        vis = pred.plot()
        st.image(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), use_column_width=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Results row ───────────────────────────────────────
    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.markdown(f"""
        <div class="result-card">
            <h4>Urgency Level</h4>
            <div class="value urgency-{urgency}">{urgency}</div>
        </div>""", unsafe_allow_html=True)

    with r2:
        num_det = len(pred.boxes) if pred.boxes is not None else 0
        st.markdown(f"""
        <div class="result-card">
            <h4>Detections</h4>
            <div class="value">{num_det}</div>
        </div>""", unsafe_allow_html=True)

    with r3:
        score_pct = round(score * 100, 1)
        st.markdown(f"""
        <div class="result-card">
            <h4>Urgency Score</h4>
            <div class="value">{score_pct}%</div>
        </div>""", unsafe_allow_html=True)

    with r4:
        st.markdown(f"""
        <div class="result-card">
            <h4>Anomaly Score</h4>
            <div class="value">{anomaly:.5f}</div>
            <div class="anomaly-bar-bg">
                <div class="anomaly-bar-fill" style="width:{min(100, anomaly/0.03*100):.1f}%"></div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── Detected classes ──────────────────────────────────
    if detected:
        st.markdown("#### Detected Damage Types")
        badges = " ".join(
            f'<span class="badge {get_badge_class(d)}">{d}</span>'
            for d in detected
        )
        st.markdown(badges, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="result-card" style="border-color:#1e3a1e;">
            <div class="value urgency-NORMAL">✓ No road damage detected</div>
        </div>""", unsafe_allow_html=True)

    # Cleanup
    tmp_path.unlink(missing_ok=True)