"""
Drug Name Matching Service
--------------------------
Takes raw OCR text, pulls out drug-name-like candidates from each
line, and fuzzy-matches them against a local list of common drugs.

Deliberately local-only (no network calls): during a live demo,
depending on an external API here means a single slow/failed request
can silently drop a medicine from the results, with no way to explain
why on the spot. Keeping this offline-safe makes the demo predictable.

Endpoint: POST /match  { "text": "<raw ocr text>" }
Response: { "matched_drugs": ["Amoxicillin", "Paracetamol"] }
"""

from flask import Flask, request, jsonify
from rapidfuzz import process, fuzz
import re

app = Flask(__name__)

# 30 common drugs across the categories most likely to appear on a
# printed prescription or lab report. Extend this list as needed --
# it's the single source of truth for what this service can recognize.
KNOWN_DRUGS = [
    # Analgesics / anti-inflammatory
    "Paracetamol", "Ibuprofen", "Aspirin",
    # Antibiotics
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Metronidazole",
    "Clarithromycin", "Doxycycline",
    # Diabetes
    "Metformin", "Glimepiride", "Insulin",
    # Cardiovascular
    "Atorvastatin", "Simvastatin", "Amlodipine", "Losartan",
    "Enalapril", "Warfarin", "Clopidogrel",
    # Gastrointestinal
    "Omeprazole", "Pantoprazole", "Ranitidine", "Domperidone",
    "Hyoscine",
    # Respiratory / allergy
    "Cetirizine", "Loratadine", "Montelukast", "Salbutamol",
    # Other common
    "Levothyroxine", "Prednisolone",
]

MATCH_THRESHOLD = 72 # 0-100, higher = stricter matching


def extract_candidates(text):
    """
    Pull the likely drug-name token out of each OCR'd line.

    Prescription lines are typically formatted like:
        "Omeprazole 20mg (Premio)"
        "Hyoscine 10mg (Hyos) 1 after breakfast"
        "Prescribed: Warfarin 5mg, Aspirin 75mg"

    The drug name is almost always the leading word(s) before the
    first number/dosage. We split on newlines, semicolons, commas,
    AND colons -- so a line like "Prescribed: Warfarin 5mg, Aspirin
    75mg" correctly splits into "Prescribed", "Warfarin 5mg", and
    "Aspirin 75mg" as three separate candidates, instead of being
    treated as one unmatched blob.
    """
    lines = re.split(r"[\n;,:]+", text)
    candidates = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Take words from the start of the line until we hit a digit,
        # a parenthesis, or the end -- that's the drug name portion.
        match = re.match(r"^([A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z\-]*){0,2})", line)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) > 2:
                candidates.append(candidate)

    return candidates


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/match", methods=["POST"])
def match():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "No 'text' field provided"}), 400

    matched = []
    for candidate in extract_candidates(text):
        best = process.extractOne(candidate, KNOWN_DRUGS, scorer=fuzz.WRatio)
        if best and best[1] >= MATCH_THRESHOLD:
            drug_name = best[0]
            if drug_name not in matched:
                matched.append(drug_name)

    return jsonify({"matched_drugs": matched})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)