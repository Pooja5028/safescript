"""
API Gateway / Backend Orchestrator
-----------------------------------
Single entry point for the client. Instead of the dashboard calling
OCR -> matching -> interaction-check -> summary itself (4 separate
network round-trips from the browser), it calls this ONE endpoint,
and the gateway does the internal orchestration server-side.

Endpoint: POST /api/v1/process-report  (multipart/form-data, field: "image")

Response:
{
  "ocr_text": "...",
  "matched_drugs": [...],
  "drug_info": { "Amoxicillin": "Used to treat bacterial infections." },
  "interactions": [...],
  "summary": "...",
  "stage_timings_ms": {
    "ocr": 812,
    "matching": 45,
    "drug_info": 340,
    "interaction_check": 63,
    "summary": 12,
    "total": 1272
  }
}

Each downstream service's location is read from environment variables,
which Render injects automatically when services are linked in
render.yaml via `fromService`. This means you never hardcode URLs —
if a service's host changes, the gateway picks it up automatically.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import os

app = Flask(__name__)
CORS(app)

# Render injects these via render.yaml's `fromService` links.
# Locally, set them yourself (see README) e.g. OCR_HOST=localhost:5000
OCR_HOST = os.environ.get("OCR_HOST", "localhost:5000")
MATCHING_HOST = os.environ.get("MATCHING_HOST", "localhost:5001")
INTERACTION_HOST = os.environ.get("INTERACTION_HOST", "localhost:5002")
SUMMARY_HOST = os.environ.get("SUMMARY_HOST", "localhost:5003")
DRUG_INFO_HOST = os.environ.get("DRUG_INFO_HOST", "localhost:5005")


def service_url(host, path):
    # Render-hosted services need https; localhost testing needs http.
    scheme = "http" if host.startswith("localhost") else "https"
    return f"{scheme}://{host}{path}"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/v1/process-report", methods=["POST"])
def process_report():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided under field 'image'"}), 400

    image_file = request.files["image"]
    image_bytes = image_file.read()
    timings = {}
    overall_start = time.time()

    # ---- Stage 1: OCR ----
    t0 = time.time()
    try:
        ocr_res = requests.post(
            service_url(OCR_HOST, "/ocr"),
            files={"image": (image_file.filename, image_bytes)},
            timeout=30,
        )
        ocr_res.raise_for_status()
        ocr_text = ocr_res.json().get("text", "")
    except requests.RequestException as e:
        return jsonify({"error": f"OCR service failed: {e}"}), 502
    timings["ocr"] = round((time.time() - t0) * 1000)

    # ---- Stage 2: Drug name matching ----
    t0 = time.time()
    try:
        match_res = requests.post(
            service_url(MATCHING_HOST, "/match"),
            json={"text": ocr_text},
            timeout=15,
        )
        match_res.raise_for_status()
        matched_drugs = match_res.json().get("matched_drugs", [])
    except requests.RequestException as e:
        return jsonify({"error": f"Matching service failed: {e}"}), 502
    timings["matching"] = round((time.time() - t0) * 1000)

    # ---- Stage 2.5: Drug info lookup (what each medicine is for) ----
    t0 = time.time()
    try:
        info_res = requests.post(
            service_url(DRUG_INFO_HOST, "/info"),
            json={"drugs": matched_drugs},
            timeout=15,
        )
        info_res.raise_for_status()
        drug_info = info_res.json().get("drug_info", {})
    except requests.RequestException:
        # Non-critical stage: if drug-info lookup fails, don't fail the
        # whole request -- just proceed without the "what is this for"
        # descriptions. Interaction safety info still matters more.
        drug_info = {}
    timings["drug_info"] = round((time.time() - t0) * 1000)

    # ---- Stage 3: Interaction check ----
    t0 = time.time()
    try:
        check_res = requests.post(
            service_url(INTERACTION_HOST, "/check"),
            json={"drugs": matched_drugs},
            timeout=15,
        )
        check_res.raise_for_status()
        interactions = check_res.json().get("interactions", [])
    except requests.RequestException as e:
        return jsonify({"error": f"Interaction service failed: {e}"}), 502
    timings["interaction_check"] = round((time.time() - t0) * 1000)

    # ---- Stage 4: Summary generation ----
    t0 = time.time()
    try:
        summary_res = requests.post(
            service_url(SUMMARY_HOST, "/summarize"),
            json={"matched_drugs": matched_drugs, "interactions": interactions},
            timeout=15,
        )
        summary_res.raise_for_status()
        summary = summary_res.json().get("summary", "")
    except requests.RequestException as e:
        return jsonify({"error": f"Summary service failed: {e}"}), 502
    timings["summary"] = round((time.time() - t0) * 1000)

    timings["total"] = round((time.time() - overall_start) * 1000)

    return jsonify({
        "ocr_text": ocr_text,
        "matched_drugs": matched_drugs,
        "drug_info": drug_info,
        "interactions": interactions,
        "summary": summary,
        "stage_timings_ms": timings,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5004))
    app.run(host="0.0.0.0", port=port)
