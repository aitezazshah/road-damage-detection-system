"""
InspectRAIL inference core — used by Streamlit (optional refactor), FastAPI, etc.
"""
from __future__ import annotations

import base64
import functools
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn

# Paths relative to repo root (cwd when running api or streamlit from project root)
MODELS_DIR = Path(os.environ.get("INSPECTRAIL_MODELS_DIR", "models"))
YOLO_PATH = MODELS_DIR / "best.pt"
AE_PATH = MODELS_DIR / "conv_autoencoder.pth"

CLASS_NAMES = [
    "Longitudinal Crack",
    "Transverse Crack",
    "Alligator Crack",
    "Other Corruption",
    "Pothole",
]
SEVERITY_WEIGHTS = {0: 0.50, 1: 0.65, 2: 0.85, 3: 0.40, 4: 1.00}
POTHOLE_CLASS_IDX = 4
DEVICE = "cpu"
AE_PATCH_SIZE = 128
YOLO_IMGSZ = 512


class ConvAutoencoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(16, 3, 3, stride=2, padding=1, output_padding=1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


_yolo_model = None
_ae_model = None


def load_models():
    from ultralytics import YOLO

    global _yolo_model, _ae_model
    if _yolo_model is not None:
        return _yolo_model, _ae_model

    original_load = torch.load
    torch.load = functools.partial(original_load, weights_only=False)
    try:
        _yolo_model = YOLO(str(YOLO_PATH))
        _ae_model = ConvAutoencoder()
        _ae_model.load_state_dict(
            torch.load(str(AE_PATH), map_location=DEVICE, weights_only=False)
        )
        _ae_model.eval()
    finally:
        torch.load = original_load
    return _yolo_model, _ae_model


def compute_anomaly_score(img_bgr, model, patch_size=128, num_patches=4):
    img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    y1, y2 = int(0.45 * h), int(0.95 * h)
    x1, x2 = int(0.10 * w), int(0.90 * w)
    roi = img[y1:y2, x1:x2]
    h, w = roi.shape[:2]
    if h < patch_size or w < patch_size:
        roi = cv2.resize(roi, (max(patch_size, w), max(patch_size, h)))
        h, w = roi.shape[:2]
    criterion = nn.MSELoss()
    losses = []
    gr = int(np.ceil(np.sqrt(num_patches)))
    gc = int(np.ceil(num_patches / max(gr, 1)))
    max_y = max(0, h - patch_size)
    max_x = max(0, w - patch_size)
    for i in range(num_patches):
        ri = i // gc
        ci = i % gc
        y = int((ri + 0.5) / max(gr, 1) * max_y) if max_y > 0 else 0
        x = int((ci + 0.5) / max(gc, 1) * max_x) if max_x > 0 else 0
        y = min(y, max_y)
        x = min(x, max_x)
        patch = roi[y : y + patch_size, x : x + patch_size].astype(np.float32) / 255.0
        patch_t = torch.tensor(np.transpose(patch, (2, 0, 1)), dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            losses.append(criterion(model(patch_t), patch_t).item())
    return float(np.mean(losses))


def compute_urgency(result, anomaly_score):
    if result.boxes is None or len(result.boxes) == 0:
        return "NORMAL", 0.0, []
    classes = [int(b.cls.item()) for b in result.boxes]
    confs = [float(b.conf.item()) for b in result.boxes]
    xyxy = result.boxes.xyxy.cpu().numpy()
    if POTHOLE_CLASS_IDX in classes:
        return "URGENT", 1.0, list({CLASS_NAMES[c] for c in classes})
    area_score = severity_score = 0.0
    count_score = min(1.0, len(classes) / 5.0)
    img_h, img_w = result.orig_shape
    image_area = img_h * img_w
    for c, box, conf in zip(classes, xyxy, confs):
        x1, y1, x2, y2 = box
        area_score += min(
            1.0,
            max(1.0, (x2 - x1) * (y2 - y1)) / image_area * 8.0,
        )
        severity_score += SEVERITY_WEIGHTS.get(c, 0.4) * conf
    severity_score = min(1.0, severity_score / max(1, len(classes)))
    area_score = min(1.0, area_score)
    anomaly_norm = min(1.0, anomaly_score / 0.03)
    s = (
        0.45 * severity_score
        + 0.30 * area_score
        + 0.15 * count_score
        + 0.10 * anomaly_norm
    )
    detected = list({CLASS_NAMES[c] for c in classes})
    if s >= 0.67:
        return "HIGH", s, detected
    if s >= 0.34:
        return "MEDIUM", s, detected
    if s >= 0.10:
        return "LOW", s, detected
    return "NORMAL", s, detected


def analyze_image_bytes(image_bytes: bytes) -> dict:
    """Run YOLO + ConvAE on a JPEG/PNG image; return JSON-serializable dict."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image")

    yolo_model, ae_model = load_models()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        pred = yolo_model.predict(
            source=tmp_path,
            imgsz=YOLO_IMGSZ,
            conf=0.25,
            device=DEVICE,
            verbose=False,
        )[0]
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    anomaly = compute_anomaly_score(img_bgr, ae_model, patch_size=AE_PATCH_SIZE)
    urgency, score, detected = compute_urgency(pred, anomaly)
    vis = pred.plot()
    vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)

    _, annot_buf = cv2.imencode(".jpg", cv2.cvtColor(vis_rgb, cv2.COLOR_RGB2BGR))
    annotated_b64 = base64.b64encode(annot_buf).decode("ascii")

    _, orig_buf = cv2.imencode(".jpg", img_bgr)
    original_b64 = base64.b64encode(orig_buf).decode("ascii")

    num_det = len(pred.boxes) if pred.boxes is not None else 0

    return {
        "urgency": urgency,
        "score": round(float(score), 4),
        "anomaly": round(float(anomaly), 5),
        "detected": detected,
        "num_det": int(num_det),
        "annotated_image_b64": annotated_b64,
        "original_image_b64": original_b64,
    }
