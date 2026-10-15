
import os
import re
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
FALLBACK_TEXT = "No plain-language information available for this medicine."
_cache = {}

def clean_text(value):
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item)
    if not isinstance(value, str):
        return ""

    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""

    sentence = re.split(r"(?<=[.!?])\s+", value, maxsplit=1)[0]
    sentence = sentence[:240].strip()

    if sentence and sentence[-1] not in ".!?":
        sentence += "..."

    return sentence

def fetch_plain_description(drug_name):
    name = str(drug_name).strip()
    if not name:
        return FALLBACK_TEXT

    cache_key = name.lower()
    if cache_key in _cache:
        return _cache[cache_key]

    search_fields = [
        "active_ingredient",
        "openfda.generic_name",
        "openfda.brand_name",
        "openfda.substance_name",
    ]

    try:
        for field in search_fields:
            response = requests.get(
                FDA_LABEL_URL,
                params={
                    "search": f'{field}:"{name}"',
                    "limit": 5,
                },
                timeout=8,
            )

            if response.status_code != 200:
                continue

            results = response.json().get("results", [])

            for label in results:
                for key in ("indications_and_usage", "purpose"):
                    description = clean_text(label.get(key))
                    if description:
                        _cache[cache_key] = description
                        return description

    except (requests.RequestException, ValueError) as error:
        app.logger.warning("Medicine lookup failed for %s: %s", name, error)

    _cache[cache_key] = FALLBACK_TEXT
    return FALLBACK_TEXT

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/info", methods=["POST"])
def info():
    data = request.get_json(silent=True) or {}
    drugs = data.get("drugs", [])

    if not isinstance(drugs, list):
        return jsonify({"error": "'drugs' must be a list"}), 400

    drug_info = {}

    for drug in drugs:
        if isinstance(drug, str):
            drug_info[drug] = fetch_plain_description(drug)

    return jsonify({"drug_info": drug_info})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port)
