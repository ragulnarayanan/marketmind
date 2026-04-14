#!/bin/bash
set -e

# ── Config — edit these ───────────────────────────────────────────────────────
PROJECT_ID="your-gcp-project-id"
REGION="us-east1"
JOB_NAME="marketmind-daily-pipeline"
IMAGE="gcr.io/$PROJECT_ID/$JOB_NAME"

echo "=== MarketMind Pipeline Deploy ==="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Image:    $IMAGE"
echo ""

# ── Step 1: Build and push Docker image ──────────────────────────────────────
echo "[1/4] Building and pushing Docker image..."
gcloud builds submit \
  --tag "$IMAGE" \
  --project "$PROJECT_ID"

# ── Step 2: Deploy Cloud Run Job ──────────────────────────────────────────────
echo "[2/4] Deploying Cloud Run Job..."
gcloud run jobs deploy "$JOB_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --memory 1Gi \
  --cpu 1 \
  --task-timeout 1800 \
  --max-retries 2 \
  --service-account "marketmind-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --set-secrets \
    OPENAI_API_KEY=openai-api-key:latest,\
    GOOGLE_API_KEY=google-api-key:latest,\
    NEWSAPI_KEY=newsapi-key:latest,\
    FINNHUB_API_KEY=finnhub-api-key:latest,\
    QDRANT_URL=qdrant-url:latest,\
    QDRANT_API_KEY=qdrant-api-key:latest \
  --set-env-vars \
    GCP_PROJECT_ID="$PROJECT_ID",\
    GCP_REGION="$REGION"

# ── Step 3: Create or update Cloud Scheduler ─────────────────────────────────
echo "[3/4] Setting up Cloud Scheduler..."

# Delete existing job if it exists
gcloud scheduler jobs delete marketmind-daily-brief \
  --location "$REGION" \
  --quiet 2>/dev/null || true

# Create new scheduler job — 6 AM ET (11 AM UTC) Mon-Fri
gcloud scheduler jobs create http marketmind-daily-brief \
  --location "$REGION" \
  --schedule "0 11 * * 1-5" \
  --time-zone "America/New_York" \
  --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
  --http-method POST \
  --oauth-service-account-email \
    "marketmind-backend@$PROJECT_ID.iam.gserviceaccount.com"

# ── Step 4: Test run ──────────────────────────────────────────────────────────
echo "[4/4] Triggering test run..."
gcloud run jobs execute "$JOB_NAME" \
  --region "$REGION" \
  --wait

echo ""
echo "=== Deploy complete ==="
echo "Monitor logs:"
echo "gcloud logging read 'resource.type=cloud_run_job AND"
echo "  resource.labels.job_name=$JOB_NAME' --limit 50"
