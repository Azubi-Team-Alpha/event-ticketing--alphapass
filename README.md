# 🎟️ AlphaPass (Ticket Hub)
**Serverless Event Ticketing, Secondary Resale Market & Governance Platform**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)](#)
[![DynamoDB](https://img.shields.io/badge/Amazon%20DynamoDB-4053D6?style=for-the-badge&logo=amazondynamodb&logoColor=white)](#)

**AlphaPass** is a secure, high-performance, fully serverless event management, ticketing, and resale platform. Designed on Amazon Web Services (AWS) using FastAPI and DynamoDB, it delivers instant digital QR ticket generation, PDF pass downloads, gate check-in scanning, an organizer dashboard, price-capped secondary ticket resales, peer-to-peer ticket transfers, and administrative platform governance.

*Part of the **Azubi Cloud & AI Academy Internship Portfolio (Project 2 — Team Alpha)**.*

---

## 🌟 Core Features & Modules

- **🌐 Public Event Explorer & Discovery**: Browse live events with category filtering, search, location filtering, and price indicators.
- **🎟️ Single Event Details & Tiered Passes**: View full event metadata, policies, venue details, and dynamic ticket types (General Admission, VIP, Early Bird).
- **🛒 Cart & Guest Checkout System**: Add multiple passes to cart, apply promo codes with atomic usage validation, and execute guest orders using Mobile Money or Card payment options.
- **📱 Digital QR Passes & Printable PDFs**: Generates instant unique QR codes stored in AWS S3 and dynamically renders printable PDF tickets using ReportLab.
- **👛 Ticket Pass Wallet & Peer Transfers**: Search tickets by email/order ID, transfer passes to another attendee with email validation, or list passes on the resale market.
- **🔄 Price-Capped Secondary Resale Exchange**: Allows ticket owners to resell tickets on a fair secondary marketplace enforced with configurable maximum markup percentage caps.
- **💼 Organizer Management Portal**:
  - Event creation with S3 banner image uploads (`POST /events/upload-banner`).
  - Dynamic ticket pass creation modal (`POST /events/organizer/{id}/ticket-types`).
  - Real-time revenue and ticket sales analytics dashboard (`GET /organizer/dashboard`).
  - Gate entry QR scanner console (`POST /checkin/scan`).
  - CSV attendee export (`GET /organizer/events/{id}/attendees?format=csv`).
- **🛡️ Admin Governance & Moderation Console**:
  - Moderation queue for reviewing pending event submissions (`GET /admin/events` & `PUT /admin/events/{id}/approve`).
  - Global platform fee & commission configuration (`PUT /admin/config/commission`).
  - Event category management (`POST /admin/categories`).
  - Platform audit log tracking.

---

## 🏛️ System Architecture

The platform uses a 100% serverless AWS cloud stack with zero base idle cost ($0/month idle):

```mermaid
graph TB
    subgraph Client Tier [🌐 Web Client & Mobile]
        WEB[Static SPA Frontend <br> S3 Web Hosting]
        ORGDASH[Organizer Dashboard & Scanner]
        ADMINDASH[Admin Governance Console]
    end

    subgraph API Gateway & Compute Tier [⚡ Serverless Compute]
        GW[Amazon API Gateway REST Proxy <br> /{proxy+}]
        subgraph LambdaFn [AWS Lambda Function]
            MG[Mangum ASGI Adapter]
            FA[FastAPI Router Engine]
            Auth[JWT Security & Role Control]
        end
    end

    subgraph AWS Database & Storage Tier [🗄️ Database & Storage]
        subgraph DynamoDB [Amazon DynamoDB - 12 Tables]
            T1[(Events Table)]
            T2[(Organizers Table)]
            T3[(Admins Table)]
            T4[(Orders Table)]
            T5[(Tickets Table)]
            T6[(Resale Table)]
            T7[(Transfers Table)]
            T8[(Promo Codes Table)]
            T9[(Payouts Table)]
            T10[(Platform Settings)]
            T11[(Audit Logs)]
            T12[(Event Categories)]
        end
        
        S3[(Amazon S3 Bucket <br> QR Codes, PDFs, Event Banners)]
        SNS[Amazon SNS / SES <br> Booking Notifications]
    end

    %% Flows
    WEB & ORGDASH & ADMINDASH -->|HTTPS REST API & JWT| GW
    GW -->|Event Proxy| MG
    MG --> FA
    FA --> Auth
    FA -->|Single-Table / Multi-Table Operations| DynamoDB
    FA -->|Upload & Download Assets| S3
    FA -->|Publish Alerts| SNS

    %% Custom Styling
    classDef client fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef gw fill:#1e293b,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef lambda fill:#1e293b,stroke:#ff9900,stroke-width:2px,color:#f8fafc;
    classDef db fill:#1e293b,stroke:#4f46e5,stroke-width:2px,color:#f8fafc;
    classDef storage fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc;

    class WEB,ORGDASH,ADMINDASH client;
    class GW gw;
    class MG,FA,Auth,LambdaFn lambda;
    class T1,T2,T3,T4,T5,T6,T7,T8,T9,T10,T11,T12,DynamoDB db;
    class S3,SNS storage;
```

---

## 💾 Serverless Data Model (DynamoDB Tables)

| Table Name | Hash Key | Purpose & Description |
|---|---|---|
| `alphapass-events-[env]` | `EventID` | Event details, venue, dates, status, and nested ticket pass tiers |
| `alphapass-organizers-[env]` | `OrganizerID` | Event organizer profiles, credentials, and verification status |
| `alphapass-admins-[env]` | `AdminID` | Platform admin accounts, permissions, and superuser flags |
| `alphapass-orders-[env]` | `OrderID` | Orders, guest purchaser info, promo applied, total amounts |
| `alphapass-tickets-[env]` | `TicketID` | Unique ticket passes, ticket codes, QR links, scan status (`is_used`) |
| `alphapass-resale-listings-[env]` | `ListingID` | Listed resale passes, asking price, face value, seller/buyer email |
| `alphapass-transfers-[env]` | `TransferID` | Peer-to-peer pass transfer audit history |
| `alphapass-promo-codes-[env]` | `Code` | Discount codes, percent off, max uses, times used |
| `alphapass-payouts-[env]` | `PayoutID` | Organizer earnings payout requests and settlement status |
| `alphapass-platform-settings-[env]` | `SettingKey` | Core configuration settings (e.g. commission rate) |
| `alphapass-audit-logs-[env]` | `LogID` | Governance audit log tracking security events |
| `alphapass-event-categories-[env]` | `CategoryID` | Event category definitions and metadata |

---

## 📡 API Endpoint Overview

### Public & Guest Endpoints
- `GET /health` — Health check
- `GET /events` — List published events (supports `category_id`, `search`, pagination)
- `GET /events/{id}` — Single event details & ticket types
- `GET /events/categories` — List event categories
- `POST /orders` — Create guest order & generate QR ticket passes
- `POST /orders/lookup` — Retrieve ticket wallet by purchaser email / order ID
- `POST /orders/validate-promo` — Validate promo discount code
- `POST /orders/{id}/cancel` — Cancel guest order
- `GET /tickets/{code}` — Fetch ticket details
- `GET /tickets/{code}/pdf` — Download printable ticket PDF
- `GET /resale/listings` — Browse active resale tickets
- `POST /resale/{id}/purchase` — Purchase a resale ticket pass
- `POST /transfers/{code}/transfer` — Transfer ticket pass to another email

### Organizer Portal Endpoints (Auth: `Bearer <organizer_token>`)
- `POST /auth/organizer/signup` — Register organizer account
- `POST /auth/organizer/login` — Authenticate organizer & obtain JWT
- `GET /organizer/dashboard` — Organizer metrics & sales summary
- `GET /events/organizer/my-events` — List organizer's created events
- `POST /events/organizer` — Create new event
- `POST /events/organizer/{id}/publish` — Publish event live
- `POST /events/organizer/{id}/ticket-types` — Add ticket pass type to event
- `POST /events/upload-banner` — Upload cover picture directly to S3
- `GET /organizer/events/{id}/attendees` — Export attendee roster (JSON or CSV)
- `POST /checkin/scan` — Gate entry QR code check-in scanner

### Admin Governance Endpoints (Auth: `Bearer <admin_token>`)
- `POST /auth/admin/login` — Authenticate administrator
- `GET /admin/dashboard` — Platform-wide metrics & fees summary
- `GET /admin/events` — List all events (including drafts and pending)
- `PUT /admin/events/{id}/approve` — Approve or reject pending event
- `PUT /admin/config/commission` — Update global platform commission rate
- `POST /admin/categories` — Create event category

---

## 📁 Repository Structure

```text
alphapass/
├── backend/                  # FastAPI Application Core
│   ├── app/
│   │   ├── core/             # Security (JWT), Config, S3 Uploader, Utils
│   │   ├── db/               # DynamoDB Client Helper
│   │   ├── routers/          # API Routers (events, orders, tickets, checkin, admin, etc.)
│   │   └── schemas/          # Pydantic Input/Output Validation Schemas
│   ├── tests/                # Test suite (42 unit & integration tests)
│   ├── index.py              # AWS Lambda Mangum Handler
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Client SPA Web Pages
│   ├── index.html            # Home page & featured events
│   ├── events.html           # Event explorer & search
│   ├── single.html           # Single event details & pass selection
│   ├── cart.html             # Ticket cart & promo code application
│   ├── checkout.html         # Guest checkout & QR pass modal
│   ├── wallet.html           # Ticket wallet & pass transfers
│   ├── resale.html           # Secondary resale market exchange
│   ├── organizer.html        # Organizer portal & gate entry scanner
│   ├── admin.html            # Admin governance console
│   └── js/                   # Shared API SDK (app-api.js), Config (config.js)
├── docs/                     # Comprehensive Architecture & Integration Docs
│   ├── integration.md        # Full Frontend-Backend SDK Integration Guide
│   ├── deployment.md         # AWS Serverless Deployment & Teardown Playbook
│   └── API_REFERENCE.md      # Full OpenAPI Specification & Endpoint Reference
├── infra/                    # Terraform Infrastructure-as-code Modules
│   ├── modules/              # DynamoDB, Lambda, S3, APIGW, SNS modules
│   └── main.tf               # Terraform main execution file
└── .secrets/                 # Official Project Presentation Deck & Speaker Notes
```

---

## 🚀 Local Development Setup

### 1. Environment Setup & Dependencies
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Local Environment Variables
```bash
cp .env.example .env
```

### 3. Run FastAPI Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Execute Unit & Integration Test Suite
```bash
pytest -v
```

---

## 🛠️ Infrastructure Provisioning (Terraform Direct Serverless Stack)

This project uses **Automated Direct Serverless Stack** (AWS Lambda ZIP + API Gateway + S3 Direct Web Hosting + DynamoDB).

```bash
# 1. Provision AWS Infrastructure
cd infra/
terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev" -auto-approve

# 2. Capture Infrastructure Outputs
export BUCKET_NAME=$(terraform output -raw frontend_bucket_name)
export API_ENDPOINT=$(terraform output -raw api_endpoint)

# 3. Deploy Frontend Assets to S3
aws s3 sync ../frontend/ s3://$BUCKET_NAME --delete --cache-control "max-age=3600,public"
```

---

## 🔄 CI/CD Pipelines & Automated Teardown

- **Deployment Pipeline ([.github/workflows/deploy.yml](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/.github/workflows/deploy.yml))**: Automated testing via `pytest`, infrastructure provisioning with Terraform, Lambda ZIP updating, dynamic API Gateway URL injection into `frontend/js/config.js`, and S3 asset synchronization.
- **Teardown Pipeline ([.github/workflows/teardown.yml](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/.github/workflows/teardown.yml))**: One-click infrastructure destruction from GitHub Actions UI. Deletes versioned S3 objects, clears DynamoDB tables, and tears down all provisioned resources.

---

## 👥 Team Alpha (Project Contributors)
- **Azubi Cloud & AI Academy Internship Program (Project 2 Portfolio)**
- **Team Alpha — AWS Serverless Cloud Architecture**
