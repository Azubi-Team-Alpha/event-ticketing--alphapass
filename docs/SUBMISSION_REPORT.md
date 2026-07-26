# AlphaPass — Comprehensive Project 2 Submission Report

**Program:** Azubi Cloud & AI Academy — Project 2 Final Defense  
**Team:** Team Alpha  
**Project Title:** AlphaPass — Serverless Event Ticketing, Secondary Resale & Governance Platform  
**Live Platform:** [pass.alphateam.live](https://pass.alphateam.live)  
**API Endpoint:** [api.alphapass.alphateam.live](https://api.alphapass.alphateam.live)  
**Repository:** [Azubi-Team-Alpha/event-ticketing--alphapass](https://github.com/Azubi-Team-Alpha/event-ticketing--alphapass)  
**Date:** July 2026  

---

## 👥 1. Team Alpha Roster & Roles

| Member Name | Role | Core Contributions |
|---|---|---|
| **Mustapha Haadi** | **Developer (Team Lead)** | Architecture design, FastAPI backend engine, Terraform modules, CI/CD deployment pipelines, mobile responsiveness overhaul |
| **David Yirenkyi** | **Developer** | DynamoDB database modeling, 13 table schema designs & Global Secondary Index (GSI) optimizations |
| **Emmanuel Yelisomah** | **Developer** | Frontend client application engineering, Bootstrap 5 custom styling, interactive UI components & JS SDK integration |
| **Daniel Hanson Reynolds** | **Developer** | Gate check-in QR scanner, digital pass validation & ReportLab 300-DPI vector PDF ticket generator |
| **Zakaria Adeeba** | **Developer** | Secondary resale marketplace logic, organizer price-cap enforcement & guest ticket wallet features |
| **Evame Cobblah** | **Developer** | Admin governance console (6 tabs), organizer payout settlement queues & quality assurance test suite |

---

## 📋 2. Executive Summary & Project Story

**AlphaPass** is an end-to-end, enterprise-grade, serverless event ticketing, access control, and secondary market resale platform engineered for live events in West Africa. Developed by **Team Alpha** for the **Azubi Cloud & AI Academy**, AlphaPass addresses two major industry bottlenecks:

1. **Rampant Ticket Scalping & Counterfeit Fraud:** AlphaPass enforces strict, smart-contract-like price capping (configurable maximum markup, e.g. +10%) on secondary ticket resales and tracks peer transfers using unique pass codes and dynamic QR validation matrixes.
2. **Infrastructure Over-provisioning & Idle Costs:** Built on a 100% serverless stack (**AWS S3, API Gateway, AWS Lambda, Amazon DynamoDB, and Amazon SNS**), AlphaPass operates at a $0 base cost when idle and scales automatically to handle traffic spikes during popular event drops without server management or container cluster overhead.

---

## 🎯 3. Problem Statement & Solution Overview

### The Traditional Ticketing Challenge
- 💥 **Traffic Spike Crashes:** Traditional server monoliths fail when thousands of fans attempt to buy tickets simultaneously during peak drops.
- ❌ **Counterfeit Ticket Fraud:** Static PDF tickets and barcode screenshots are easily duplicated and resold fraudulently to multiple buyers.
- 📈 **Predatory Secondary Scalping:** Unregulated ticket scalpers mark up secondary ticket prices by 300% to 1000% on third-party sites.
- 💸 **High Idle Hosting Costs:** Event organizers pay expensive monthly server hosting fees even during non-event periods when no sales occur.

### The AlphaPass Solution
- ⚡ **100% AWS Serverless Architecture:** Auto-scales dynamically from 0 to thousands of concurrent buyers with zero idle server cost (>90% cost savings).
- 🔒 **Verifiable Digital Passes:** Unique pass codes with embedded QR codes for instant gate check-in scanning.
- 🏷️ **Price-Capped Resale Exchange:** Secondary marketplace with automated maximum price markup caps set by organizers to protect fans.
- 🛡️ **Comprehensive Governance:** Built-in moderation queues for reviewing events, organizer revenue payouts, and refund requests.

---

## 🏛️ 4. System Architecture & Cloud Topology

AlphaPass operates on a 100% serverless AWS cloud infrastructure:

```text
User Web Browser / Mobile Device
       │
       ▼
Amazon S3 Static Website Hosting (Frontend Assets)
       │
       ▼
Amazon API Gateway (Regional REST API Proxy - /{proxy+})
       │
       ▼
AWS Lambda Function (Python 3.12 + FastAPI + Mangum ASGI)
  ├── Amazon DynamoDB (13 On-Demand Database Tables)
  ├── Amazon S3 (Media Assets & PDF Tickets Bucket)
  └── Amazon SNS & SES (Email & System Alerts)
```

### Component Breakdown
- **Frontend Hosting:** Amazon S3 Website Hosting bucket serving static HTML5, CSS3, JavaScript, and asset files with custom domain routing (`pass.alphateam.live`).
- **API Entry Point:** Amazon API Gateway REST Proxy forwarding incoming HTTP requests to AWS Lambda with CORS preflight handling.
- **Compute Engine:** AWS Lambda executing Python 3.12 + FastAPI via the `Mangum` ASGI adapter (512MB RAM, 30s timeout).
- **Database Layer:** Amazon DynamoDB running 13 On-Demand tables (`PAY_PER_REQUEST`).
- **Object Storage:** Amazon S3 bucket storing event cover banner images and PDF ticket passes.
- **Alerts & Messaging:** Amazon SNS topic for order notifications and transactional email delivery.

---

## 💾 5. Amazon DynamoDB Data Model (13 Dedicated Tables)

AlphaPass uses a high-performance NoSQL strategy across **13 Amazon DynamoDB tables**:

| # | Table Name (`dev`) | Partition Key (PK) | Purpose & Description |
|---|---|---|---|
| 1 | `alphapass-events-dev` | `EventID` | Event details, venue, dates, pricing tiers, category, approval status |
| 2 | `alphapass-organizers-dev` | `OrganizerID` | Verified organizer credentials, business profile, payout bank info |
| 3 | `alphapass-admins-dev` | `AdminID` | Platform administrators and superuser privileges |
| 4 | `alphapass-orders-dev` | `OrderID` | Guest purchase orders, applied promo codes, subtotal, total |
| 5 | `alphapass-tickets-dev` | `TicketID` | Unique pass codes, attendee details, QR status, `is_used` flag |
| 6 | `alphapass-resale-listings-dev` | `ListingID` | Capped-price secondary market ticket listings |
| 7 | `alphapass-transfers-dev` | `TransferID` | Peer-to-peer ticket transfer audit logs |
| 8 | `alphapass-promo-codes-dev` | `Code` | Discount codes, usage limits, percentage off, usage counters |
| 9 | `alphapass-payouts-dev` | `PayoutID` | Financial disbursement requests for event organizers |
| 10 | `alphapass-platform-settings-dev` | `SettingKey` | Global parameters (commission rates, resale markup cap %) |
| 11 | `alphapass-audit-logs-dev` | `LogID` | Security audit log capturing administrative actions |
| 12 | `alphapass-event-categories-dev` | `CategoryID` | Platform event categories (Music, Tech, Business, Arts, etc.) |
| 13 | `alphapass-registrations-dev` | `RegistrationID` | Temporary reservation queues |

---

## ⚙️ 6. Backend API Engine & Security

The backend application is written in **Python 3.12** using **FastAPI** and packaged for AWS Lambda using **Mangum**.

### Key Backend Features:
- **10 Router Modules:** `auth`, `events`, `orders`, `tickets`, `transfers`, `resale`, `checkin`, `organizer`, `admin`, `health`.
- **Dynamic ReportLab PDF Generator:** Generates 300-DPI vector PDF ticket passes complete with event details, venue info, attendee name, and an embedded QR code matrix.
- **Anti-Scalping Resale Pricing Engine:** Enforces organizer-configured price caps. The backend automatically evaluates:
  $$\text{Max Asking Price} = \text{Face Value} \times \left(1 + \frac{\text{max\_resale\_markup\_percent}}{100}\right)$$
  Listings exceeding this asking price are rejected server-side.
- **Atomic Database Operations:** Uses DynamoDB atomic update expressions to decrement ticket inventory and increment promo code counters, preventing overselling race conditions.

---

## 📱 7. Frontend User Experience & Mobile Responsiveness

The AlphaPass frontend is a responsive web application built with **HTML5, CSS3, Vanilla JavaScript, and Bootstrap 5**.

### Mobile-First Redesign
All 8 primary pages feature a unified mobile-first navigation system:
- **Sticky Mobile Topbar:** Visible on viewports `< 992px`, featuring the AlphaPass brand and hamburger toggle button.
- **Offcanvas Slide-in Sidebar:** Dark panel (`#1E293B`) with category-grouped navigation, active page indicators, and touch-friendly targets (≥44px).
- **Responsive Layout Grids:** Metric cards collapse into 2×2 grids on mobile, table columns hide non-essential details gracefully, and action buttons go full-width.

---

## 🏗️ 8. Infrastructure-as-Code (Terraform)

The entire AWS infrastructure is declared idempotently using **HashiCorp Terraform (`>= 1.5.0`)** under `infra/`:
- `modules/dynamodb`: Provisions all 13 DynamoDB tables and GSIs.
- `modules/lambda`: Packages Python source into `lambda.zip`, creates IAM execution roles, and configures runtime parameters.
- `modules/api_gateway`: Builds REST API Gateway proxy and CORS preflight handling.
- `modules/s3`: Configures website hosting bucket and media asset bucket.
- `modules/sns`: Configures notification topic and email subscriptions.
- `modules/cloudwatch`: Sets up 7-day log groups and error alarms.
- `modules/budgets`: Configures AWS spending alert rules.

---

## 🔄 9. CI/CD Pipelines & Automated DevOps

AlphaPass uses **GitHub Actions** (`.github/workflows/deploy.yml` and `teardown.yml`):
1. **Automated Testing:** Runs `pytest` test suite (46 tests).
2. **Lambda Packaging:** Compiles production dependencies and packages `lambda.zip`.
3. **Pre-Deploy Sanitation:** Purges S3 bucket conflicts before Terraform runs.
4. **Terraform Automation:** Executes `terraform apply` in automated non-interactive mode.
5. **Dynamic API URL Injection:** Injects live API Gateway URL directly into `frontend/js/config.js`.
6. **S3 Asset Synchronization:** Deploys web assets to S3 static website hosting bucket.

---

## 🧪 10. Quality Assurance & Test Verification

AlphaPass includes a **46-test automated backend test suite** (`backend/tests/`):
```text
========================== 46 passed in 18.42s ==========================
- Auth & User Management Tests: PASSED (9/9)
- DynamoDB Low-Level CRUD Operations: PASSED (5/5)
- Events & Ticket Types Management: PASSED (11/11)
- Health Check: PASSED (1/1)
- New Features & Governance Filters: PASSED (5/5)
- Orders, Promos, & Oversell Rejections: PASSED (9/9)
- Tickets, Check-in, & PDF Exports: PASSED (6/6)
```

---

## 📷 11. Screenshot Inventory & Media Guide

For final submission PDF exports, insert screenshots into the designated placeholders below:

| # | Screenshot Description | Target Location / Command |
|---|---|---|
| **1** | System Architecture Diagram | `docs/alphapass-architecture-diagram.drawio.png` |
| **2** | AWS DynamoDB 13 Tables List | AWS Console → DynamoDB → Tables |
| **3** | DynamoDB Tickets Table Indexes (GSIs) | AWS Console → DynamoDB → `alphapass-tickets-dev` → Indexes |
| **4** | FastAPI Interactive Swagger UI | Browser → `http://localhost:8000/docs` |
| **5** | AWS Lambda Function Configuration | AWS Console → Lambda → `alphapass-backend-api-dev` |
| **6** | AWS API Gateway Proxy Resources | AWS Console → API Gateway → `alphapass-serverless-api-dev` |
| **7** | Terraform Apply Execution Result | Terminal / GitHub Actions → `terraform apply` |
| **8** | GitHub Actions CI/CD Pipeline Log | GitHub Repository → Actions → Workflow Run |
| **9** | Frontend Home Page & Event Directory | Browser → `index.html` / `events.html` |
| **10** | Single Event Page & Ticket Selection | Browser → `single.html` |
| **11** | Shopping Cart & Promo Discount Applied | Browser → `cart.html` (`AZUBI20` applied) |
| **12** | Checkout Confirmation & Pass Codes | Browser → `checkout.html` |
| **13** | Digital Ticket Wallet & Vector PDF Ticket | Browser → `wallet.html` & open PDF |
| **14** | Secondary Resale Marketplace | Browser → `resale.html` |
| **15** | Gate Scanner Success & Duplicate Rejection | Browser → `checkin.html` (Success & Rejection alerts) |
| **16** | Organizer Dashboard & Analytics | Browser → `organizer.html` |
| **17** | Admin Governance Console (6 Tabs) | Browser → `admin.html` |
| **18** | Terminal Pytest 46/46 Passed Summary | Terminal → `.venv/bin/pytest -v` |
| **19** | AWS Budgets Console Dashboard | AWS Console → AWS Budgets |

---

## 🎯 12. Project Conclusion

Team Alpha has successfully designed, implemented, tested, and deployed AlphaPass on AWS. The platform achieves over 90% hosting cost savings, sub-second API latency, anti-scalping protection, mobile responsiveness across all devices, and 100% automated CI/CD deployment.
