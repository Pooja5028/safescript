"""
Load test for SafeScript's gateway endpoint.

WHAT THIS DOES
--------------
Simulates multiple users uploading a report image at the same time,
so you can capture real performance numbers (response times, failure
rates, throughput) for your Review 2/3 "Performance Analysis" slide.

SETUP (do this once)
---------------------
1. pip install locust
2. Put a sample printed report/prescription image in this folder,
   named exactly: sample_report.jpg
   (any printed document image works fine for load testing purposes --
   you're testing performance, not OCR accuracy, here)
3. Update GATEWAY_HOST below to your deployed gateway's hostname.

RUNNING IT
-----------
    locust -f locustfile.py

Then open http://localhost:8089 in your browser, set:
- Number of users: try 20 (matches the "20 concurrent uploads" benchmark
  suggested for your review)
- Spawn rate: 5 (users started per second)
- Host: leave as configured below, or override in the UI

Locust will show live charts of response time and requests/sec. Take
screenshots of these, plus your Grafana Cloud dashboard during the same
test window, for your slides.
"""

from locust import HttpUser, task, between
import os

GATEWAY_HOST = "https://your-gateway-service.onrender.com"
SAMPLE_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "sample_report.jpg")


class SafeScriptUser(HttpUser):
    host = GATEWAY_HOST
    wait_time = between(1, 3)  # seconds between requests per simulated user

    @task
    def upload_report(self):
        if not os.path.exists(SAMPLE_IMAGE_PATH):
            # Fails loudly rather than silently skipping, so you notice
            # the missing sample file immediately instead of getting
            # confusing "0 requests" results.
            raise FileNotFoundError(
                f"Missing {SAMPLE_IMAGE_PATH}. Add a sample_report.jpg "
                "to the load-test folder before running this test."
            )

        with open(SAMPLE_IMAGE_PATH, "rb") as f:
            self.client.post(
                "/api/v1/process-report",
                files={"image": ("sample_report.jpg", f, "image/jpeg")},
                name="/api/v1/process-report",
            )
