import os
import sys

# MUST BE THE FIRST TWO LINES OF CODE
os.environ["OPENCV_VIDEOIO_PRIORITY_BACKEND"] = "0"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import streamlit as st
import cv2
import numpy as np

import torch
import torch.nn as nn
from PIL import Image
from pathlib import Path
import tempfile
import time
import json
import datetime
import base64
import functools

from supabase import create_client

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(
    page_title="InspectRAIL",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===========================
# STYLING
# ===========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

    :root {
        --bg:        #080c14;
        --surface:   #0d1220;
        --surface2:  #131929;
        --border:    #1e2a3a;
        --accent:    #f59e0b;
        --accent2:   #06b6d4;
        --text:      #e2e8f0;
        --muted:     #64748b;
        --normal:    #22c55e;
        --low:       #eab308;
        --medium:    #f97316;
        --high:      #ef4444;
        --urgent:    #dc2626;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background-color: var(--bg) !important;
        color: var(--text);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] * { color: var(--text) !important; }

    /* Hide default streamlit elements */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; }

    /* ── LOGO BAR ── */
    .logo-bar {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.5rem 0 1rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }
    .logo-icon {
        width: 48px; height: 48px;
        background: linear-gradient(135deg, var(--accent), #d97706);
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.4rem;
        flex-shrink: 0;
    }
    .logo-text h1 {
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 1.6rem;
        margin: 0;
        color: var(--text);
        letter-spacing: -0.02em;
    }
    .logo-text p {
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        color: var(--muted);
        margin: 0;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    /* ── NAV TABS ── */
    .nav-tabs {
        display: flex;
        gap: 0.4rem;
        background: var(--surface);
        border-radius: 12px;
        padding: 0.35rem;
        margin-bottom: 2rem;
        border: 1px solid var(--border);
    }
    .nav-tab {
        flex: 1;
        padding: 0.55rem 1rem;
        border-radius: 8px;
        text-align: center;
        font-family: 'DM Mono', monospace;
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.05em;
        cursor: pointer;
        color: var(--muted);
        border: none;
        background: transparent;
        transition: all 0.2s;
    }
    .nav-tab.active {
        background: var(--accent);
        color: #0a0a0a;
        font-weight: 700;
    }

    /* ── INPUT MODE SELECTOR ── */
    .mode-selector {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .mode-card {
        background: var(--surface);
        border: 2px solid var(--border);
        border-radius: 16px;
        padding: 1.8rem 1rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.25s;
    }
    .mode-card:hover, .mode-card.active {
        border-color: var(--accent);
        background: #1a1500;
    }
    .mode-card .icon { font-size: 2.2rem; margin-bottom: 0.6rem; }
    .mode-card h3 {
        font-family: 'Syne', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: var(--text);
        margin: 0 0 0.25rem;
    }
    .mode-card p {
        font-size: 0.78rem;
        color: var(--muted);
        margin: 0;
    }

    /* ── RESULT CARDS ── */
    .result-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .result-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
        background: var(--accent);
        border-radius: 0 2px 2px 0;
    }
    .result-card .label {
        font-family: 'DM Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.4rem;
    }
    .result-card .val {
        font-family: 'Syne', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text);
    }

    /* ── URGENCY COLORS ── */
    .u-NORMAL  { color: var(--normal)  !important; }
    .u-LOW     { color: var(--low)     !important; }
    .u-MEDIUM  { color: var(--medium)  !important; }
    .u-HIGH    { color: var(--high)    !important; }
    .u-URGENT  { color: var(--urgent)  !important; animation: pulse 1.2s infinite; }

    @keyframes pulse {
        0%,100% { opacity:1; } 50% { opacity:0.6; }
    }

    /* ── URGENCY BADGE ── */
    .urgency-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.08em;
    }
    .ub-NORMAL  { background:#052e16; color:#4ade80; border:1px solid #166534; }
    .ub-LOW     { background:#422006; color:#fbbf24; border:1px solid #92400e; }
    .ub-MEDIUM  { background:#431407; color:#fb923c; border:1px solid #9a3412; }
    .ub-HIGH    { background:#450a0a; color:#f87171; border:1px solid #991b1b; }
    .ub-URGENT  { background:#450a0a; color:#ff3b3b; border:1px solid #dc2626;
                  animation: pulse 1.2s infinite; }

    /* ── DAMAGE BADGES ── */
    .damage-badge {
        display: inline-flex; align-items: center; gap: 0.3rem;
        padding: 0.3rem 0.8rem;
        border-radius: 8px;
        font-family: 'DM Mono', monospace;
        font-size: 0.75rem; font-weight: 500;
        margin: 0.2rem;
    }
    .db-crack   { background:#0c1a2e; color:#60a5fa; border:1px solid #1e3a5f; }
    .db-pothole { background:#1a0a0a; color:#f87171; border:1px solid #3b1f1f; }
    .db-other   { background:#1a1500; color:#fbbf24; border:1px solid #3d2f00; }

    /* ── PROGRESS BAR ── */
    .prog-wrap { margin-top: 0.6rem; }
    .prog-bg {
        background: var(--border);
        border-radius: 999px;
        height: 6px;
        overflow: hidden;
    }
    .prog-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #22c55e 0%, #eab308 50%, #ef4444 100%);
        transition: width 0.6s ease;
    }

    /* ── SECTION HEADERS ── */
    .section-header {
        font-family: 'Syne', sans-serif;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--muted);
        margin: 1.5rem 0 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-header::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }

    /* ── DASHBOARD REPORT CARD ── */
    .report-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        display: grid;
        grid-template-columns: 80px 1fr auto;
        gap: 1rem;
        align-items: center;
        transition: border-color 0.2s;
    }
    .report-card:hover { border-color: var(--accent); }
    .report-thumb {
        width: 80px; height: 60px;
        border-radius: 8px;
        object-fit: cover;
        background: var(--surface2);
    }
    .report-info h4 {
        font-family: 'Syne', sans-serif;
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--text);
        margin: 0 0 0.25rem;
    }
    .report-info p {
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        color: var(--muted);
        margin: 0;
    }

    /* ── STAT BOX ── */
    .stat-box {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.25rem;
        text-align: center;
    }
    .stat-box .stat-num {
        font-family: 'Syne', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        color: var(--accent);
        line-height: 1;
        margin-bottom: 0.3rem;
    }
    .stat-box .stat-label {
        font-family: 'DM Mono', monospace;
        font-size: 0.68rem;
        color: var(--muted);
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    /* ── DIVIDER ── */
    .div { border:none; border-top:1px solid var(--border); margin:1.5rem 0; }

    /* ── OVERRIDE STREAMLIT ── */
    .stButton > button {
        background: var(--accent) !important;
        color: #0a0a0a !important;
        font-family: 'DM Mono', monospace !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.5rem !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.05em !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #fbbf24 !important;
        transform: translateY(-1px);
    }
    div[data-testid="stFileUploader"] {
        background: var(--surface);
        border: 2px dashed var(--border);
        border-radius: 14px;
        padding: 1rem;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: var(--accent);
    }
    .stSelectbox > div > div {
        background: var(--surface) !important;
        border-color: var(--border) !important;
        color: var(--text) !important;
    }
    .stRadio > div { gap: 0.5rem; }
    .stRadio label { color: var(--text) !important; }
    img { border-radius: 10px; }
    .stAlert { border-radius: 10px; }
    .stSpinner > div { border-top-color: var(--accent) !important; }
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
    'Longitudinal Crack', 'Transverse Crack', 'Alligator Crack',
    'Other Corruption',   'Pothole'
]
SEVERITY_WEIGHTS  = {0: 0.50, 1: 0.65, 2: 0.85, 3: 0.40, 4: 1.00}
POTHOLE_CLASS_IDX = 4
DEVICE            = "cpu"
AE_PATCH_SIZE     = 128
YOLO_IMGSZ        = 512

# ===========================
# SESSION STATE
# ===========================
if "page" not in st.session_state:
    st.session_state.page = "inspect"

# ===========================
# SUPABASE (city authority reports)
# ===========================
def _supabase_credentials():
    try:
        return st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    except (KeyError, FileNotFoundError, TypeError):
        u = os.environ.get("SUPABASE_URL")
        k = os.environ.get("SUPABASE_KEY")
        return u, k


@st.cache_resource
def get_supabase():
    u, k = _supabase_credentials()
    if not u or not k:
        return None
    return create_client(u, k)


def _storage_public_url(sb, bucket: str, key: str) -> str:
    out = sb.storage.from_(bucket).get_public_url(key)
    if isinstance(out, str):
        return out
    if isinstance(out, dict):
        return out.get("publicUrl") or out.get("public_url") or ""
    return str(out)


def upload_report(img_bgr, vis_rgb, urgency, score, anomaly,
                  detected, num_det, lat, lon, location_str, source):
    sb = get_supabase()
    if sb is None:
        raise RuntimeError(
            "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to "
            ".streamlit/secrets.toml (or environment variables)."
        )
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bucket = "inspectRAIL-images"

    _, orig_buf = cv2.imencode(".jpg", img_bgr)
    orig_key = f"originals/{timestamp}_orig.jpg"
    sb.storage.from_(bucket).upload(
        orig_key,
        orig_buf.tobytes(),
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    orig_url = _storage_public_url(sb, bucket, orig_key)

    _, annot_buf = cv2.imencode(".jpg", cv2.cvtColor(vis_rgb, cv2.COLOR_RGB2BGR))
    annot_key = f"annotated/{timestamp}_annot.jpg"
    sb.storage.from_(bucket).upload(
        annot_key,
        annot_buf.tobytes(),
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    annot_url = _storage_public_url(sb, bucket, annot_key)

    lat_f = float(lat) if lat and str(lat).strip() else None
    lon_f = float(lon) if lon and str(lon).strip() else None

    sb.table("reports").insert({
        "urgency": urgency,
        "score": round(float(score), 4),
        "anomaly": round(float(anomaly), 5),
        "detected": detected,
        "num_det": int(num_det),
        "latitude": lat_f,
        "longitude": lon_f,
        "location_str": location_str or "Not provided",
        "source": source or "unknown",
        "image_url": orig_url,
        "annot_url": annot_url,
    }).execute()


@st.cache_data(ttl=20)
def fetch_reports_from_supabase():
    sb = get_supabase()
    if sb is None:
        return []
    resp = sb.table("reports").select("*").limit(500).execute()
    rows = list(resp.data or [])
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows


def sidebar_report_counts():
    rows = fetch_reports_from_supabase()
    total = len(rows)
    urgent = sum(1 for r in rows if r.get("urgency") == "URGENT")
    high = sum(1 for r in rows if r.get("urgency") == "HIGH")
    return total, urgent, high


# ===========================
# LOAD MODELS
# ===========================
@st.cache_resource
def load_models():
    from ultralytics import YOLO
    original_load = torch.load
    torch.load = functools.partial(original_load, weights_only=False)
    YOLO_PATH = Path("models/best.pt")
    AE_PATH   = Path("models/conv_autoencoder.pth")
    yolo_model = YOLO(str(YOLO_PATH))
    ae_model   = ConvAutoencoder()
    ae_model.load_state_dict(torch.load(str(AE_PATH), map_location=DEVICE, weights_only=False))
    ae_model.eval()
    torch.load = original_load
    return yolo_model, ae_model

# ===========================
# INFERENCE
# ===========================
def compute_anomaly_score(img_bgr, model, patch_size=128, num_patches=4):
    img     = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w    = img.shape[:2]
    y1, y2  = int(0.45*h), int(0.95*h)
    x1, x2  = int(0.10*w), int(0.90*w)
    roi     = img[y1:y2, x1:x2]
    h, w    = roi.shape[:2]
    if h < patch_size or w < patch_size:
        roi  = cv2.resize(roi, (max(patch_size,w), max(patch_size,h)))
        h, w = roi.shape[:2]
    criterion = nn.MSELoss()
    losses = []
    for _ in range(num_patches):
        y = np.random.randint(0, h - patch_size + 1)
        x = np.random.randint(0, w - patch_size + 1)
        patch   = roi[y:y+patch_size, x:x+patch_size].astype(np.float32)/255.0
        patch_t = torch.tensor(np.transpose(patch,(2,0,1)), dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            losses.append(criterion(model(patch_t), patch_t).item())
    return float(np.mean(losses))

def compute_urgency(result, anomaly_score):
    if result.boxes is None or len(result.boxes) == 0:
        return "NORMAL", 0.0, []
    classes = [int(b.cls.item())    for b in result.boxes]
    confs   = [float(b.conf.item()) for b in result.boxes]
    xyxy    = result.boxes.xyxy.cpu().numpy()
    if POTHOLE_CLASS_IDX in classes:
        return "URGENT", 1.0, list({CLASS_NAMES[c] for c in classes})
    area_score = severity_score = 0.0
    count_score = min(1.0, len(classes)/5.0)
    img_h, img_w = result.orig_shape
    image_area   = img_h * img_w
    for c, box, conf in zip(classes, xyxy, confs):
        x1,y1,x2,y2 = box
        area_score     += min(1.0, max(1.0,(x2-x1)*(y2-y1))/image_area*8.0)
        severity_score += SEVERITY_WEIGHTS.get(c,0.4)*conf
    severity_score = min(1.0, severity_score/max(1,len(classes)))
    area_score     = min(1.0, area_score)
    anomaly_norm   = min(1.0, anomaly_score/0.03)
    s = 0.45*severity_score + 0.30*area_score + 0.15*count_score + 0.10*anomaly_norm
    detected = list({CLASS_NAMES[c] for c in classes})
    if s >= 0.67:   return "HIGH",   s, detected
    elif s >= 0.34: return "MEDIUM", s, detected
    elif s >= 0.10: return "LOW",    s, detected
    else:           return "NORMAL", s, detected

def get_damage_badge(name):
    n = name.lower()
    if "pothole" in n: return "db-pothole", "🕳️"
    if "crack"   in n: return "db-crack",   "⚡"
    return "db-other", "⚠️"

def urgency_icon(u):
    return {"NORMAL":"✅","LOW":"🟡","MEDIUM":"🟠","HIGH":"🔴","URGENT":"🚨"}.get(u,"⚪")

def img_to_b64(img_rgb):
    _, buf = cv2.imencode(".jpg", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
    return base64.b64encode(buf).decode()

# ===========================
# SIDEBAR
# ===========================
with st.sidebar:
    st.markdown("""
    <div class="logo-bar">
        <div class="logo-icon">🛣️</div>
        <div class="logo-text">
            <h1>InspectRAIL</h1>
            <p>Road Analysis & Inspection Logic</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Navigation")
    if st.button("🔍  Inspect Road", use_container_width=True):
        st.session_state.page = "inspect"
    if st.button("📊  Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"

    st.markdown("<hr class='div'>", unsafe_allow_html=True)

    # Stats summary in sidebar (from Supabase)
    total, urgent, high = sidebar_report_counts()
    if get_supabase() is None:
        st.caption("Configure Supabase in secrets for live stats.")

    st.markdown("### Quick Stats")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-num">{total}</div>
            <div class="stat-label">Reports</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-box" style="border-color:{'#dc2626' if urgent>0 else 'var(--border)'}">
            <div class="stat-num" style="color:{'#f87171' if urgent>0 else 'var(--accent)'}">
                {urgent}
            </div>
            <div class="stat-label">Urgent</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='div'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-family:'DM Mono',monospace;font-size:0.68rem;color:var(--muted);text-align:center;">
        YOLOv8n · ConvAE · RDD2022<br>
        v1.0.0 — InspectRAIL
    </div>""", unsafe_allow_html=True)

# ===========================
# LOAD MODELS
# ===========================
with st.spinner("Initialising InspectRAIL models..."):
    try:
        yolo_model, ae_model = load_models()
    except Exception as e:
        st.error(f"Model load failed: {e}")
        st.stop()

# ===========================
# PAGE: INSPECT
# ===========================
if st.session_state.page == "inspect":

    st.markdown("""
    <div style="margin-bottom:2rem;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;
                   color:var(--text);margin:0 0 0.3rem;">Road Inspection</h2>
        <p style="font-family:'DM Mono',monospace;font-size:0.75rem;
                  color:var(--muted);margin:0;letter-spacing:0.05em;">
            UPLOAD AN IMAGE OR CAPTURE FROM CAMERA — AI ANALYSES ROAD CONDITION INSTANTLY
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Input Mode ──
    st.markdown('<div class="section-header">Input Method</div>', unsafe_allow_html=True)
    input_mode = st.radio(
        "Input method",
        ["📁  Upload Image", "📷  Camera Capture"],
        horizontal=True,
        label_visibility="collapsed"
    )

    img_bgr    = None
    tmp_path   = None
    source_label = ""

    # ── Upload ──
    if "Upload" in input_mode:
        uploaded = st.file_uploader(
            "Drop a road image here",
            type=["jpg","jpeg","png"],
            label_visibility="collapsed"
        )
        if uploaded:
            suffix = Path(uploaded.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                tmp_path = Path(tmp.name)
            img_bgr      = cv2.imread(str(tmp_path))
            source_label = uploaded.name

    # ── Camera ──
    else:
        st.info("📷 Allow camera access when prompted. Click **Take Photo** to capture.", icon="ℹ️")
        cam_img = st.camera_input("Capture road image", label_visibility="collapsed")
        if cam_img:
            nparr    = np.frombuffer(cam_img.getvalue(), np.uint8)
            img_bgr  = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            suffix   = ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(cam_img.getvalue())
                tmp_path     = Path(tmp.name)
            source_label = f"camera_{datetime.datetime.now().strftime('%H%M%S')}.jpg"

    # ── Location (browser GPS when available) ──
    if img_bgr is not None:
        st.markdown('<div class="section-header">Location (Optional)</div>', unsafe_allow_html=True)
        st.caption(
            "We request your browser’s location once (HTTPS / localhost). "
            "Allow the prompt, or edit coordinates manually."
        )

        def _fill_geo_from_browser() -> None:
            try:
                from streamlit_js_eval import streamlit_js_eval
            except ImportError:
                return
            nonce = st.session_state.get("geo_nonce", 0)
            raw = streamlit_js_eval(
                js_expressions="""
                await new Promise((resolve) => {
                  if (!navigator.geolocation) { resolve(""); return; }
                  navigator.geolocation.getCurrentPosition(
                    (p) => resolve(JSON.stringify({
                      lat: p.coords.latitude,
                      lon: p.coords.longitude
                    })),
                    () => resolve(""),
                    { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
                  );
                })
                """,
                key=f"inspectrail_geo_{nonce}",
                want_output=True,
            )
            if not raw:
                return
            try:
                d = json.loads(raw)
                st.session_state.lat_in = f'{float(d["lat"]):.6f}'
                st.session_state.lon_in = f'{float(d["lon"]):.6f}'
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass

        if "lat_in" not in st.session_state:
            st.session_state.lat_in = ""
        if "lon_in" not in st.session_state:
            st.session_state.lon_in = ""

        cur_img = str(tmp_path) if tmp_path else ""
        if st.session_state.get("_geo_session_key") != cur_img:
            st.session_state._geo_session_key = cur_img
            st.session_state.lat_in = ""
            st.session_state.lon_in = ""
            st.session_state.geo_nonce = st.session_state.get("geo_nonce", 0) + 1
            _fill_geo_from_browser()

        gc1, gc2, gc3 = st.columns([2, 2, 1])
        with gc1:
            lat = st.text_input("Latitude", key="lat_in", placeholder="Auto or e.g. 33.7294")
        with gc2:
            lon = st.text_input("Longitude", key="lon_in", placeholder="Auto or e.g. 73.0931")
        with gc3:
            st.write("")  # align button
            st.write("")
            if st.button("📍 Refresh location"):
                st.session_state.geo_nonce = st.session_state.get("geo_nonce", 0) + 1
                _fill_geo_from_browser()

        location_str = f"{lat}, {lon}" if lat and lon else "Not provided"

    # ── Run Analysis ──
    if img_bgr is not None:
        st.markdown('<div class="section-header">Analysis</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.markdown("**Original**")
            st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), use_column_width=True)

        with st.spinner("Analysing road condition..."):
            pred    = yolo_model.predict(
                source=str(tmp_path), imgsz=YOLO_IMGSZ,
                conf=0.25, device=DEVICE, verbose=False
            )[0]
            anomaly = compute_anomaly_score(img_bgr, ae_model, patch_size=AE_PATCH_SIZE)
            urgency, score, detected = compute_urgency(pred, anomaly)
            vis     = pred.plot()
            vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)

        with col2:
            st.markdown("**Detected Damage**")
            st.image(vis_rgb, use_column_width=True)

        st.markdown("<hr class='div'>", unsafe_allow_html=True)

        # ── Result Cards ──
        rc1, rc2, rc3, rc4 = st.columns(4, gap="small")
        with rc1:
            st.markdown(f"""
            <div class="result-card">
                <div class="label">Urgency Level</div>
                <div class="val u-{urgency}">{urgency_icon(urgency)} {urgency}</div>
            </div>""", unsafe_allow_html=True)
        with rc2:
            num_det = len(pred.boxes) if pred.boxes is not None else 0
            st.markdown(f"""
            <div class="result-card">
                <div class="label">Detections</div>
                <div class="val">{num_det}</div>
            </div>""", unsafe_allow_html=True)
        with rc3:
            st.markdown(f"""
            <div class="result-card">
                <div class="label">Urgency Score</div>
                <div class="val">{round(score*100,1)}%</div>
                <div class="prog-wrap">
                    <div class="prog-bg">
                        <div class="prog-fill" style="width:{round(score*100,1)}%"></div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        with rc4:
            pct = min(100, anomaly/0.03*100)
            st.markdown(f"""
            <div class="result-card">
                <div class="label">Anomaly Score</div>
                <div class="val">{anomaly:.5f}</div>
                <div class="prog-wrap">
                    <div class="prog-bg">
                        <div class="prog-fill" style="width:{pct:.1f}%"></div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

        # ── Damage Types ──
        st.markdown('<div class="section-header">Damage Classification</div>', unsafe_allow_html=True)
        if detected:
            badges = ""
            for d in detected:
                cls, icon = get_damage_badge(d)
                badges += f'<span class="damage-badge {cls}">{icon} {d}</span> '
            st.markdown(badges, unsafe_allow_html=True)
        else:
            st.markdown("""
            <span class="damage-badge db-crack" style="background:#052e16;color:#4ade80;border-color:#166534;">
                ✅ No road damage detected — road appears normal
            </span>""", unsafe_allow_html=True)

        # ── Report Button ──
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("📋  Submit to city dashboard"):
                with st.spinner("Submitting report..."):
                    try:
                        upload_report(
                            img_bgr, vis_rgb, urgency, score, anomaly,
                            detected, num_det, lat, lon, location_str, source_label
                        )
                        st.success("✅ Report submitted. City authorities can view it on the web dashboard.")
                        fetch_reports_from_supabase.clear()
                    except Exception as e:
                        st.error(f"Failed to submit: {e}")

# ===========================
# PAGE: DASHBOARD
# ===========================
elif st.session_state.page == "dashboard":

    try:
        ext_url = str(st.secrets["DASHBOARD_URL"])
    except Exception:
        ext_url = os.environ.get("DASHBOARD_URL", "")
    reports = fetch_reports_from_supabase()

    st.markdown("""
    <div style="margin-bottom:2rem;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;
                   color:var(--text);margin:0 0 0.3rem;">Inspection Dashboard</h2>
        <p style="font-family:'DM Mono',monospace;font-size:0.75rem;
                  color:var(--muted);margin:0;letter-spacing:0.05em;">
            REPORTS SYNCED TO SUPABASE — SAME DATA AS THE CITY WEB DASHBOARD
        </p>
    </div>
    """, unsafe_allow_html=True)
    if ext_url:
        st.markdown(
            f'<p style="font-family:\'DM Mono\',monospace;font-size:0.78rem;">'
            f'Public dashboard: <a href="{ext_url}" target="_blank" rel="noopener">{ext_url}</a></p>',
            unsafe_allow_html=True,
        )
    if get_supabase() is None:
        st.warning(
            "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to "
            ".streamlit/secrets.toml to load reports."
        )

    if not reports:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;background:var(--surface);
                    border:1px solid var(--border);border-radius:16px;">
            <div style="font-size:3rem;margin-bottom:1rem;">📋</div>
            <h3 style="font-family:'Syne',sans-serif;color:var(--text);margin:0 0 0.5rem;">
                No reports yet
            </h3>
            <p style="font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--muted);margin:0;">
                Go to Inspect Road, analyse an image, and click Submit to Dashboard
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        # ── Summary Stats ──
        total  = len(reports)
        urgent = sum(1 for r in reports if r["urgency"] == "URGENT")
        high   = sum(1 for r in reports if r["urgency"] == "HIGH")
        medium = sum(1 for r in reports if r["urgency"] == "MEDIUM")
        low    = sum(1 for r in reports if r["urgency"] in ["LOW","NORMAL"])

        s1, s2, s3, s4, s5 = st.columns(5, gap="small")
        for col, num, label, color in [
            (s1, total,  "Total Reports", "var(--accent)"),
            (s2, urgent, "Urgent",        "#f87171"),
            (s3, high,   "High",          "#f97316"),
            (s4, medium, "Medium",        "#eab308"),
            (s5, low,    "Low / Normal",  "#22c55e"),
        ]:
            with col:
                st.markdown(f"""
                <div class="stat-box" style="border-color:{'#dc2626' if num>0 and color=='#f87171' else 'var(--border)'}">
                    <div class="stat-num" style="color:{color}">{num}</div>
                    <div class="stat-label">{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<hr class='div'>", unsafe_allow_html=True)

        # ── Filters ──
        fc1, fc2, fc3 = st.columns([2,2,3], gap="small")
        with fc1:
            filter_urgency = st.selectbox(
                "Filter by Urgency",
                ["All", "URGENT", "HIGH", "MEDIUM", "LOW", "NORMAL"],
                label_visibility="collapsed"
            )
        with fc2:
            sort_by = st.selectbox(
                "Sort by",
                ["Newest First", "Oldest First", "Highest Urgency", "Lowest Urgency"],
                label_visibility="collapsed"
            )
        with fc3:
            st.markdown(
                f'<p style="font-family:\'DM Mono\',monospace;font-size:0.72rem;'
                f'color:var(--muted);margin:0.6rem 0;">Showing {total} report(s)</p>',
                unsafe_allow_html=True
            )

        # Apply filters
        urgency_order = {"URGENT":0,"HIGH":1,"MEDIUM":2,"LOW":3,"NORMAL":4}
        filtered = [r for r in reports if filter_urgency=="All" or r["urgency"]==filter_urgency]

        def _ts(r):
            return r.get("created_at") or ""

        if sort_by == "Newest First":
            filtered = sorted(filtered, key=_ts, reverse=True)
        elif sort_by == "Oldest First":
            filtered = sorted(filtered, key=_ts)
        elif sort_by == "Highest Urgency":
            filtered = sorted(filtered, key=lambda r: urgency_order.get(r["urgency"],5))
        elif sort_by == "Lowest Urgency":
            filtered = sorted(filtered, key=lambda r: urgency_order.get(r["urgency"],5), reverse=True)

        st.markdown('<div class="section-header">Reports</div>', unsafe_allow_html=True)

        # ── Report Cards ──
        for r in filtered:
            u = r.get("urgency", "")
            icon = urgency_icon(u)
            rid = r.get("id", "")
            ts = r.get("created_at", "")
            loc = r.get("location_str") or "Not provided"

            with st.expander(
                f"{icon}  Report #{rid} — {u}  |  {ts}  |  📍 {loc}",
                expanded=(u in ["URGENT", "HIGH"])
            ):
                ec1, ec2 = st.columns([1,1], gap="large")

                with ec1:
                    st.markdown("**Original Image**")
                    if r.get("image_url"):
                        st.image(r["image_url"], use_column_width=True)
                    else:
                        st.caption("No image URL")

                with ec2:
                    st.markdown("**Annotated Result**")
                    if r.get("annot_url"):
                        st.image(r["annot_url"], use_column_width=True)
                    else:
                        st.caption("No annotated image")

                # Metrics row
                m1, m2, m3, m4 = st.columns(4, gap="small")
                with m1:
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="label">Urgency</div>
                        <div class="val u-{u}">{icon} {u}</div>
                    </div>""", unsafe_allow_html=True)
                with m2:
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="label">Detections</div>
                        <div class="val">{r.get("num_det", 0)}</div>
                    </div>""", unsafe_allow_html=True)
                with m3:
                    sc = float(r.get("score") or 0)
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="label">Urgency Score</div>
                        <div class="val">{round(sc*100,1)}%</div>
                    </div>""", unsafe_allow_html=True)
                with m4:
                    an = r.get("anomaly")
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="label">Anomaly Score</div>
                        <div class="val">{an if an is not None else "—"}</div>
                    </div>""", unsafe_allow_html=True)

                # Damage types
                detected_list = r.get("detected") or []
                if isinstance(detected_list, str):
                    try:
                        detected_list = json.loads(detected_list)
                    except json.JSONDecodeError:
                        detected_list = []
                if detected_list:
                    st.markdown('<div class="section-header">Damage Types</div>', unsafe_allow_html=True)
                    badges = ""
                    for d in detected_list:
                        cls, di = get_damage_badge(d)
                        badges += f'<span class="damage-badge {cls}">{di} {d}</span> '
                    st.markdown(badges, unsafe_allow_html=True)

                # Location
                st.markdown('<div class="section-header">Location & Meta</div>', unsafe_allow_html=True)
                lc1, lc2 = st.columns(2)
                with lc1:
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="label">📍 GPS Coordinates</div>
                        <div style="font-family:'DM Mono',monospace;font-size:0.88rem;
                                    color:var(--accent);margin-top:0.3rem;">
                            {loc}
                        </div>
                    </div>""", unsafe_allow_html=True)
                with lc2:
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="label">🕐 Timestamp</div>
                        <div style="font-family:'DM Mono',monospace;font-size:0.88rem;
                                    color:var(--text);margin-top:0.3rem;">
                            {ts}
                        </div>
                    </div>""", unsafe_allow_html=True)

        # ── Export ──
        st.markdown("<hr class='div'>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
        ex1, ex2 = st.columns([1,4])
        with ex1:
            export_data = []
            for r in reports:
                export_data.append(dict(r))
            st.download_button(
                label="⬇️  Export JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"inspectRAIL_reports_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )
