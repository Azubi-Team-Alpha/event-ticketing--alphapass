# 🎟️ AlphaPass (Ticket Hub)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)](#-technology-stack--integrations)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](#-technology-stack--integrations)

**AlphaPass (Ticket Hub)** is a secure, high-performance, containerized ticketing platform built for managing events, generating digital QR-code tickets, and facilitating safe secondary ticket transfers and resales. 

This repository is part of the **Azubi Cloud & AI Academy Internship Portfolio (Project 2 — Team Alpha)**.

---

## 📢 Current Project State: Backend-Only

> [!NOTE]
> **Active Implementation Phase:** Currently, only the **Backend API** is implemented. 
> The `frontend` directory is reserved for future web application development. The platform is currently managed and accessed directly via the containerized FastAPI backend endpoints.

---

## 📁 Repository Structure

```text
alphapass/
├── backend/            # FastAPI REST API, database migrations, and backend tests
│   ├── app/            # Application core code (models, schemas, routers, CRUD)
│   ├── alembic/        # Database migration scripts
│   ├── tests/          # Comprehensive pytest suite
│   ├── Dockerfile      # Production-ready Docker build configuration
│   └── README.md       # Detailed setup & API guide for the backend
└── frontend/           # [Placeholder] Reserved for the web client
```

---

## ⚡ Backend Core Features

* **Role-Based Authentication:** Secure JWT-based registration and login flows for **Admins**, **Organizers**, and **Guests**.
* **Event Management:** Organizers can draft, set ticket availability, define transfer/resale rules, and publish events.
* **Guest Checkout & Purchase:** Public users can purchase tickets using promo codes without needing to register first.
* **PDF Ticket & QR Code Generation:** Generates print-ready PDFs containing unique QR codes for event check-in.
* **Secondary Market (Transfers & Resales):**
  * **Secure Transfer:** Safe peer-to-peer ticket transfers with defined deadlines.
  * **Capped Resale:** Secure resale marketplace with price-markup limits enforced at the database level to prevent scalping.
* **Organizer & Admin Dashboards:** Access real-time event analytics, manage event approvals, and adjust platform fees.

---

## 🛠️ Technology Stack & Integrations

| Layer | Technology / Service | Description |
|---|---|---|
| **Framework** | **FastAPI** | High-performance asynchronous REST API framework |
| **Database** | **PostgreSQL** / **SQLite** | PostgreSQL (Docker/Production) and SQLite (Local development) |
| **ORM & Migrations** | **SQLAlchemy 2.0** + **Alembic** | Object-Relational Mapper & schema migration control |
| **Storage** | **AWS S3** | Persistent storage for event banner images & generated QR codes |
| **Messaging** | **AWS SES** | Transactional emails for order confirmations & transfer notifications |
| **PDF Engine** | **ReportLab** | Dynamically constructs ticket receipt and pass PDFs |
| **Testing** | **pytest** + **moto** | Test suite with mocked AWS services |

---

## 🚀 Quick Start (Backend)

For full instructions on local execution, environment configuration, database seeding, and testing, please refer to the detailed [Backend README](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/backend/README.md).

### 1. Fast Local Setup (SQLite)
Navigate to the `backend` folder, create a virtual environment, and install dependencies:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file by copying the template:
```bash
cp .env.example .env
```
*(The default configuration points to a local SQLite database file `test.db` and is ready for local execution).*

### 3. Database Migration & Seeding
```bash
# Apply migrations to set up schema
alembic upgrade head

# Seed admin/organizer accounts & mock events
python -m app.db.seed
```

### 4. Run Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Visit **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Running Tests
Ensure your virtual environment is active, then execute:
```bash
pytest
```

---

## 👥 Team Alpha (Project Contributors)
* **Azubi-AWS-AI Internship Program**
* **Project Portfolio Reference:** Project 2
