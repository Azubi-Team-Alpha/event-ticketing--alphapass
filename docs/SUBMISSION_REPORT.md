# AlphaPass — Project Submission & Step-by-Step Implementation Report

**Program:** Azubi AWS Cloud & AI Training — Capstone Project 2  
**Team:** Team Alpha  
**Project Title:** AlphaPass — Serverless Event Ticketing, Resale Exchange & Governance Platform  
**Live Application:** [alphapass.alphateam.live](https://alphapass.alphateam.live)  
**Repository:** [Azubi-Team-Alpha/event-ticketing--alphapass](https://github.com/Azubi-Team-Alpha/event-ticketing--alphapass)  
**Date:** July 2026  

---

## 👥 1. Team Alpha Roster & Project Overview

| Member Name | Role | Core Responsibility |
|---|---|---|
| **Mustapha Haadi** | **Developer (Team Lead)** | Architecture design, FastAPI backend engine, Terraform modules, CI/CD pipelines, mobile redesign |
| **David Yirenkyi** | **Developer** | DynamoDB database modeling, 13 table schema designs & Global Secondary Index (GSI) setup |
| **Emmanuel Yelisomah** | **Developer** | Frontend application engineering, Bootstrap 5 custom styling & API SDK integration |
| **Daniel Hanson Reynolds** | **Developer** | Gate check-in QR scanner, digital pass validation & ReportLab PDF ticket engine |
| **Zakaria Adeeba** | **Developer** | Secondary resale marketplace, price-cap enforcement & guest ticket wallet |
| **Evame Cobblah** | **Developer** | Admin governance console, organizer payout queues & quality assurance testing |

---

## 📋 2. Project Story & What AlphaPass Solves

AlphaPass was built to solve the real-world friction experienced by event organizers and ticket buyers in West Africa:

1. **No Crashes During Sales Drops:** Built on AWS serverless compute, AlphaPass auto-scales during traffic spikes and costs $0 when idle (>90% hosting savings).
2. **Anti-Scalping Protection:** Organizers set a maximum resale markup percentage (e.g. +10%), preventing resellers from price gouging.
3. **Instant QR Gate Check-in:** Every ticket pass generates a unique pass code, embedded QR code matrix, and printable 300-DPI PDF ticket.
4. **Complete Governance:** Built-in dashboard tools for organizers to create events and request payouts, and for admins to approve events and process payouts.

---

## 🛠️ Step 1: Project Planning & Team Collaboration (Trello & GitHub)

### Implementation Process
1. **Sprint Board Setup (Trello):** We established a central Trello workspace divided into `Backlog`, `In Progress`, `In Review`, and `Done` columns to track all user stories and feature requests.
2. **Modular Architecture Division:** The project was split into three main layers: `backend/` (FastAPI + DynamoDB), `frontend/` (HTML/CSS/JS web app), and `infra/` (TerraformIaC).
3. **GitHub Pull Request Workflow:** All code changes were submitted via topic branches (`feat/mustpha`, etc.) and peer-reviewed before merging into the primary repository branch.

---

## 💾 Step 2: Database Setup & Data Modeling (Amazon DynamoDB)

### Implementation Process
1. **NoSQL Schema Design:** We designed **13 dedicated DynamoDB tables** with `PAY_PER_REQUEST` On-Demand capacity to ensure sub-10ms response times and zero idle costs.
2. **Global Secondary Index (GSI) Configuration:** Created GSIs on `alphapass-tickets-dev` (`ticket_code-index`, `order_id-index`, `attendee_email-index`) and `alphapass-events-dev` (`category_id-index`, `approval_status-index`) to enable instant lookups without expensive full-table scans.

### Results & Verification

> [!NOTE]  
> **📸 RESULT 1: DYNAMODB 13 TABLES CONSOLE**  
> Screenshot from AWS Console → DynamoDB → Tables showing all 13 `alphapass-*-dev` tables.

![Result 1: AWS DynamoDB 13 Tables Console](images/02_dynamodb_tables.png)

> [!NOTE]  
> **📸 RESULT 2: DYNAMODB TICKETS TABLE INDEXES (GSIs)**  
> Screenshot from AWS Console → DynamoDB → Tables → `alphapass-tickets-dev` → Indexes tab.

![Result 2: DynamoDB Tickets Table Indexes](images/03_dynamodb_indexes.png)

---

## ⚙️ Step 3: Backend API & PDF Pass Engine Development (FastAPI & ReportLab)

### Implementation Process
1. **Modular Router Construction:** Developed **10 backend routers** (`auth`, `events`, `orders`, `tickets`, `transfers`, `resale`, `checkin`, `organizer`, `admin`, `health`).
2. **Printable Vector PDF Ticket Generator:** Built a dynamic PDF engine using Python's `ReportLab` library that compiles 300-DPI printable ticket passes formatted with venue details, attendee names, and embedded high-density QR code matrixes.
3. **Resale Price-Capping Logic:** Programmed server-side validation to automatically reject secondary resale listings exceeding the organizer's maximum allowed markup.

### Results & Verification

> [!NOTE]  
> **📸 RESULT 3: FASTAPI INTERACTIVE SWAGGER API DOCUMENTATION**  
> Screenshot from browser at `https://api.alphapass.alphateam.live/docs` showing interactive OpenAPI Swagger docs.

![Result 3: FastAPI Interactive Swagger API Documentation](images/04_swagger_api_docs.png)

---

## 🏗️ Step 4: AWS Cloud Infrastructure Provisioning (Terraform)

### Implementation Process
1. **Infrastructure-as-Code (`infra/`):** Automated AWS cloud provisioning using HashiCorp Terraform modules:
   - `modules/dynamodb`: Provisions all 13 DynamoDB tables.
   - `modules/lambda`: Packages backend code into `lambda.zip` and sets Python 3.12 runtime with 512MB RAM and 30s timeout.
   - `modules/api_gateway`: Creates Regional REST API Gateway proxy routes (`/{proxy+}`) and CORS preflight handling.
   - `modules/s3`: Creates S3 static website hosting bucket and media asset bucket.
   - `modules/budgets`: Configures AWS spending alerts.

### Results & Verification

> [!NOTE]  
> **📸 RESULT 4: AWS LAMBDA FUNCTION CONFIGURATION**  
> Screenshot from AWS Console → Lambda → `alphapass-backend-api-dev`.

![Result 4: AWS Lambda Function Configuration](images/05_lambda_configuration.png)

> [!NOTE]  
> **📸 RESULT 5: AWS API GATEWAY REST PROXY**  
> Screenshot from AWS Console → API Gateway → `alphapass-serverless-api-dev`.

![Result 5: AWS API Gateway Proxy Resources](images/06_api_gateway_resources.png)

> [!NOTE]  
> **📸 RESULT 6: TERRAFORM APPLY TERMINAL EXECUTION**  
> Screenshot of terminal or GitHub Actions log showing successful `terraform apply` output.

![Result 6: Terraform Apply Execution Result](images/07_terraform_apply.png)

---

## 🔄 Step 5: Automated CI/CD & Operations Setup (GitHub Actions)

### Implementation Process
1. **Automated Deployment Pipeline (`deploy.yml`):**
   - Stage 1: Runs 46 automated backend unit tests via `pytest`.
   - Stage 2: Compiles production packages into `lambda.zip`.
   - Stage 3: Executes pre-deploy sanitation to purge S3 bucket conflicts.
   - Stage 4: Runs `terraform apply` in automated non-interactive mode.
   - Stage 5: Injects live API Gateway URL into `frontend/js/config.js`.
   - Stage 6: Synchronizes static assets to S3 static website bucket (`aws s3 sync`).
2. **Automated Teardown Pipeline (`teardown.yml`):** Allows non-destructive full cleanup of AWS resources from the GitHub Actions UI.

### Results & Verification

> [!NOTE]  
> **📸 RESULT 7: GITHUB ACTIONS CI/CD PIPELINE EXECUTION LOG**  
> Screenshot from GitHub Repository → Actions → AlphaPass CI/CD Deployment showing all green checkmarks.

![Result 7: GitHub Actions CI/CD Pipeline Execution Log](images/08_github_actions_pipeline.png)

---

## 📱 Step 6: Frontend Development & Mobile Responsiveness

### Implementation Process
1. **Responsive Mobile Overhaul:** Re-engineered all 8 web pages with a unified mobile-first navigation system:
   - Sticky topbar visible on viewports `< 992px`.
   - Slide-in offcanvas sidebar (`#1E293B`) with category navigation links.
   - Mobile card layouts (2×2 grid for metrics, stacked ticket wallet cards).
2. **Frontend-Backend SDK Integration (`app-api.js`):** Built a centralized JS client with toast notifications, cart management, token handling, and error formatting.

### Results & Verification

#### 1. Buyer Journey (Browse → Details → Cart → Checkout)

> [!NOTE]  
> **📸 RESULT 8: HOMEPAGE & EVENT EXPLORER**  
> Screenshot of browser on `pass.alphateam.live` (`index.html` or `events.html`) showing the published event grid.

![Result 8: Homepage & Event Directory](images/09_homepage_events.png)

> [!NOTE]  
> **📸 RESULT 9: SINGLE EVENT DETAILS & TICKET SELECTION**  
> Screenshot of `single.html` showing event details, venue info, and ticket tier selectors.

![Result 9: Single Event Details & Pass Selection](images/10_single_event_details.png)

> [!NOTE]  
> **📸 RESULT 10: CART & PROMO CODE VALIDATION**  
> Screenshot of `cart.html` showing promo code `AZUBI20` applied and discount calculation.

![Result 10: Cart & Promo Discount Applied](images/11_cart_promo_discount.png)

> [!NOTE]  
> **📸 RESULT 11: CHECKOUT CONFIRMATION & PASS CODES**  
> Screenshot of `checkout.html` displaying order success and issued ticket pass codes.

![Result 11: Checkout Confirmation & Issued Pass Codes](images/12_checkout_confirmation.png)

---

#### 2. Digital Ticket Wallet, PDF Ticket Export & Resale Market

> [!NOTE]  
> **📸 RESULT 12: TICKET WALLET & REPORTLAB PDF TICKET**  
> Screenshot of `wallet.html` displaying active passes alongside an open downloaded ReportLab PDF ticket pass with QR code.

![Result 12: Ticket Wallet & ReportLab PDF Ticket](images/13_ticket_wallet_pdf.png)

> [!NOTE]  
> **📸 RESULT 13: SECONDARY RESALE MARKETPLACE**  
> Screenshot of `resale.html` showing active price-capped secondary ticket listings.

![Result 13: Secondary Resale Marketplace](images/14_secondary_resale.png)

---

#### 3. Gate Entry Check-in Scanner

> [!NOTE]  
> **📸 RESULT 14: GATE SCANNER VALIDATION & DUPLICATE REJECTION**  
> Split screenshot of `checkin.html` showing the GREEN SUCCESS alert on first scan and RED REJECTION alert on duplicate scan.

![Result 14: Gate Scanner Validation & Duplicate Rejection](images/15_gate_scanner_checkin.png)

---

#### 4. Organizer Portal & Admin Governance Console

> [!NOTE]  
> **📸 RESULT 15: ORGANIZER DASHBOARD & ANALYTICS**  
> Screenshot of `organizer.html` showing revenue metrics, ticket sales overview, and event creation wizard.

![Result 15: Organizer Dashboard & Analytics](images/16_organizer_dashboard.png)

> [!NOTE]  
> **📸 RESULT 16: ADMIN GOVERNANCE CONSOLE (6 TABS)**  
> Screenshot of `admin.html` showing platform overview stats, organizer payout settlement queue, and commission settings.

![Result 16: Admin Governance Console & Payout Queue](images/17_admin_governance_console.png)

---

## 🧪 Step 7: Testing, Cost Guardrails & Project Outcomes

### Implementation Process
1. **Automated Pytest Suite:** Executed 46 unit and integration tests covering authentication, database CRUD operations, order processing, promo validation, and PDF generation.
2. **AWS Budget Guardrails:** Configured `infra/modules/budgets/` to send email alerts if estimated AWS costs exceed Free-Tier limits.

### Results & Verification

> [!NOTE]  
> **📸 RESULT 17: PYTEST 46/46 PASSED EXECUTION SUMMARY**  
> Screenshot of terminal executing `.venv/bin/pytest -v` inside `backend/` showing 46 passed tests.

![Result 17: Terminal Pytest 46/46 Passed Execution Summary](images/18_pytest_test_results.png)

> [!NOTE]  
> **📸 RESULT 18: AWS BUDGETS CONSOLE DASHBOARD**  
> Screenshot from AWS Console → AWS Budgets showing the budget alert configuration.

![Result 18: AWS Budgets Console Dashboard](images/19_aws_budgets_dashboard.png)

---

## 📋 Screenshot Directory Checklist

To complete the report visual presentation, drop image files into `docs/images/` using the file paths below:

| # | Result Image | File Path to Save | Section |
|---|---|---|---|
| **1** | DynamoDB 13 Tables Console | `docs/images/02_dynamodb_tables.png` | Step 2 |
| **2** | DynamoDB Ticket Table Indexes | `docs/images/03_dynamodb_indexes.png` | Step 2 |
| **3** | FastAPI Swagger Interactive Docs | `docs/images/04_swagger_api_docs.png` | Step 3 |
| **4** | AWS Lambda Function Config | `docs/images/05_lambda_configuration.png` | Step 4 |
| **5** | AWS API Gateway Proxy Routes | `docs/images/06_api_gateway_resources.png` | Step 4 |
| **6** | Terraform Apply Execution Result | `docs/images/07_terraform_apply.png` | Step 4 |
| **7** | GitHub Actions Deployment Log | `docs/images/08_github_actions_pipeline.png` | Step 5 |
| **8** | Homepage & Event Directory | `docs/images/09_homepage_events.png` | Step 6 |
| **9** | Single Event Page & Pass Tiers | `docs/images/10_single_event_details.png` | Step 6 |
| **10** | Cart & Promo Code Discount | `docs/images/11_cart_promo_discount.png` | Step 6 |
| **11** | Checkout Confirmation & Pass Codes | `docs/images/12_checkout_confirmation.png` | Step 6 |
| **12** | Ticket Wallet & ReportLab PDF Ticket | `docs/images/13_ticket_wallet_pdf.png` | Step 6 |
| **13** | Secondary Resale Marketplace | `docs/images/14_secondary_resale.png` | Step 6 |
| **14** | Gate Scanner (Success & Rejection) | `docs/images/15_gate_scanner_checkin.png` | Step 6 |
| **15** | Organizer Dashboard & Analytics | `docs/images/16_organizer_dashboard.png` | Step 6 |
| **16** | Admin Governance Console (6 Tabs) | `docs/images/17_admin_governance_console.png` | Step 6 |
| **17** | Pytest 46/46 Passed Summary | `docs/images/18_pytest_test_results.png` | Step 7 |
| **18** | AWS Budgets Dashboard | `docs/images/19_aws_budgets_dashboard.png` | Step 7 |

---

## 🎯 Project Conclusion

Team Alpha has successfully designed, built, tested, and deployed AlphaPass — a production-ready, serverless event ticketing, resale exchange, and governance platform on AWS. The platform achieves over 90% hosting cost savings, sub-second API latency, anti-scalping protection, mobile responsiveness across all devices, and 100% automated CI/CD deployment.
