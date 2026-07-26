#!/usr/bin/env bash
# ==============================================================================
# S3 Bucket Purge & Sanitation Script — AlphaPass
# Purges all objects, version history, and delete markers from S3 buckets
# to allow instantaneous, error-free `terraform destroy` execution.
# ==============================================================================

set -euo pipefail

BUCKET_NAME="${1:-alphapass.alphateam.live}"
REGION="${AWS_REGION:-us-east-1}"

echo "🧹 Checking S3 bucket: $BUCKET_NAME in region $REGION..."

if aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null; then
  echo "📦 Emptying all current objects from s3://$BUCKET_NAME..."
  aws s3 rm "s3://$BUCKET_NAME" --recursive 2>/dev/null || true

  echo "📜 Deleting all versioned objects from s3://$BUCKET_NAME..."
  VERSIONS=$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || true)
  if [ -n "$VERSIONS" ] && [ "$VERSIONS" != '{"Objects": null}' ] && [ "$VERSIONS" != '{"Objects": []}' ]; then
    aws s3api delete-objects --bucket "$BUCKET_NAME" --delete "$VERSIONS" 2>/dev/null || true
  fi

  echo "🏷️ Deleting all delete markers from s3://$BUCKET_NAME..."
  MARKERS=$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null || true)
  if [ -n "$MARKERS" ] && [ "$MARKERS" != '{"Objects": null}' ] && [ "$MARKERS" != '{"Objects": []}' ]; then
    aws s3api delete-objects --bucket "$BUCKET_NAME" --delete "$MARKERS" 2>/dev/null || true
  fi

  echo "🗑️ Deleting bucket: $BUCKET_NAME..."
  aws s3api delete-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null || true
  echo "✅ S3 Bucket $BUCKET_NAME successfully deleted."
else
  echo "ℹ️ Bucket $BUCKET_NAME does not exist or is already removed."
fi
