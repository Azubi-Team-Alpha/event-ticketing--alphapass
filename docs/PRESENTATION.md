# AlphaPass Internship Project Defense & Presentation Guide

> **Azubi Cloud & AI Academy — Project 2 (Team Alpha)**  
> **Topic:** Serverless Event Ticketing, Resale Exchange & Governance Platform  
> **Team Structure:** 3 Presenters (Presenter 1, Presenter 2, Presenter 3)  
> **Slide Deck Length:** 9 Slides (Theoretical & Architecture Focus)  
> **Live Demo:** Handled separately via [`docs/LIVE_DEMO_GUIDE.md`](LIVE_DEMO_GUIDE.md)

---

## 📊 Presentation Structure Overview (9 Slides)

| Slide # | Slide Title | Primary Presenter | Key Focus Area |
|:---:|:---|:---:|:---|
| **1** | Title & Team Introduction | **Presenter 1** | Project vision, team roles, technology stack |
| **2** | The Problem: Traditional Ticketing Bottlenecks | **Presenter 1** | Monolith crashes, scalping, static PDF fraud, high idle costs |
| **3** | The Solution: AlphaPass Serverless Platform | **Presenter 1** | Auto-scaling, price-capped resale, verifiable digital passes |
| **4** | AWS Cloud Architecture & Network Flow | **Presenter 2** | API Gateway REST proxy, Lambda ASGI compute, S3 assets |
| **5** | Serverless Data Modeling with Amazon DynamoDB | **Presenter 2** | 13 DynamoDB tables, GSIs, atomic update counters |
| **6** | Infrastructure-as-Code with HashiCorp Terraform | **Presenter 2** | Modular Terraform, IAM least privilege, CloudWatch & Budgets |
| **7** | DevOps Automation & Dynamic CI/CD Pipelines | **Presenter 3** | GitHub Actions multi-stage build, dynamic API URL injection |
| **8** | Quality Assurance, Security Controls & Governance | **Presenter 3** | 46/46 Pytest pass rate, JWT auth, admin moderation queues |
| **9** | Business Impact, Cost ROI & Conclusion | **Presenter 1** | 90%+ hosting cost savings, scalability, future roadmap |

---

## 🎤 Slide-by-Slide Contents & Speaker Notes

---

### Slide 1: Title & Team Introduction
* **Presenter:** Presenter 1
* **Visual Recommendations:** AlphaPass logo, AWS Cloud Partner badge, Team Alpha logo.
* **On-Slide Text:**
  - **Title:** AlphaPass — Serverless Event Ticketing, Resale & Governance Platform
  - **Subtitle:** Azubi Cloud & AI Academy — Project 2 Internship Defense
  - **Team Alpha Presenters:** [Presenter 1 Name], [Presenter 2 Name], [Presenter 3 Name]
  - **Core Technologies:** AWS Lambda | API Gateway | DynamoDB | FastAPI | HashiCorp Terraform

> **🎤 SPEAKER NOTES — Presenter 1:**  
> *"Good day everyone, respected mentors, evaluators, and colleagues. Welcome to Team Alpha's presentation for Project 2 at the Azubi Cloud & AI Academy.*  
> *Today, we are excited to present **AlphaPass** — a high-performance, serverless event ticketing, peer-to-peer resale exchange, and governance platform built on Amazon Web Services. I am [Presenter 1 Name], presenting alongside my team members [Presenter 2 Name], who will cover our cloud architecture and database design, and [Presenter 3 Name], who will walk us through our CI/CD pipelines, security controls, and quality assurance. Let's begin!"*

---

### Slide 2: The Problem — Traditional Ticketing Bottlenecks
* **Presenter:** Presenter 1
* **Visual Recommendations:** Split graphic showing HTTP 502 server crash vs. ticket scalper markup prices.
* **On-Slide Text:**
  - 💥 **Traffic Spike Crashes:** Traditional server monoliths collapse when thousands of fans attempt to buy tickets simultaneously.
  - ❌ **Counterfeit Ticket Fraud:** Static PDF passes are easy to duplicate and resell fraudulently.
  - 📈 **Predatory Secondary Scalping:** Unregulated resellers mark up ticket prices by 500%+ on third-party sites.
  - 💸 **High Idle Infrastructure Expenses:** Event organizers pay high monthly server hosting fees even during non-event periods.

> **🎤 SPEAKER NOTES — Presenter 1:**  
> *"When analyzing the traditional event ticketing ecosystem, we identified four major pain points. First, traditional server-based platforms suffer severe downtime during high-demand ticket drops. Second, fraud is widespread due to easily duplicated static PDF passes. Third, secondary buyers get exploited by uncontrolled ticket scalping. And fourth, event organizers pay expensive monthly hosting fees even when no events are active. We built AlphaPass specifically to eliminate these four challenges using serverless cloud technology."*

---

### Slide 3: The Solution — The AlphaPass Serverless Platform
* **Presenter:** Presenter 1
* **Visual Recommendations:** High-level solution diagram highlighting 100% Serverless, Instant QR Passes, and Price Caps.
* **On-Slide Text:**
  - ⚡ **100% AWS Serverless Stack:** Scales dynamically from 0 to thousands of requests with zero idle server cost.
  - 🔒 **Verifiable Digital Passes:** Formatted ticket pass codes with embedded QR codes for gate check-in scanning.
  - 🏷️ **Price-Capped Resale Exchange:** Secondary marketplace with automated maximum price markup caps.
  - 🛡️ **End-to-End Governance:** Moderator queues for reviewing events, organizer payouts, and refund requests.

> **🎤 SPEAKER NOTES — Presenter 1:**  
> *"AlphaPass solves these issues through an event-driven, 100% serverless architecture. Utilizing AWS Lambda and API Gateway, our platform scales instantly during traffic surges and costs zero dollars when idle. We provide ticket verification with QR codes, a secondary resale marketplace with price-capping to prevent scalping, and comprehensive governance tools for event organizers and platform administrators."*

---

### Slide 4: AWS Cloud Architecture & Network Flow
* **Presenter:** Presenter 2
* **Visual Recommendations:** Full AWS Architecture Diagram ([docs/alphapass-architecture-diagram.drawio.png](alphapass-architecture-diagram.drawio.png)).
* **On-Slide Text:**
  - 🌐 **Edge & Client Layer:** Static web pages served via Cloudflare + Amazon S3 Website Hosting.
  - 🔀 **API Routing:** Amazon API Gateway REST Proxy with regional wildcard `{proxy+}` routing.
  - ⚙️ **Compute Engine:** AWS Lambda executing Python 3.12 + FastAPI via Mangum ASGI handler.
  - 🗄️ **Storage & Messaging:** 13 DynamoDB tables, S3 asset bucket, Amazon SNS/SES notifications.

> **🎤 SPEAKER NOTES — Presenter 2:**  
> *"Thank you [Presenter 1 Name]. As shown in our cloud architecture diagram, when a user accesses AlphaPass, their browser loads static assets directly from Amazon S3 via Cloudflare. All API requests route through Amazon API Gateway to our backend AWS Lambda function.  
> Lambda runs Python 3.12 and FastAPI wrapped by Mangum, an ASGI adapter that converts API Gateway proxy events into HTTP request objects. Lambda seamlessly interacts with our 13 DynamoDB tables for database operations, S3 for banner image and PDF storage, and SNS/SES for notifications. This decoupled serverless pattern gives us high availability and sub-second execution speeds."*

---

### Slide 5: Serverless Data Modeling with Amazon DynamoDB
* **Presenter:** Presenter 2
* **Visual Recommendations:** DynamoDB table model diagram highlighting key table relationships and GSIs.
* **On-Slide Text:**
  - 🗃️ **13 Specialized DynamoDB Tables:** `events`, `organizers`, `admins`, `orders`, `tickets`, `resale_listings`, `transfers`, `promo_codes`, `payouts`, `platform_settings`, `audit_logs`, `event_categories`, `registrations`.
  - ⚡ **On-Demand Billing (`PAY_PER_REQUEST`):** Zero cost during idle periods, automatic throughput capacity scaling.
  - 🔍 **Global Secondary Indexes (GSIs):** Sub-10ms query access (`email-index`, `organizer_id-index`, `ticket_code-index`, `guest_email-index`).
  - 🔒 **Atomic Update Counters:** Race-condition-free promo code usage counters and ticket inventory updates.

> **🎤 SPEAKER NOTES — Presenter 2:**  
> *"To ensure low-latency database reads and writes under heavy traffic, we designed our data layer on Amazon DynamoDB with On-Demand billing. We utilize 13 dedicated tables configured with Global Secondary Indexes. For example, our `tickets` table uses GSIs for `ticket_code`, `order_id`, and `attendee_email`, allowing sub-10-millisecond lookups whether searching by purchaser email or scanning at the gate. Crucially, we use DynamoDB atomic update expressions to decrement available ticket quantities and increment promo code counts, eliminating race conditions and overselling."*

---

### Slide 6: Infrastructure-as-Code with HashiCorp Terraform
* **Presenter:** Presenter 2
* **Visual Recommendations:** Terraform execution tree showing sub-modules (`modules/lambda`, `modules/dynamodb`, `modules/api_gateway`, `modules/s3`).
* **On-Slide Text:**
  - 🏗️ **100% Reproducible Stack:** Infrastructure defined using HashiCorp Terraform (`>= 1.5.0`).
  - 🧩 **Modular Architecture:** Sub-modules for `dynamodb`, `lambda`, `api_gateway`, `s3`, `sns`, `cloudwatch`, and `budgets`.
  - 🔐 **Least-Privilege IAM Security:** Lambda execution role restricted strictly to required `alphapass-*` table ARNs.
  - 📊 **Cost Guardrails:** CloudWatch error metric alarms & AWS Budget cost protection.

> **🎤 SPEAKER NOTES — Presenter 2:**  
> *"Every single AWS resource in AlphaPass is provisioned using HashiCorp Terraform. Our Terraform code is modularized into reusable sub-modules for DynamoDB, Lambda, API Gateway, S3, CloudWatch, and AWS Budgets. We strictly enforce least-privilege IAM policies, ensuring our Lambda function can only access specific `alphapass-*` tables and resources. We've also configured automated AWS Budget alerts to guarantee we stay within free-tier limits.  
> I will now pass the floor to [Presenter 3 Name] to discuss our CI/CD pipeline and security."*

---

### Slide 7: DevOps Automation & Dynamic CI/CD Pipelines
* **Presenter:** Presenter 3
* **Visual Recommendations:** GitHub Actions workflow diagram showing Test $\rightarrow$ Package $\rightarrow$ Sanitize $\rightarrow$ Terraform Apply $\rightarrow$ S3 Sync.
* **On-Slide Text:**
  - 🚀 **Automated CI/CD:** GitHub Actions workflows ([deploy.yml](../.github/workflows/deploy.yml) and [teardown.yml](../.github/workflows/teardown.yml)).
  - 🧪 **Stage 1 (Testing):** Automatic execution of 46 backend unit & integration tests on push.
  - 📦 **Stage 2 (Packaging):** Cross-platform Python compilation targeting `manylinux2014_x86_64` for Lambda.
  - 🔗 **Dynamic API URL Injection:** Extracts API Gateway base URL from Terraform output and dynamically injects `window.ALPHAPASS_API_URL` into `frontend/js/config.js` prior to S3 sync.

> **🎤 SPEAKER NOTES — Presenter 3:**  
> *"Thank you [Presenter 2 Name]. Our deployment pipeline is fully automated using GitHub Actions. Whenever code is pushed to the `main` branch, our pipeline triggers a multi-stage workflow. Stage 1 executes our 46 unit and integration tests. If all tests pass, Stage 2 packages production Python dependencies targeting the Linux architecture required by AWS Lambda. In Stage 3, the pipeline runs an infrastructure sanitation script, executes `terraform apply`, and dynamically injects the deployed API Gateway URL into `frontend/js/config.js` before syncing to S3. This completely eliminates hardcoded URLs."*

---

### Slide 8: Quality Assurance, Security Controls & Governance
* **Presenter:** Presenter 3
* **Visual Recommendations:** Pytest terminal execution summary showing `46 passed in 18.42s` with green checkmarks.
* **On-Slide Text:**
  - ✅ **100% Test Pass Rate:** 46 unit & integration tests covering Auth, Events, Orders, Promos, Tickets, Check-in, Resale, and Admin queues.
  - 🔑 **Robust Security:** JWT Bearer authentication, bcrypt password hashing, and HTML XSS sanitization in frontend rendering.
  - 🛡️ **Governance Queues:** Moderator approval queues for new events, revenue payouts, refund requests, and secondary resale listings.

> **🎤 SPEAKER NOTES — Presenter 3:**  
> *"Quality assurance and security are built into the core of AlphaPass. Our test suite includes 46 comprehensive unit and integration tests covering every single API router and database operation. Security is enforced through JWT token authentication with role-based access control for organizers and admins, bcrypt password hashing, and XSS sanitization in the frontend. We also provide complete governance queues for reviewing event approvals, organizer revenue payouts, and refund requests."*

---

### Slide 9: Business Impact, Cost ROI & Conclusion
* **Presenter:** Presenter 1 & All Presenters
* **Visual Recommendations:** Hosting cost comparison chart (Monolith Server vs. AWS Serverless) & Future Roadmap timeline.
* **On-Slide Text:**
  - 💡 **Cost Efficiency:** Over 90% hosting cost reduction via AWS Free-Tier and On-Demand billing.
  - 📈 **Infinite Scalability:** Scales automatically from 0 to tens of thousands of concurrent ticket buyers during peak drops.
  - 🚀 **Future Roadmap:** AWS Cognito social sign-in, NFT ticket pass verification on Polygon, native Flutter mobile app.
  - ❓ **Open Floor:** Questions, Comments & Discussion.

> **🎤 SPEAKER NOTES — Presenter 1:**  
> *"In conclusion, AlphaPass provides event organizers with over 90% cost savings compared to traditional server hosting because there are zero server costs when no events are actively selling. Team Alpha has successfully built, tested, and deployed a complete, secure, and production-ready serverless ticketing platform on AWS. We want to thank our Azubi Cloud Academy instructors and mentors for their invaluable guidance. We now open the floor for any questions. Thank you!"*
