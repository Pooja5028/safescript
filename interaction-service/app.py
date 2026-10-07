"""
Interaction Check Service
--------------------------
Takes a list of drug names and returns any known interactions
between them, using the full DDInter dataset (merged via
build_interactions.py into interactions.csv).

DDInter names drugs by their generic/chemical name, which doesn't
always match the common name a prescription or OCR pass produces
(e.g. "Aspirin" vs DDInter's "Acetylsalicylic acid"). NAME_ALIASES
below maps known common-name mismatches to DDInter's actual name.
If a pair you expect to match still comes back empty, grep
interactions.csv for one of the two drug names to find what DDInter
actually calls it, then add an entry here.

Endpoint: POST /check  { "drugs": ["Warfarin", "Aspirin"] }
Response: { "interactions": [
    {"pair": ["Warfarin", "Aspirin"], "severity": "major",
     "description": "..."}
] }
"""

from flask import Flask, request, jsonify
from itertools import combinations
import csv
import os

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "interactions.csv")

# Common/regional name -> DDInter's canonical name. Add to this as you
# hit more mismatches (see module docstring for how to find them).
NAME_ALIASES = {
    "aspirin": "acetylsalicylic acid",
    "paracetamol": "acetaminophen",
    "hyoscine": "scopolamine",
}


def normalize(name):
    key = name.strip().lower()
    return NAME_ALIASES.get(key, key)


def load_interactions():
    """
    Index interactions by an unordered pair of normalized drug names,
    so a lookup is O(1) regardless of dataset size, and so common-name
    variants (Aspirin vs Acetylsalicylic acid) still match.
    """
    index = {}
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = frozenset({normalize(row["drug_a"]), normalize(row["drug_b"])})
            index[key] = row
    return index


INTERACTIONS = load_interactions()
print(f"Loaded {len(INTERACTIONS)} known drug interactions")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(silent=True) or {}
    drugs = data.get("drugs", [])

    if not drugs or len(drugs) < 2:
        return jsonify({"interactions": []})

    found = []
    for drug_a, drug_b in combinations(drugs, 2):
        key = frozenset({normalize(drug_a), normalize(drug_b)})
        row = INTERACTIONS.get(key)
        if row:
            found.append({
                "pair": [row["drug_a"], row["drug_b"]],
                "severity": row["severity"],
                "description": row["description"],
            })

    return jsonify({"interactions": found})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)