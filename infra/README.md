# VeriFleet on Google Cloud

`bash infra/deploy.sh` is **not** run in CI. A human with a billed project runs it after this increment.

The script must set `DATABASE_URL` (Cloud SQL unix socket), `VERIFLEET_PUBSUB_PUSH=1`, `PUBSUB_TOPIC`, and a **push subscription** to `/api/v1/fleet/pubsub/push`. Then paste the Cloud Run URL into Devpost.

Mandatory contest services: **Cloud Run**, **Cloud SQL**, **Pub/Sub**.

```bash
# From repo root, after gcloud auth and a billed project:
export PROJECT_ID=project-89d8567f-49f2-48bc-a00
export REGION=europe-west1
bash infra/deploy.sh
```

The live URL is printed by the script after deploy. Do not invent one beforehand. `VERIFLEET_SKIP_LLM=1` keeps Gemini/Vertex off so hackathon credits go to Cloud Run / Cloud SQL / Pub/Sub.

The script:

1. Enables Cloud Run, Cloud SQL Admin, Pub/Sub, Secret Manager, Cloud Trace, Vertex AI.
2. Creates a Postgres 15 instance and the `veriagent` database.
3. Creates Pub/Sub topic `invoice.received`.
4. Deploys `core_engine` to Cloud Run with `gemini-3.5-flash` **identified** and `VERIFLEET_SKIP_LLM=1` so this credit-funded service spends Cloud Run / Cloud SQL / Pub/Sub only — it does **not** call Vertex or Gemini. Unset `VERIFLEET_SKIP_LLM` later when you want a live consult (that burns model credits). The script does not set `GEMINI_API_KEY` or `XAI_API_KEY`.

Set `CORS_ORIGINS` to the frontend Cloud Run URL. Min instances stay at 0 after the demo video.

Proof for judges: screenshot of this service in Cloud Run + a live `*.run.app` URL in the video.
