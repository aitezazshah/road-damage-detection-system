"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  CircleMarker,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix Leaflet default icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const URGENCY_COLORS = {
  URGENT: "#dc2626",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
  NORMAL: "#64748b",
};
const URGENCY_ICONS = {
  URGENT: "🚨",
  HIGH: "🔴",
  MEDIUM: "🟠",
  LOW: "🟡",
  NORMAL: "✅",
};

export default function MapComponent({ reports }) {
  // Calculate center from reports
  const lats = reports.map((r) => r.latitude);
  const lons = reports.map((r) => r.longitude);
  const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
  const centerLon = lons.reduce((a, b) => a + b, 0) / lons.length;

  return (
    <MapContainer
      center={[centerLat, centerLon]}
      zoom={10}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {reports.map((r) => (
        <CircleMarker
          key={r.id}
          center={[r.latitude, r.longitude]}
          radius={r.urgency === "URGENT" ? 14 : r.urgency === "HIGH" ? 11 : 8}
          pathOptions={{
            color: URGENCY_COLORS[r.urgency],
            fillColor: URGENCY_COLORS[r.urgency],
            fillOpacity: 0.85,
            weight: 2,
          }}
        >
          <Popup>
            <div
              style={{
                fontFamily: "DM Mono, monospace",
                fontSize: "0.78rem",
                minWidth: 180,
              }}
            >
              <div
                style={{
                  fontWeight: 700,
                  fontSize: "0.88rem",
                  marginBottom: "0.4rem",
                }}
              >
                {URGENCY_ICONS[r.urgency]} Report #{r.id}
              </div>
              <div
                style={{
                  color: URGENCY_COLORS[r.urgency],
                  fontWeight: 600,
                  marginBottom: "0.3rem",
                }}
              >
                {r.urgency}
              </div>
              {(r.detected || []).length > 0 && (
                <div style={{ marginBottom: "0.3rem" }}>
                  {r.detected.join(", ")}
                </div>
              )}
              <div style={{ opacity: 0.7, fontSize: "0.7rem" }}>
                📍 {r.latitude.toFixed(5)}, {r.longitude.toFixed(5)}
              </div>
              <div
                style={{
                  opacity: 0.7,
                  fontSize: "0.7rem",
                  marginTop: "0.2rem",
                }}
              >
                Score: {(r.score * 100).toFixed(1)}%
              </div>
              {r.image_url && (
                <img
                  src={r.image_url}
                  alt="road"
                  style={{
                    width: "100%",
                    borderRadius: 6,
                    marginTop: "0.5rem",
                  }}
                />
              )}
              <a
                href={`https://www.google.com/maps?q=${r.latitude},${r.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "block",
                  marginTop: "0.5rem",
                  color: "#f59e0b",
                  fontSize: "0.72rem",
                }}
              >
                Open in Google Maps →
              </a>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
