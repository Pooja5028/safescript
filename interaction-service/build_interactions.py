"""
One-time build script: merges the raw DDInter category CSVs in
ddinter_raw/ into a single interactions.csv in the format
interaction-service/app.py expects (drug_a,drug_b,severity,description).

Run this once now, and again any time you re-download the raw files:
    python build_interactions.py
"""

import csv
import glob
import os

RAW_DIR = os.path.join(os.path.dirname(__file__), "ddinter_raw")
OUT_FILE = os.path.join(os.path.dirname(__file__), "interactions.csv")

seen = set()
rows_out = []

raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "ddinter_downloads_code_*.csv")))
print(f"Found {len(raw_files)} raw files")

for path in raw_files:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            drug_a = row["Drug_A"].strip()
            drug_b = row["Drug_B"].strip()
            severity = row["Level"].strip().lower()

            if not drug_a or not drug_b or not severity:
                continue

            key = frozenset({drug_a.lower(), drug_b.lower()})
            if key in seen:
                continue
            seen.add(key)

            description = (
                f"DDInter reports a {severity} interaction risk between "
                f"{drug_a} and {drug_b}. Consult a doctor or pharmacist "
                f"before combining these."
            )
            rows_out.append([drug_a, drug_b, severity, description])

print(f"Writing {len(rows_out)} unique interaction pairs to {OUT_FILE}")

with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["drug_a", "drug_b", "severity", "description"])
    writer.writerows(rows_out)

print("Done.")
