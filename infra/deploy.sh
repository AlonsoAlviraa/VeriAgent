#!/usr/bin/env bash
# Deploy VeriFleet backend to Cloud Run + Cloud SQL + Pub/Sub.
# Requires: gcloud, billed GCP project, Docker.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
INSTANCE="${CLOUDSQL_INSTANCE:-verifleet-pg}"
SERVICE="${CLOUD_RUN_SERVICE:-verifleet}"
DB_NAME="${POSTGRES_DB:-veriagent_core}"
DB_USER="${POSTGRES_USER:-veriagent}"

gcloud config set project "$PROJECT_ID"
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudtrace.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com

if ! gcloud sql instances describe "$INSTANCE" --quiet >/dev/null 2>&1; then
  gcloud sql instances create "$INSTANCE" \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region="$REGION"
fi

gcloud sql databases create "$DB_NAME" --instance="$INSTANCE" || true
gcloud pubsub topics create invoice.received || true

IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}:ata"
gcloud builds submit --tag "$IMAGE" --file Dockerfile.backend .

CONNECTION="${PROJECT_ID}:${REGION}:${INSTANCE}"
TOPIC="projects/${PROJECT_ID}/topics/invoice.received"
DB_PASS="${POSTGRES_PASSWORD:-securepassword}"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@/${DB_NAME}?host=/cloudsql/${CONNECTION}"
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "VERIFLEET_GEMINI_MODEL=gemini-3.5-flash,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},VERIAGENT_AUTO_INIT_DB=1,PUBSUB_TOPIC=${TOPIC},VERIFLEET_PUBSUB_PUSH=1,DATABASE_URL=${DATABASE_URL}" \
  --add-cloudsql-instances "$CONNECTION" \
  --min-instances 0

SERVICE_URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
gcloud pubsub subscriptions create invoice-received-push \
  --topic=invoice.received \
  --push-endpoint="${SERVICE_URL}/api/v1/fleet/pubsub/push" \
  --ack-deadline=60 \
  || true

echo "Deployed ${SERVICE_URL}. Confirm /health, then one wait=false ingest completes."
