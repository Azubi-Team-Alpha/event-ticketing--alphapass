# AlphaPass AWS Infrastructure Architecture Guide

> **Azubi Cloud & AI Academy — Project 2 (Team Alpha)**  
> **Infrastructure Model:** Serverless Multi-Region Ready AWS Stack  
> **IaC Framework:** HashiCorp Terraform (`>= 1.5.0`)

---

## 1. System Architecture Overview

AlphaPass is built on a 100% serverless, event-driven architecture on AWS. The design prioritizes zero infrastructure maintenance overhead, high availability, sub-second latency, strict IAM least-privilege security, and pay-per-use cost efficiency.

```
                   +---------------------------------------+
                   |          End-User Browser             |
                   +-------------------+-------------------+
                                       |
                   +-------------------v-------------------+
                   |         Cloudflare / S3               |
                   |     Static Website Hosting            |
                   +-------------------+-------------------+
                                       | HTTP(S) API Requests
                   +-------------------v-------------------+
                   |        Amazon API Gateway             |
                   |        REST API (Regional)            |
                   +-------------------+-------------------+
                                       | AWS_PROXY Integration
                   +-------------------v-------------------+
                   |          AWS Lambda                   |
                   |     (Python 3.12 + FastAPI)           |
                   +--+----------------+---------------+---+
                      |                |               |
         +------------v---+   +--------v-------+  +----+-----------+
         | Amazon DynamoDB|   |   Amazon S3    |  | Amazon SNS/SES |
         |  (13 Tables)   |   | (Assets/PDFs)  |  | Notifications  |
         +----------------+   +----------------+  +----------------+
```

---

## 2. Infrastructure Component Breakdown

### 2.1 Compute Layer: AWS Lambda
- **Runtime:** Python 3.12 (`runtime = "python3.12"`)
- **Handler:** `index.lambda_handler` (Powered by `Mangum` ASGI adapter wrapping `FastAPI`)
- **Memory & Timeout:** 512 MB RAM, 30-second execution timeout.
- **Packaging:** Automated build zip including FastAPI, Boto3, ReportLab, and Pydantic stripped of development packages.
- **Environment Variables:**
  - `EVENTS_TABLE`, `ORDERS_TABLE`, `TICKETS_TABLE`, `ORGANIZERS_TABLE`, `ADMINS_TABLE`, `PROMO_CODES_TABLE`, `RESALE_LISTINGS_TABLE`, `TRANSFERS_TABLE`, `PAYOUTS_TABLE`, `PLATFORM_SETTINGS_TABLE`, `AUDIT_LOGS_TABLE`, `EVENT_CATEGORIES_TABLE`, `REGISTRATIONS_TABLE`
  - `SECRET_KEY`, `SES_SENDER_EMAIL`, `SNS_TOPIC_ARN`

### 2.2 API Router: Amazon API Gateway
- **Type:** REST API Gateway (Regional)
- **Integration:** `AWS_PROXY` pass-through forwarding all headers, path parameters, query strings, and payloads directly to Lambda.
- **Routes:** Wildcard `{proxy+}` resource catching all routes (`ANY /`) and root (`ANY /`).
- **CORS Management:**
  - Gateway Responses `DEFAULT_4XX` and `DEFAULT_5XX` configured with CORS headers (`Access-Control-Allow-Origin: *`).
  - FastAPI middleware (`CORSMiddleware`) handles application-level OPTIONS preflight requests.

### 2.3 Database Layer: Amazon DynamoDB
AlphaPass uses **13 DynamoDB tables** with `PAY_PER_REQUEST` (On-Demand) billing:

| Table Name | Primary Key (Hash) | Global Secondary Indexes (GSIs) | Key Use Case |
|---|---|---|---|
| `alphapass-events-[env]` | `EventID` (S) | `organizer_id-index`, `status-index` | Event listings, ticket tiers, venue metadata |
| `alphapass-organizers-[env]` | `OrganizerID` (S) | `email-index`, `verification_token-index`, `reset_token-index` | Organizer profiles & authentication |
| `alphapass-admins-[env]` | `AdminID` (S) | `email-index` | Superuser & moderator accounts |
| `alphapass-orders-[env]` | `OrderID` (S) | `event_id-index`, `guest_email-index` | Purchase transactions & payment receipts |
| `alphapass-tickets-[env]` | `TicketID` (S) | `ticket_code-index`, `order_id-index`, `attendee_email-index` | Issued digital tickets & gate check-in status |
| `alphapass-resale-listings-[env]`| `ListingID` (S) | `ticket_id-index`, `status-index` | Secondary peer-to-peer resale tickets |
| `alphapass-transfers-[env]` | `TransferID` (S) | `ticket_id-index` | Pass transfer ownership audit history |
| `alphapass-promo-codes-[env]` | `Code` (S) | `event_id-index` | Discount codes & usage trackers |
| `alphapass-payouts-[env]` | `PayoutID` (S) | `organizer_id-index` | Revenue payout settlement requests |
| `alphapass-platform-settings-[env]`| `SettingKey` (S) | None | Dynamic platform commission & settings |
| `alphapass-audit-logs-[env]` | `LogID` (S) | None | Platform security audit trailing |
| `alphapass-event-categories-[env]`| `CategoryID` (S) | None | System-wide event categories |
| `alphapass-registrations-[env]`| `RegistrationID` (S)| None | Registration queues & temporary holds |

### 2.4 Object Storage: Amazon S3
- **Frontend Hosting Bucket:** `alphapass-frontend-[env]`
  - S3 Website Hosting enabled (`index.html`, error document `404.html`).
  - Public read bucket policy attached with CORS configuration for web assets.
- **Media & Asset Storage:** `alphapass-assets-[env]`
  - Used for storing uploaded event banner images (`POST /events/upload-banner`) and PDF tickets.

### 2.5 Messaging & Notifications: Amazon SNS & SES
- **SNS Topic:** `alphapass-notifications-[env]` publishes order verification and system alert messages.
- **SES (Simple Email Service):** Dispatches HTML transactional emails (ticket delivery, pass transfer alerts, password resets).

### 2.6 Observability & Budget Guardrails
- **CloudWatch Logs:** `/aws/lambda/alphapass-backend-api-[env]` with 7-day retention policy.
- **CloudWatch Alarms:** Triggers SNS email alerts if Lambda error count exceeds 5 errors in 5 minutes.
- **AWS Budgets:** Monthly zero-cost / free-tier budget alert configured to notify team if estimated charges exceed threshold limits.

---

## 3. IAM Least-Privilege Policy

The Lambda execution role (`alphapass-lambda-role-[env]`) is restricted strictly to required AWS resources:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:DescribeTable",
        "dynamodb:TransactWriteItems"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/alphapass-*",
        "arn:aws:dynamodb:*:*:table/alphapass-*/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:*:*:alphapass-*"
    },
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::alphapass-*/*"
    }
  ]
}
```

---

## 4. Terraform Code Directory Structure

```text
infra/
├── main.tf                 # Root Terraform entrypoint connecting all modules
├── variables.tf            # Input variables (environment, aws_region, secret_key)
├── outputs.tf              # Exported outputs (api_endpoint, frontend_url, etc.)
└── modules/
    ├── api_gateway/        # API Gateway REST API, Proxy Resources, Responses
    ├── budgets/            # AWS Budget Cost Alert Module
    ├── cloudwatch/         # CloudWatch Log Group & Error Metric Alarms
    ├── dynamodb/           # 13 DynamoDB Tables & GSI Configurations
    ├── lambda/             # Lambda Function, IAM Role, Policies, ZIP Packager
    ├── s3/                 # S3 Website Hosting Bucket & Bucket Policies
    └── sns/                # SNS Topic & Email Subscriptions
```
