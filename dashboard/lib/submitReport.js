import { supabase } from "@/lib/supabase";

const BUCKET = "inspectRAIL-images";

function b64ToBlob(b64, mime = "image/jpeg") {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime });
}

/**
 * Upload images + insert row — same schema as app.py upload_report.
 */
export async function submitReportToSupabase({
  originalImageB64,
  annotatedImageB64,
  urgency,
  score,
  anomaly,
  detected,
  numDet,
  lat,
  lon,
  locationStr,
  source,
}) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error("Supabase env vars are not set");
  }

  const ts = new Date()
    .toISOString()
    .replace(/[-:TZ.]/g, "")
    .slice(0, 15);
  const origKey = `originals/${ts}_orig.jpg`;
  const annotKey = `annotated/${ts}_annot.jpg`;

  const origBlob = b64ToBlob(originalImageB64);
  const annotBlob = b64ToBlob(annotatedImageB64);

  const { error: e1 } = await supabase.storage
    .from(BUCKET)
    .upload(origKey, origBlob, {
      contentType: "image/jpeg",
      upsert: true,
    });
  if (e1) throw e1;

  const { error: e2 } = await supabase.storage
    .from(BUCKET)
    .upload(annotKey, annotBlob, {
      contentType: "image/jpeg",
      upsert: true,
    });
  if (e2) throw e2;

  const { data: u1 } = supabase.storage.from(BUCKET).getPublicUrl(origKey);
  const { data: u2 } = supabase.storage.from(BUCKET).getPublicUrl(annotKey);

  const latN = lat != null && String(lat).trim() !== "" ? parseFloat(lat) : null;
  const lonN = lon != null && String(lon).trim() !== "" ? parseFloat(lon) : null;

  const { error: e3 } = await supabase.from("reports").insert({
    urgency,
    score: Math.round(score * 1e4) / 1e4,
    anomaly: Math.round(anomaly * 1e5) / 1e5,
    detected,
    num_det: numDet,
    latitude: latN,
    longitude: lonN,
    location_str: locationStr || "Not provided",
    source: source || "inspect-web",
    image_url: u1.publicUrl,
    annot_url: u2.publicUrl,
  });

  if (e3) throw e3;
  return { ok: true };
}
