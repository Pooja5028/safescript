"""
Drug Name Matching Service
--------------------------
Takes raw OCR text and pulls out likely drug names, correcting
common OCR misreads using fuzzy matching against a known drug list.

Endpoint: POST /match  { "text": "<raw ocr text>" }
Response: { "matched_drugs": ["Amoxicillin", "Paracetamol"] }

NOTE FOR THE TEAM:
KNOWN_DRUGS below is a small starter list. Replace/extend it with
a proper drug name dataset (e.g. exported from RxNorm or DDInter)
before your real demo.
"""

from flask import Flask, request, jsonify
from rapidfuzz import process, fuzz
import re

app = Flask(__name__)

KNOWN_DRUGS = [
    "Amoxicillin", "Paracetamol", "Ibuprofen", "Metformin",
    "Atorvastatin", "Amlodipine", "Omeprazole", "Azithromycin",
    "Ciprofloxacin", "Losartan", "Aspirin", "Warfarin",
    "Simvastatin", "Metronidazole", "Cetirizine",
]

MATCH_THRESHOLD = 80  # 0-100, higher = stricter matching


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/match", methods=["POST"])
def match():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "No 'text' field provided"}), 400

    # Split OCR text into candidate word/phrase tokens.
    candidates = re.split(r"[\n,;]+", text)
    candidates = [c.strip() for c in candidates if c.strip()]

    matched = []
    for candidate in candidates:
        best = process.extractOne(
            candidate, KNOWN_DRUGS, scorer=fuzz.WRatio
        )
        if best and best[1] >= MATCH_THRESHOLD:
            drug_name = best[0]
            if drug_name not in matched:
                matched.append(drug_name)

    return jsonify({"matched_drugs": matched})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
