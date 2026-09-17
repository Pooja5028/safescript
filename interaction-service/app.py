"""
Interaction Check Service
--------------------------
Takes a list of drug names and returns any known interactions
between them, using a local interaction dataset.

Endpoint: POST /check  { "drugs": ["Warfarin", "Aspirin"] }
Response: { "interactions": [
    {"pair": ["Warfarin", "Aspirin"], "severity": "major",
     "description": "Increased risk of bleeding."}
] }

NOTE FOR THE TEAM:
interactions.csv below is a small starter dataset for demo purposes.
Before your real submission, replace it with data exported from
DDInter 2.0 (https://ddinter2.scbdd.com/) — it's free to download,
no account required, and far more complete than this starter file.
"""

from flask import Flask, request, jsonify
import csv
import os

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "interactions.csv")


def load_interactions():
    interactions = []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            interactions.append(row)
    return interactions


INTERACTIONS = load_interactions()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(silent=True) or {}
    drugs = data.get("drugs", [])

    if not drugs or len(drugs) < 2:
        return jsonify({"interactions": []})

    drug_set = {d.lower() for d in drugs}
    found = []

    for row in INTERACTIONS:
        a, b = row["drug_a"].lower(), row["drug_b"].lower()
        if a in drug_set and b in drug_set:
            found.append({
                "pair": [row["drug_a"], row["drug_b"]],
                "severity": row["severity"],
                "description": row["description"],
            })

    return jsonify({"interactions": found})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)
