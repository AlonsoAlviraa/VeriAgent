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
DB_PASS="${POSTGRES_PASSWORD:-securepassword}"

gcloud config set project "$PROJECT_ID"
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudtrace.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  compute.googleapis.com

if ! gcloud sql instances describe "$INSTANCE" --quiet >/dev/null 2>&1; then
  gcloud sql instances create "$INSTANCE" \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region="$REGION" \
    --root-password="$DB_PASS"
fi

gcloud sql users create "$DB_USER" --instance="$INSTANCE" --password="$DB_PASS" || true
gcloud sql databases create "$DB_NAME" --instance="$INSTANCE" || true
gcloud pubsub topics create invoice.received || true

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
for MEMBER_ROLE in \
  "serviceAccount:${COMPUTE_SA}=roles/storage.admin" \
  "serviceAccount:${COMPUTE_SA}=roles/logging.logWriter" \
  "serviceAccount:${COMPUTE_SA}=roles/artifactregistry.admin" \
  "serviceAccount:${COMPUTE_SA}=roles/cloudsql.client" \
  "serviceAccount:${CLOUDBUILD_SA}=roles/cloudbuild.builds.builder" \
  "serviceAccount:${CLOUDBUILD_SA}=roles/storage.admin"
do
  MEMBER="${MEMBER_ROLE%%=*}"
  ROLE="${MEMBER_ROLE#*=}"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="$MEMBER" \
    --role="$ROLE" \
    --quiet >/dev/null || true
done

gcloud artifacts repositories describe verifleet --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create verifleet \
    --repository-format=docker \
    --location="$REGION" \
    --description="VeriFleet contest images"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/verifleet/${SERVICE}:ata"
gcloud builds submit --config infra/cloudbuild.yaml .

CONNECTION="${PROJECT_ID}:${REGION}:${INSTANCE}"
TOPIC="projects/${PROJECT_ID}/topics/invoice.received"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@/${DB_NAME}?host=/cloudsql/${CONNECTION}"
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "VERIFLEET_GEMINI_MODEL=gemini-3.5-flash,VERIFLEET_SKIP_LLM=1,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},VERIAGENT_AUTO_INIT_DB=1,PUBSUB_TOPIC=${TOPIC},VERIFLEET_PUBSUB_PUSH=1,DATABASE_URL=${DATABASE_URL}" \
  --add-cloudsql-instances "$CONNECTION" \
  --min-instances 0

SERVICE_URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
gcloud pubsub subscriptions create invoice-received-push \
  --topic=invoice.received \
  --push-endpoint="${SERVICE_URL}/api/v1/fleet/pubsub/push" \
  --ack-deadline=60 \
  || true

echo "Deployed ${SERVICE_URL}. Confirm /health, then one wait=false ingest completes."
