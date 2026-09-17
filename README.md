# SafeScript — Medical Report OCR and Drug Interaction Checker

A cloud-deployed pipeline that reads a printed medical report or prescription,
identifies the medicines mentioned, explains what each one is for, checks
them for known interactions, and returns a plain-language safety summary.

**This is a decision-support demo, not a medical device.** It is not a
substitute for professional medical advice. It is scoped to printed/typed
documents only — handwriting recognition is out of scope (see "Known
limitations" below).

## Architecture

```
User → Dashboard → Gateway (single entry point)
                       ├─ OCR service
                       ├─ Drug matching service
                       ├─ Drug info service   (what each medicine is for)
                       ├─ Interaction check service
                       └─ Summary service
```

The dashboard makes **one** call to the gateway. The gateway internally
calls the other five services in sequence and returns one combined result —
this is the "API Gateway / Backend Orchestrator" pattern, and it's what
lets you demonstrate inter-service orchestration cleanly in your report.

## Project structure

```
safescript/
├── gateway-service/       # Single entry point; orchestrates the pipeline
├── ocr-service/            # Extracts text from uploaded report images (Tesseract)
├── matching-service/       # Corrects OCR errors, matches against known drug names
├── drug-info-service/      # Looks up what each identified drug is used for (openFDA)
├── interaction-service/    # Checks matched drugs against a local interaction dataset
├── summary-service/        # Turns everything into one plain-language summary
├── dashboard/               # Simple HTML/JS frontend, calls the gateway only
├── load-test/                # Locust script for performance benchmarking
└── render.yaml               # Render blueprint — deploys all 6 services + wiring
```

## Running locally (before deploying)

Each service can be run independently for testing:

```bash
cd ocr-service
pip install -r requirements.txt
python app.py
```

Repeat for `matching-service`, `drug-info-service`, `interaction-service`,
and `summary-service` (each has its own `requirements.txt`). `ocr-service`
also requires the Tesseract binary installed on your machine — on
Ubuntu/WSL: `sudo apt install tesseract-ocr`. This is only needed for
*local* testing; the Dockerfile already handles it for deployment.

To test the **gateway** locally, run all five services above first
(default ports 5000–5003, 5005), then:

```bash
cd gateway-service
pip install -r requirements.txt
python app.py
```

It defaults to calling `localhost:<port>` for each service, so no
environment variables are needed for local testing.

## Deploying to Render (free, no credit card)

1. Push this whole `safescript/` folder to a GitHub repository.
2. Go to https://render.com and sign up (GitHub login is easiest).
3. Click **New +** → **Blueprint**, and point it at your GitHub repo.
   Render will read `render.yaml` and set up all 6 services automatically,
   including linking the gateway's environment variables (`OCR_HOST`,
   `MATCHING_HOST`, etc.) to the other services' real hostnames — you
   don't need to manually copy-paste URLs between services.
4. Once deployed, note your gateway's URL, e.g.
   `https://safescript-gateway.onrender.com`.
5. Open `dashboard/index.html`, update `GATEWAY_URL` at the top with your
   real gateway URL (keep the `/api/v1/process-report` path), and open the
   file in a browser (or deploy the dashboard folder as a Render **Static
   Site** for a proper public link).

**Free tier note:** Render's free services "sleep" after 15 minutes of
inactivity and take ~30-60 seconds to wake up on the next request. Before
your live demo, open each service URL once to wake it up a few minutes
in advance. Frame this in your presentation as an accepted trade-off of
free-tier hosting, and mention that Grafana's synthetic monitoring pings
double as a lightweight keep-alive mechanism.

## Load testing (for Review 2/3 "Performance Analysis")

```bash
cd load-test
pip install locust
# add a sample_report.jpg image to this folder first
locust -f locustfile.py
```

Open http://localhost:8089, set ~20 users, and run against your deployed
gateway. Capture the response-time/throughput charts Locust shows you,
alongside your Grafana Cloud dashboard during the same test window, as
your performance benchmark evidence.

## Before your real submission — things to replace

1. **`interaction-service/interactions.csv`** is a small starter file.
   Replace it with a real export from **DDInter 2.0**
   (https://ddinter2.scbdd.com/) — free, downloadable, no signup required.
2. **`matching-service/app.py`**'s `KNOWN_DRUGS` list is a short starter
   list. Expand it with a fuller drug name list (e.g. from RxNorm's
   downloadable files) so matching works on real prescriptions.
3. Add basic authentication and Firebase session logging to the dashboard.
4. Connect Grafana Cloud's free tier to monitor the deployed services.

## Known limitations (state these explicitly in your report — they're
## deliberate scope decisions, not oversights)

- **Handwriting is not supported.** Even 2026 hybrid deep-learning OCR
  research doesn't outperform a general-purpose LLM on handwritten
  prescriptions — it remains a genuinely open research problem. This
  system is scoped to printed/typed reports, prescriptions, and lab
  results.
- **Drug purpose descriptions are simplified via basic truncation of
  FDA label text**, not true NLP summarization — good enough for a
  demo, noted as a future-work improvement.
- **The interaction dataset is a point-in-time snapshot.** A production
  version would need periodic re-syncing with DDInter or an equivalent
  source.

## Team split suggestion

| Person | Owns |
|---|---|
| A | `ocr-service` + `matching-service` |
| B | `drug-info-service` + `interaction-service`, DDInter dataset integration |
| C | `summary-service` + `gateway-service` + Firebase integration |
| D | `dashboard` frontend + Render deployment + `load-test` + monitoring |
