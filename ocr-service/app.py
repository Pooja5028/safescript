"""
OCR Service
-----------
Accepts an uploaded image of a printed medical report/prescription
and returns the extracted raw text using Tesseract OCR.

Endpoint: POST /ocr  (multipart/form-data, field name: "image")
Response: { "text": "<extracted text>" }
"""

from flask import Flask, request, jsonify
from PIL import Image
import pytesseract
import io

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/ocr", methods=["POST"])
def ocr():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided under field 'image'"}), 400

    file = request.files["image"]

    try:
        image = Image.open(io.BytesIO(file.read()))
    except Exception:
        return jsonify({"error": "Could not read image file"}), 400

    # Basic preprocessing: convert to grayscale, which usually
    # improves Tesseract accuracy on scanned/printed documents.
    gray_image = image.convert("L")

    extracted_text = pytesseract.image_to_string(gray_image)

    return jsonify({"text": extracted_text.strip()})


if __name__ == "__main__":
    # Render sets the PORT environment variable; default to 5000 locally.
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
