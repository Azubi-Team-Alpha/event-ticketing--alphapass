# 🎟️ AlphaPass AWS Serverless Deployment & Infrastructure Playbook

This document is the official infrastructure deployment and operational playbook for **AlphaPass** (Serverless Event Ticketing, Resale Exchange & Governance Platform).

The production architecture strategy is **Automated Direct Serverless Stack (AWS Lambda ZIP + API Gateway + S3 Direct Website Hosting + Amazon DynamoDB)**.

---

## 🏛️ Infrastructure Component Architecture

| Component | AWS Resource | Deployment Method | Configuration File |
| :--- | :--- | :--- | :--- |
| **Frontend Web Client** | AWS S3 Static Website | S3 Direct Sync (`aws s3 sync`) | `infra/modules/s3` |
| **API Entry Point** | Amazon API Gateway REST Proxy | Terraform Resource | `infra/modules/api_gateway` |
| **Backend Compute** | AWS Lambda (Python 3.12 + FastAPI + Mangum) | Terraform ZIP Deployment | `infra/modules/lambda` |
| **Database Storage** | Amazon DynamoDB (12 Tables) | Terraform Modules | `infra/modules/dynamodb` |
| **Media & File Bucket** | Amazon S3 Asset Bucket (`alphapass-assets-dev`) | Terraform Resource | `infra/modules/s3` |
| **Notifications** | Amazon SNS Topic | Terraform Resource | `infra/modules/sns` |
| **IaC Orchestration** | Terraform `>= 1.5.0` | Direct Execution / GitHub Actions | `infra/main.tf` |

---

## 🚀 Step-by-Step Manual Deployment Instructions

### Prerequisites
- Installed AWS CLI (`aws --version`) configured with valid credentials (`aws configure`).
- Installed Terraform (`terraform -v` `>= 1.5.0`).
- Installed Python (`python3 --version` `>= 3.12`).

---

### Step 1: Provision Infrastructure via Terraform
```bash
cd infra/
terraform init
terraform validate
terraform plan -var="environment=dev"
terraform apply -var="environment=dev" -auto-approve
```

---

### Step 2: Capture Environment Outputs
```bash
export FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
export FRONTEND_URL=$(terraform output -raw frontend_website_endpoint)
export API_GATEWAY_URL=$(terraform output -raw api_endpoint)

echo "Frontend S3 URL: http://$FRONTEND_URL"
echo "API Gateway Endpoint: $API_GATEWAY_URL"
```

---

### Step 3: Configure Frontend API Gateway Base URL
Inject the live API Gateway endpoint into `frontend/js/config.js`:

```bash
cat <<EOF > ../frontend/js/config.js
window.ALPHAPASS_API_URL = "$API_GATEWAY_URL";
EOF
```

---

### Step 4: Deploy Static Web Frontend to AWS S3
```bash
aws s3 sync ../frontend/ s3://$FRONTEND_BUCKET \
  --delete \
  --cache-control "max-age=3600,public"
```

Once synced, open `http://$FRONTEND_URL` in your browser to access the live platform.

---

## 🔄 GitHub Actions CI/CD Workflows

The repository contains automated GitHub Actions workflows under `.github/workflows/`:

### 1. Automated Deployment Pipeline ([.github/workflows/deploy.yml](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/.github/workflows/deploy.yml))
Triggered on `push` or `pull_request` to `main`, or via manual **Workflow Dispatch**:

- **Stage 1 (Test)**: Runs `pytest` test suite across all 42 backend unit/integration tests.
- **Stage 2 (Package)**: Prepares production Python dependencies for Lambda packaging.
- **Stage 3 (Deploy)**: Executes `terraform apply`, updates Lambda code, injects live API Gateway URL into `frontend/js/config.js`, syncs static frontend files to S3, and posts deployment summary details.

### 2. Manual Infrastructure Teardown Workflow ([.github/workflows/teardown.yml](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/.github/workflows/teardown.yml))
Destroys all provisioned AWS cloud infrastructure on demand from GitHub Actions UI:

1. Go to **Actions** -> **AlphaPass Infrastructure Teardown**.
2. Click **Run workflow**.
3. Type `"DESTROY"` into the text input to confirm deletion.
4. Purges all S3 buckets (including versioned objects & delete markers) and executes `terraform destroy`.

---

## 🔐 Required GitHub Repository Secrets

Configure the following secrets in GitHub under **Settings > Secrets and variables > Actions**:

| Secret Name | Description | Example Value |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | IAM User Access Key ID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | IAM User Secret Access Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS Deployment Region | `us-east-1` |
| `JWT_SECRET_KEY` | Secret Key for JWT Token Generation | `super-secret-jwt-signing-key` |

---

## 🛠️ Environment Variables Reference (`.env`)

```env
# APP
APP_NAME="AlphaPass API"
APP_VERSION="2.0.0"
DEBUG=False

# JWT SECURITY
SECRET_KEY="alphapass-jwt-secret-key-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AWS CONFIGURATION
AWS_REGION="us-east-1"
S3_BUCKET_NAME="alphapass-assets-dev"
SES_SENDER_EMAIL="noreply@alphapass.alphateam.live"

# DYNAMODB TABLES
EVENTS_TABLE="alphapass-events-dev"
REGISTRATIONS_TABLE="alphapass-registrations-dev"
ORGANIZERS_TABLE="alphapass-organizers-dev"
ADMINS_TABLE="alphapass-admins-dev"
ORDERS_TABLE="alphapass-orders-dev"
TICKETS_TABLE="alphapass-tickets-dev"
PROMO_CODES_TABLE="alphapass-promo-codes-dev"
RESALE_LISTINGS_TABLE="alphapass-resale-listings-dev"
TRANSFERS_TABLE="alphapass-transfers-dev"
PAYOUTS_TABLE="alphapass-payouts-dev"
PLATFORM_SETTINGS_TABLE="alphapass-platform-settings-dev"
AUDIT_LOGS_TABLE="alphapass-audit-logs-dev"
EVENT_CATEGORIES_TABLE="alphapass-event-categories-dev"
```

---

## 🧹 Local Clean & Teardown Commands

To completely remove local build artifacts and Python virtualenv caches:

```bash
cd backend
rm -rf .venv/ .pytest_cache/ __pycache__/ app/__pycache__/
```
