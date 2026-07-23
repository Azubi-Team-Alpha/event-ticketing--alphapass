# Ticket Hub Backend API (AlphaPass)
**Azubi Cloud & AI Academy Portfolio — Project 2 — Team Alpha**

Welcome to the backend service of **AlphaPass**. This service is a high-performance, serverless REST API built with **FastAPI**, **Amazon DynamoDB (Boto3)**, and **Mangum ASGI Adapter**. It supports organizer/admin authentication, public guest checkout, PDF ticket rendering, gate entry QR scanning, price-capped secondary market resales, and peer ticket transfers.

---

## 🛠️ Tech Stack & Core Services

- **Framework:** FastAPI (Python 3.12+)
- **Database Engine:** Amazon DynamoDB (12 serverless on-demand tables via Boto3)
- **ASGI Lambda Adapter:** Mangum (for running FastAPI directly on AWS Lambda)
- **Authentication:** JSON Web Tokens (JWT) using `python-jose` & `bcrypt`
- **Security:** Password hashing, role guards (`organizer`, `admin`), atomic inventory locks
- **Integrations:**
  - **AWS S3:** Storage for event cover pictures & generated QR code images
  - **AWS SNS / SES:** Real-time booking alerts and verification links
- **Testing:** `pytest` + `httpx` + `moto` (for mocking AWS DynamoDB & S3 in test suite)
- **PDF Generation:** `reportlab` (for rendering printable PDF tickets)

---

## 🚀 Quick Start Setup

### 1. Prerequisites
Python 3.12+ installed locally.

### 2. Virtual Environment & Dependencies
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Launch Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Tests

Execute the complete 42-test unit and integration test suite:
```bash
pytest -v
```
*Note: DynamoDB and S3 interactions are automatically mocked during pytest runs using `moto`.*
