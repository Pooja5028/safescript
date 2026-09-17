"""
Drug Info Service
------------------
For each identified drug, looks up what it's actually used for and
returns a short, plain-language description. This turns the app from
"here's what's wrong" into "here's what these medicines are, plus
what's wrong (if anything)".

Endpoint: POST /info   { "drugs": ["Amoxicillin", "Paracetamol"] }
Response: { "drug_info": {
    "Amoxicillin": "Used to treat bacterial infections.",
    "Paracetamol": "Used to relieve pain and reduce fever."
} }

Data source: openFDA drug label API (https://open.fda.gov/apis/drug/label/)
Free, no API key required for light use (an optional free key raises the
rate limit — see README if you hit rate limiting during testing/demo).
"""

from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

# A short fallback description for drugs the FDA API can't find or
# times out on, so the UI never shows a blank/broken entry.
FALLBACK_TEXT = "No plain-language information available for this medicine."

# Small manual cache so demo runs don't hit the FDA API repeatedly.
_cache = {}


def fetch_plain_description(drug_name):
    if drug_name in _cache:
        return _cache[drug_name]

    try:
        response = requests.get(
            FDA_LABEL_URL,
            params={
                "search": f'openfda.generic_name:"{drug_name}"',
                "limit": 1,
            },
            timeout=8,
        )
        if response.status_code != 200:
            _cache[drug_name] = FALLBACK_TEXT
            return FALLBACK_TEXT

        results = response.json().get("results", [])
        if not results:
            _cache[drug_name] = FALLBACK_TEXT
            return FALLBACK_TEXT

        label = results[0]
        # Prescription drugs usually have "indications_and_usage".
        # Over-the-counter drugs usually have "purpose" instead.
        raw_text = None
        if "indications_and_usage" in label:
            raw_text = label["indications_and_usage"][0]
        elif "purpose" in label:
            raw_text = label["purpose"][0]

        if not raw_text:
            _cache[drug_name] = FALLBACK_TEXT
            return FALLBACK_TEXT

        # These fields are written for clinicians and can be long/dense.
        # Trim to the first sentence or ~180 characters as a simple
        # "plain language" pass. This is a basic heuristic, not real
        # NLP simplification -- good enough for a course demo, worth
        # noting as a future-work improvement (e.g. summarizing with
        # a small local model instead of simple truncation).
        first_sentence = raw_text.split(". ")[0].strip()
        short_text = first_sentence[:180]
        if not short_text.endswith("."):
            short_text += "."

        _cache[drug_name] = short_text
        return short_text

    except requests.RequestException:
        _cache[drug_name] = FALLBACK_TEXT
        return FALLBACK_TEXT


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/info", methods=["POST"])
def info():
    data = request.get_json(silent=True) or {}
    drugs = data.get("drugs", [])

    drug_info = {}
    for drug in drugs:
        drug_info[drug] = fetch_plain_description(drug)

    return jsonify({"drug_info": drug_info})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port)
