"""
Summary Generator Service
--------------------------
Takes the matched drugs and any found interactions, and produces
a plain-language summary for the end user.

Endpoint: POST /summarize
Body: {
  "matched_drugs": ["Warfarin", "Aspirin"],
  "drug_info": {"Warfarin": "Used to prevent harmful blood clots.",
                 "Aspirin": "Used to relieve pain and reduce fever."},
  "interactions": [
    {"pair": ["Warfarin", "Aspirin"], "severity": "major",
     "description": "Increased risk of bleeding when taken together."}
  ]
}
Response: { "summary": "<plain language text>" }
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

SEVERITY_LANGUAGE = {
    "major": "This is a serious interaction. Please talk to your doctor or pharmacist before taking these together.",
    "moderate": "This interaction is worth mentioning to your doctor or pharmacist at your next visit.",
    "minor": "This is a minor interaction and usually not a major concern, but you can mention it to your pharmacist.",
}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json(silent=True) or {}
    matched_drugs = data.get("matched_drugs", [])
    drug_info = data.get("drug_info", {})
    interactions = data.get("interactions", [])

    lines = []

    if matched_drugs:
        lines.append("Medicines identified in this report:")
        for drug in matched_drugs:
            purpose = drug_info.get(drug, "").strip()
            if purpose:
                lines.append(f"- {drug}: {purpose}")
            else:
                lines.append(f"- {drug}")
    else:
        lines.append("No medicines could be confidently identified in this report.")

    if not interactions:
        lines.append("No known interactions were found between these medicines in our database.")
    else:
        lines.append(f"{len(interactions)} potential interaction(s) found:")
        for item in interactions:
            pair_text = " and ".join(item["pair"])
            advice = SEVERITY_LANGUAGE.get(item["severity"], "Please check with your doctor or pharmacist.")
            lines.append(f"- {pair_text}: {item['description']} {advice}")

    lines.append(
        "This tool is for informational purposes only and is not a substitute "
        "for professional medical advice. Always consult a qualified doctor or pharmacist."
    )

    return jsonify({"summary": "\n".join(lines)})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port)
