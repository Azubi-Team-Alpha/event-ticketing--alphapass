# AlphaPass CI/CD Automation & DevOps Pipeline Guide

> **Azubi Cloud & AI Academy — Project 2 (Team Alpha)**  
> **Automation Engine:** GitHub Actions  
> **Workflows:** `.github/workflows/deploy.yml` and `.github/workflows/teardown.yml`

---

## 1. CI/CD Architecture Overview

The AlphaPass CI/CD pipeline delivers fully automated build, test, infrastructure provisioning, backend deployment, dynamic configuration injection, and static site distribution upon every push to the `main` branch.

```
 [Push to main] ──> [1. Test Stage] ──> [2. Package Stage] ──> [3. Deploy Stage]
                         │                   │                    │
                  (pytest suite)    (Pip manylinux zip)  (Terraform Apply
                   46/46 passed                           & S3 Frontend Sync)
```

---

## 2. Pipeline Stages & Workflow Breakdown

### Stage 1: Automated Unit & Integration Testing
- **Trigger:** Pull requests and pushes to `main`.
- **Environment:** `ubuntu-latest`, Python 3.12.
- **Actions:**
  1. Installs backend dependencies from `backend/requirements.txt`.
  2. Runs `pytest -v` executing all 46 unit, integration, authentication, and DynamoDB database tests.
  3. Fails pipeline immediately if any test fails, blocking deployment to production.

### Stage 2: Cross-Platform Lambda Artifact Packaging
- **Environment:** `ubuntu-latest`, Python 3.12.
- **Actions:**
  1. Compiles production Python packages targeting `--platform manylinux2014_x86_64` to match the AWS Lambda Amazon Linux execution environment.
  2. Uploads the packaged backend artifact (`packaged-backend`) to GitHub Actions artifact storage for Stage 3.

### Stage 3: Infrastructure Sanitation & Provisioning
- **Authentication:** Authenticates to AWS using GitHub Secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).
- **Pre-Deploy Sanitation:**
  - Checks if an existing S3 website bucket (`alphapass-frontend-dev`) exists.
  - Purges versioned objects and delete markers to prevent `BucketAlreadyExists` or `BucketNotEmpty` conflicts.
  - Checks and clears pre-existing AWS Budgets (`alphapass-free-tier-budget-dev`) to prevent duplicate record exceptions during fresh Terraform deployments.
- **Terraform Automation:**
  - Installs HashiCorp Terraform `1.7.0`.
  - Runs `terraform init`.
  - Executes `terraform plan` and `terraform apply -auto-approve`.

### Stage 4: Lambda Application Code Update
- Uses AWS CLI (`aws lambda update-function-code`) to deploy the newly packaged `lambda.zip` artifact to the provisioned Lambda function (`alphapass-backend-api-dev`).

### Stage 5: Dynamic API Gateway URL & Frontend Config Injection
- **Dynamic Configuration:** Extracts the live REST API Gateway base URL from Terraform output:
  ```bash
  API_URL=$(terraform output -raw api_endpoint)
  ```
- **Injects Config:** Dynamically generates `frontend/js/config.js` before syncing assets to S3:
  ```javascript
  /**
   * AlphaPass Global Frontend Configuration
   * Dynamically generated during CI/CD deployment
   */
  window.ALPHAPASS_API_URL = '$API_URL';
  ```
- **Eliminates Hardcoded Endpoints:** Ensures the static frontend always communicates with the matching API Gateway deployment.

### Stage 6: S3 Static Website Distribution
- Executes `aws s3 sync ../frontend/ s3://$BUCKET_NAME --delete --cache-control "max-age=3600,public"`.
- Outputs live URLs (Frontend S3 URL, API Gateway REST URL, Lambda Function Name, S3 Bucket Target) to the GitHub Step Summary and Action Notices.

---

## 3. Automated Infrastructure Teardown Workflow

A dedicated workflow ([.github/workflows/teardown.yml](file://../.github/workflows/teardown.yml)) allows instant, clean teardown of all AWS resources via manual `workflow_dispatch`:

1. Purges all objects, object versions, and delete markers from the S3 hosting and asset buckets.
2. Deletes AWS Budget records.
3. Runs `terraform destroy -auto-approve` to cleanly remove API Gateway, Lambda, IAM Roles, DynamoDB tables, CloudWatch log groups, and SNS topics.

---

## 4. GitHub Repository Secrets Required

To enable the deployment pipeline, configure the following secrets in GitHub Repository Settings (**Settings -> Secrets and variables -> Actions**):

| Secret Name | Description | Example / Value |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | IAM User Access Key ID with Admin / Provisioning privileges | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | IAM User Secret Access Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | Target AWS Region | `us-east-1` |
| `SECRET_KEY` | Secret key for JWT token signing | `alphapass-jwt-production-secret-2026` |
| `SES_SENDER_EMAIL` | Verified AWS SES sender email address | `noreply@alphapass.alphateam.live` |

---

## 5. Local Execution of CI/CD Steps

You can reproduce the CI/CD pipeline locally:

```bash
# 1. Run Tests
cd backend
pytest -v

# 2. Deploy Infrastructure with Terraform
cd ../infra
terraform init
terraform apply -var="environment=dev" -auto-approve

# 3. Update Lambda Code
LAMBDA_NAME=$(terraform output -raw lambda_function_name)
aws lambda update-function-code --function-name "$LAMBDA_NAME" --zip-file "fileb://modules/lambda/lambda.zip"

# 4. Inject Config & Sync S3 Frontend
API_URL=$(terraform output -raw api_endpoint)
BUCKET_NAME=$(terraform output -raw frontend_bucket_name)

echo "window.ALPHAPASS_API_URL = '$API_URL';" > ../frontend/js/config.js
aws s3 sync ../frontend/ s3://$BUCKET_NAME --delete
```
