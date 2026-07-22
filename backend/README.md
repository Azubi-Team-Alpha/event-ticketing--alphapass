# Ticket Hub Backend API (AlphaPass)
**Internship Portfolio — Project 2 - Team Alpha**

Welcome to the backend service of **Ticket Hub (AlphaPass)**. This service is a high-performance, serverless REST API built with **FastAPI**, **Boto3 DynamoDB Client**, and **Mangum ASGI Adapter**. It supports secure organizer/admin authentication, public guest checkout with transactional emails, QR-code ticket PDF generation, transfers, and resales.

---

## 🛠️ Tech Stack & Core Services
- **Framework:** FastAPI (Python 3.12+)
- **Database Layer:** Amazon DynamoDB (Serverless On-Demand Tables via Boto3 Client)

- **Database Migrations:** Alembic 1.13+
- **Authentication:** JSON Web Tokens (JWT) using `python-jose` & `bcrypt`
- **Security:** Hashed passwords & role-based route guards
- **Integrations:**
  - **AWS S3:** Persistent storage for event banner images & generated ticket QR codes
  - **AWS SES:** Dispatches transactional HTML emails (Order confirmations, verification links, ticket transfers, resale sales)
- **Testing:** `pytest` + `pytest-asyncio` + `moto` (for AWS services mocking)
- **PDF Generation:** `reportlab` (for official ticket downloads)

---

## 🚀 Local Host Setup (Quick Start)

### 1. Prerequisites
Ensure you have Python 3.12+ installed on your system.

### 2. Set Up Virtual Environment & Dependencies
Clone the repository, navigate to the `backend` directory, create a virtual environment, and install requirements:
```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
By default, the `.env` is configured to use a local **SQLite** database (`test.db`) for zero-configuration setup:
```ini
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=my-local-dev-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=ticket-hub-dev
SES_SENDER_EMAIL=noreply@ticket-hub.com
DEBUG=true
```

### 4. Database Setup & Seeding
Prepare the database schema by executing migrations, then seed default credentials and mock events:
```bash
# Run migrations (creates SQLite tables)
alembic upgrade head

# Run seed script to pre-populate database
python -m app.db.seed
```

**Seeded Accounts:**
- **Platform Admin:** `admin@ticket-hub.com` / `Password123`
- **Event Organizer:** `organizer@ticket-hub.com` / `Password123`

### 5. Launch the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Documentation (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Tests

A comprehensive test suite is included to cover authentication, events creation, guest checkouts, ticket transfers, resales, and scan workflows.

To run the tests:
```bash
# Ensure your virtual environment is active
source .venv/bin/activate

# Run pytest
pytest
```
*Note: AWS service interactions (S3/SES) are fully mocked in the test suite using `moto`.*

---

## 🔍 API Testing Guide

You can test the APIs directly using the **Swagger UI** (`/docs`) or utility CLI tools like **`curl`** or HTTP Clients. Below is the step-by-step guide to testing the main backend workflows.

### 1. Health & Readiness Check
Ensure the backend and database are online.
```bash
curl -X GET http://localhost:8000/
```
**Response:**
```json
{
  "status": "ok",
  "db": "connected",
  "timestamp": "2026-07-11T16:00:00Z"
}
```

---

### 2. Organizer Authentication Workflow

#### A. Organizer Registration
Create a new organizer account.
```bash
curl -X POST http://localhost:8000/auth/organizer/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "myorg@example.com",
    "full_name": "Organizer Name",
    "password": "StrongPassword123",
    "business_name": "My Business LLC"
  }'
```

#### B. Organizer Login & Token Retrieval
Authenticates and returns a JSON Web Token (JWT).
```bash
curl -X POST http://localhost:8000/auth/organizer/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "organizer@ticket-hub.com",
    "password": "Password123"
  }'
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
  "token_type": "bearer",
  "role": "organizer"
}
```
*Save the `access_token` string. You will need it to authorize future requests as an organizer.*

#### C. Get Organizer Profile (Authenticated)
Pass the token in the `Authorization` header.
```bash
curl -X GET http://localhost:8000/auth/organizer/me \
  -H "Authorization: Bearer <access_token>"
```

---

### 3. Event & Ticket Type Management (Organizer)

#### A. Create a Draft Event
```bash
curl -X POST http://localhost:8000/events/organizer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "title": "Alpha Summer Festival 2026",
    "description": "Premium music and arts event",
    "starts_at": "2026-08-15T18:00:00",
    "ends_at": "2026-08-15T23:00:00",
    "venue_name": "Festival Grounds",
    "city": "Accra",
    "country": "Ghana",
    "allow_transfers": true,
    "transfer_deadline_hours": 12,
    "allow_resale": true,
    "max_resale_markup_percent": 15.0
  }'
```
*Note the `"id"` of the returned event (e.g. `event_uuid`).*

#### B. Add a Ticket Type to the Event
```bash
curl -X POST http://localhost:8000/events/organizer/<event_uuid>/ticket-types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "General Admission",
    "description": "Standard entry pass",
    "price": 50.00,
    "quantity": 100,
    "purchase_limit": 5
  }'
```

#### C. Publish the Event
An event must have at least one ticket type before it can be published.
```bash
curl -X POST http://localhost:8000/events/organizer/<event_uuid>/publish \
  -H "Authorization: Bearer <access_token>"
```

---

### 4. Public Event Browsing & Guest Checkout

#### A. Browse Published Events
Publicly retrieve all published events.
```bash
curl -X GET http://localhost:8000/events
```

#### B. Validate a Promo Code (Optional)
If a promo code is set, validate its discount amount.
```bash
curl -X POST http://localhost:8000/orders/validate-promo \
  -H "Content-Type: application/json" \
  -d '{
    "code": "EARLYBIRD",
    "event_id": "<event_uuid>"
  }'
```

#### C. Create an Order (Guest Checkout)
Purchase tickets without requiring a pre-registered account.
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "<event_uuid>",
    "guest_name": "Alice Johnson",
    "guest_email": "alice@example.com",
    "items": [
      {
        "ticket_type_id": "<ticket_type_uuid>",
        "quantity": 2
      }
    ]
  }'
```
**Response:**
```json
{
  "id": "order_uuid",
  "event_id": "event_uuid",
  "guest_name": "Alice Johnson",
  "guest_email": "alice@example.com",
  "status": "confirmed",
  "subtotal": "100.00",
  "discount_amount": "0.00",
  "platform_fee": "5.00",
  "total_amount": "105.00",
  "items": [
    {
      "id": "order_item_uuid",
      "ticket_type_id": "ticket_type_uuid",
      "quantity": 2,
      "unit_price": "50.00",
      "tickets": [
        {
          "id": "ticket_uuid_1",
          "ticket_code": "TC-XXXX-XXXX-1",
          "status": "active"
        },
        {
          "id": "ticket_uuid_2",
          "ticket_code": "TC-XXXX-XXXX-2",
          "status": "active"
        }
      ]
    }
  ]
}
```

---

### 5. Ticket Management, PDF, & Scanning

#### A. View Ticket Status
Anyone can check details of a ticket code:
```bash
curl -X GET http://localhost:8000/tickets/<ticket_code>/status
```

#### B. Download Ticket PDF
Generate and download the official PDF:
```bash
curl -X GET http://localhost:8000/tickets/<ticket_code>/pdf --output ticket.pdf
```

#### C. Scan / Check-In Ticket
Scan a ticket code to validate entry (marks ticket status as `used`).
```bash
curl -X POST http://localhost:8000/checkin/scan \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_code": "<ticket_code>"
  }'
```

---

### 6. Secondary Market (Transfers & Resales)

#### A. Transfer a Ticket to Another Person
```bash
curl -X POST "http://localhost:8000/transfers/<ticket_code>/transfer?guest_email=alice@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "to_name": "Bob Smith",
    "to_email": "bob@example.com"
  }'
```

#### B. List a Ticket for Resale
Seller creates a public listing with their desired asking price (subject to the event markup cap).
```bash
curl -X POST http://localhost:8000/resale/tickets/<ticket_code> \
  -H "Content-Type: application/json" \
  -d '{
    "seller_name": "Alice Johnson",
    "seller_email": "alice@example.com",
    "asking_price": 55.00
  }'
```

#### C. Browse Available Resale Listings
```bash
curl -X GET "http://localhost:8000/resale?event_id=<event_uuid>"
```

#### D. Purchase a Resold Ticket
Buyer purchases a listed ticket. The old ticket is marked `resold` and a new ticket is generated for the buyer.
```bash
curl -X POST http://localhost:8000/resale/<resale_listing_uuid>/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_name": "Charlie Brown",
    "buyer_email": "charlie@example.com"
  }'
```

---

### 7. Administrative Controls

#### A. Admin Login
```bash
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ticket-hub.com",
    "password": "Password123"
  }'
```
*Save the `access_token` string (role: "admin").*

#### B. View Platform Stats Dashboard
```bash
curl -X GET http://localhost:8000/admin/dashboard \
  -H "Authorization: Bearer <admin_access_token>"
```

#### C. Approve Event
If `REQUIRE_EVENT_APPROVAL=true`, events go to pending first. Admin approvals publish them.
```bash
curl -X PUT http://localhost:8000/admin/events/<event_uuid>/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_access_token>" \
  -d '{
    "approved": true
  }'
```

#### D. Update Platform Commission Percent
```bash
curl -X PUT http://localhost:8000/admin/config/commission \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_access_token>" \
  -d '{
    "commission_percent": 6.5
  }'
```
