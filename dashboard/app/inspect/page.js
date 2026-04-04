"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { submitReportToSupabase } from "@/lib/submitReport";

const URGENCY_STYLE = {
  NORMAL: "#22c55e",
  LOW: "#eab308",
  MEDIUM: "#f97316",
  HIGH: "#ef4444",
  URGENT: "#dc2626",
};

export default function InspectPage() {
  const [mode, setMode] = useState("upload");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [result, setResult] = useState(null);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [geoHint, setGeoHint] = useState(null);
  const [sourceLabel, setSourceLabel] = useState("upload.jpg");
  const fileRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const lastAutoGeoKeyRef = useRef(null);
  const [camReady, setCamReady] = useState(false);

  const runAnalysis = useCallback(async (file) => {
    if (!file) return;
    setErr(null);
    setResult(null);
    setLat("");
    setLon("");
    setGeoHint(null);
    lastAutoGeoKeyRef.current = null;
    setBusy(true);
    setSourceLabel(file.name || "capture.jpg");
    try {
      const fd = new FormData();
      fd.append("file", file, file.name || "road.jpg");
      const res = await fetch("/api/analyze", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.detail || `Analysis failed (${res.status})`);
      }
      setResult(data);
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const onFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) runAnalysis(f);
  };

  const startCamera = async () => {
    setErr(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCamReady(true);
    } catch (e) {
      setErr("Camera access denied or unavailable.");
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCamReady(false);
  };

  const requestDeviceLocation = useCallback((opts = {}) => {
    const { onlyIfEmpty = false } = opts;
    if (typeof window === "undefined" || !navigator.geolocation) {
      setGeoHint("Geolocation is not supported in this browser.");
      return;
    }
    setGeoHint("Requesting location…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const la = pos.coords.latitude.toFixed(6);
        const lo = pos.coords.longitude.toFixed(6);
        if (onlyIfEmpty) {
          setLat((prev) => (prev && String(prev).trim() !== "" ? prev : la));
          setLon((prev) => (prev && String(prev).trim() !== "" ? prev : lo));
        } else {
          setLat(la);
          setLon(lo);
        }
        setGeoHint("Filled from your device (browser GPS). You can edit if needed.");
      },
      () => {
        setGeoHint(
          "Could not read location (permission denied or unavailable). Enter coordinates manually or submit without.",
        );
      },
      { enableHighAccuracy: true, timeout: 25000, maximumAge: 0 },
    );
  }, []);

  /** After each new analysis result, request GPS once — does not overwrite typed coords. */
  useEffect(() => {
    if (!result?.annotated_image_b64) return;
    const key = result.annotated_image_b64.slice(0, 80);
    if (lastAutoGeoKeyRef.current === key) return;
    lastAutoGeoKeyRef.current = key;
    requestDeviceLocation({ onlyIfEmpty: true });
  }, [result, requestDeviceLocation]);

  const capturePhoto = async () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);
    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.92),
    );
    stopCamera();
    if (blob) {
      const file = new File([blob], `camera_${Date.now()}.jpg`, {
        type: "image/jpeg",
      });
      runAnalysis(file);
    }
  };

  const submitCity = async () => {
    if (!result) return;
    setErr(null);
    setBusy(true);
    try {
      const locationStr =
        lat && lon ? `${lat}, ${lon}` : lat || lon ? `${lat}${lon}` : "Not provided";
      await submitReportToSupabase({
        originalImageB64: result.original_image_b64,
        annotatedImageB64: result.annotated_image_b64,
        urgency: result.urgency,
        score: result.score,
        anomaly: result.anomaly,
        detected: result.detected,
        numDet: result.num_det,
        lat,
        lon,
        locationStr,
        source: sourceLabel,
      });
      alert("Report submitted to the city dashboard.");
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "1.5rem" }}>
      <div style={{ marginBottom: "1.75rem" }}>
        <h1
          style={{
            fontFamily: "Syne, sans-serif",
            fontSize: "1.75rem",
            fontWeight: 800,
            margin: "0 0 0.35rem",
          }}
        >
          Road inspection
        </h1>
        <p
          style={{
            fontFamily: "DM Mono, monospace",
            fontSize: "0.75rem",
            color: "var(--muted)",
            margin: 0,
            letterSpacing: "0.05em",
          }}
        >
          UPLOAD OR USE YOUR CAMERA — AI ANALYSES ROAD CONDITION
        </p>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        {["upload", "camera"].map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              setErr(null);
              if (m !== "camera") stopCamera();
            }}
            style={{
              background: mode === m ? "var(--accent)" : "var(--surface)",
              color: mode === m ? "#0a0a0a" : "var(--muted)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "0.45rem 1rem",
              fontFamily: "DM Mono, monospace",
              fontSize: "0.78rem",
              cursor: "pointer",
              fontWeight: mode === m ? 700 : 500,
            }}
          >
            {m === "upload" ? "📁 Upload" : "📷 Camera"}
          </button>
        ))}
      </div>

      {mode === "upload" && (
        <div
          style={{
            border: "2px dashed var(--border)",
            borderRadius: 14,
            padding: "1.5rem",
            background: "var(--surface)",
            marginBottom: "1.5rem",
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/jpg"
            onChange={onFileChange}
            disabled={busy}
          />
        </div>
      )}

      {mode === "camera" && (
        <div style={{ marginBottom: "1.5rem" }}>
          {!camReady ? (
            <button
              type="button"
              onClick={startCamera}
              disabled={busy}
              style={{
                background: "var(--accent)",
                color: "#0a0a0a",
                border: "none",
                borderRadius: 10,
                padding: "0.6rem 1.25rem",
                fontFamily: "DM Mono, monospace",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Start camera
            </button>
          ) : (
            <div>
              <video
                ref={videoRef}
                playsInline
                muted
                style={{
                  width: "100%",
                  maxWidth: 640,
                  borderRadius: 12,
                  border: "1px solid var(--border)",
                }}
              />
              <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
                <button
                  type="button"
                  onClick={capturePhoto}
                  disabled={busy}
                  style={{
                    background: "var(--accent)",
                    color: "#0a0a0a",
                    border: "none",
                    borderRadius: 10,
                    padding: "0.6rem 1.25rem",
                    fontFamily: "DM Mono, monospace",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Capture & analyse
                </button>
                <button
                  type="button"
                  onClick={stopCamera}
                  style={{
                    background: "var(--surface2)",
                    color: "var(--text)",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: "0.6rem 1.25rem",
                    fontFamily: "DM Mono, monospace",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {busy && (
        <p style={{ fontFamily: "DM Mono, monospace", color: "var(--muted)" }}>
          Analysing…
        </p>
      )}
      {err && (
        <p style={{ color: "#f87171", marginBottom: "1rem", maxWidth: 720 }}>
          {err}
        </p>
      )}

      {result && (
        <>
          <h2
            style={{
              fontFamily: "DM Mono, monospace",
              fontSize: "0.72rem",
              letterSpacing: "0.12em",
              color: "var(--muted)",
              margin: "1.5rem 0 0.75rem",
            }}
          >
            RESULTS
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
              marginBottom: "1rem",
            }}
          >
            <div>
              <p
                style={{
                  fontFamily: "DM Mono, monospace",
                  fontSize: "0.7rem",
                  color: "var(--muted)",
                }}
              >
                Original
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/jpeg;base64,${result.original_image_b64}`}
                alt="Original"
                style={{ width: "100%", borderRadius: 10, border: "1px solid var(--border)" }}
              />
            </div>
            <div>
              <p
                style={{
                  fontFamily: "DM Mono, monospace",
                  fontSize: "0.7rem",
                  color: "var(--muted)",
                }}
              >
                Detected damage
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/jpeg;base64,${result.annotated_image_b64}`}
                alt="Annotated"
                style={{ width: "100%", borderRadius: 10, border: "1px solid var(--border)" }}
              />
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: "0.75rem",
              marginBottom: "1.25rem",
            }}
          >
            {[
              ["Urgency", result.urgency, URGENCY_STYLE[result.urgency] || "#94a3b8"],
              ["Detections", String(result.num_det), "var(--text)"],
              ["Score", `${(result.score * 100).toFixed(1)}%`, "var(--text)"],
              ["Anomaly", String(result.anomaly), "var(--text)"],
            ].map(([label, val, color]) => (
              <div
                key={label}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: "0.85rem",
                }}
              >
                <div
                  style={{
                    fontFamily: "DM Mono, monospace",
                    fontSize: "0.65rem",
                    color: "var(--muted)",
                    marginBottom: "0.35rem",
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontFamily: "Syne, sans-serif",
                    fontWeight: 700,
                    fontSize: "1.1rem",
                    color,
                  }}
                >
                  {val}
                </div>
              </div>
            ))}
          </div>

          <h3
            style={{
              fontFamily: "DM Mono, monospace",
              fontSize: "0.72rem",
              letterSpacing: "0.12em",
              color: "var(--muted)",
              margin: "1rem 0 0.5rem",
            }}
          >
            LOCATION (OPTIONAL) — SUBMIT TO CITY
          </h3>
          <p
            style={{
              fontFamily: "DM Mono, monospace",
              fontSize: "0.72rem",
              color: "var(--muted)",
              margin: "0 0 0.75rem",
              maxWidth: 640,
            }}
          >
            We request your device location automatically after analysis (browser will ask for
            permission on HTTPS). You can edit or use “Refresh location” if needed.
          </p>
          {geoHint && (
            <p
              style={{
                fontFamily: "DM Mono, monospace",
                fontSize: "0.72rem",
                color: "var(--accent2)",
                margin: "0 0 0.75rem",
              }}
            >
              {geoHint}
            </p>
          )}
          <div
            style={{
              display: "flex",
              gap: "0.75rem",
              flexWrap: "wrap",
              marginBottom: "0.75rem",
              alignItems: "center",
            }}
          >
            <input
              placeholder="Latitude"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                borderRadius: 8,
                padding: "0.5rem 0.75rem",
                fontFamily: "DM Mono, monospace",
                fontSize: "0.85rem",
                width: 160,
              }}
            />
            <input
              placeholder="Longitude"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                borderRadius: 8,
                padding: "0.5rem 0.75rem",
                fontFamily: "DM Mono, monospace",
                fontSize: "0.85rem",
                width: 160,
              }}
            />
            <button
              type="button"
              onClick={requestDeviceLocation}
              disabled={busy}
              style={{
                background: "var(--surface2)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                borderRadius: 8,
                padding: "0.5rem 0.9rem",
                fontFamily: "DM Mono, monospace",
                fontSize: "0.75rem",
                cursor: busy ? "wait" : "pointer",
              }}
            >
              📍 Refresh location
            </button>
          </div>
          <button
            type="button"
            onClick={submitCity}
            disabled={busy}
            style={{
              background: "var(--accent)",
              color: "#0a0a0a",
              border: "none",
              borderRadius: 10,
              padding: "0.65rem 1.5rem",
              fontFamily: "DM Mono, monospace",
              fontWeight: 700,
              cursor: busy ? "wait" : "pointer",
            }}
          >
            Submit to city dashboard
          </button>
        </>
      )}
    </main>
  );
}
