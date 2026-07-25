# AlphaPass Backend Architecture & Developer Guide

> **Azubi Cloud & AI Academy — Project 2 (Team Alpha)**  
> **Framework:** FastAPI (`>= 0.110.0`)  
> **Serverless Wrapper:** Mangum (`>= 0.17.0`)  
> **Database Helper:** Boto3 DynamoDB Client Wrapper

---

## 1. Application Architecture & Entrypoint

The backend is built with **FastAPI**, structured modularly across 10 router modules, and served in AWS Lambda using **Mangum** to translate AWS API Gateway payload events into ASGI HTTP requests.

```text
AWS API Gateway ──> Lambda (index.py) ──> Mangum ──> FastAPI (app/main.py) ──> Routers ──> DynamoDB Helper
```

- **[index.py](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/backend/index.py)**: Contains `lambda_handler = Mangum(app, lifespan="off")`.
- **[app/main.py](file:///home/haadi/Desktop/AWS%20Cloud/Azubi-AWS-AI/Team%20Alpha/alphapass/backend/app/main.py)**: Initializes FastAPI, configures CORS middleware (`allow_origins=["*"]`), and registers all 10 router modules under their respective path prefixes.

---

## 2. API Router Modules & Responsibilities

The backend functionality is divided into 10 focused router modules in `app/routers/`:

### 1. `auth.py` (Authentication & Security)
- **Endpoints:**
  - `POST /auth/organizer/signup` — Register event organizer account.
  - `POST /auth/organizer/login` — Authenticate organizer & issue JWT.
  - `GET /auth/organizer/me` — Retrieve logged-in organizer profile.
  - `POST /auth/admin/login` — Authenticate administrator & issue JWT.
  - `POST /auth/admin/signup` — Register admin account.
  - `POST /auth/verify-email` & `POST /auth/request-password-reset` — Account verification and password reset workflows.
- **Security:** Password hashing with `passlib[bcrypt]` and OAuth2 JWT Bearer token generation.

### 2. `events.py` (Event Management & Discovery)
- **Endpoints:**
  - `GET /events` — List public events with pagination, category filter (`category_id`), search query (`search`), city, and date filters.
  - `GET /events/{event_id}` — Detailed event information, ticket pass tiers, policies, and organizer details.
  - `POST /events/organizer` — Create new event draft.
  - `POST /events/upload-banner` — Upload event cover image directly to S3 bucket.
  - `POST /events/organizer/{event_id}/publish` — Publish event.
  - `POST /events/organizer/{event_id}/ticket-types` — Add ticket tier (e.g. VIP, General Admission).
  - `POST /events/organizer/{event_id}/promo-codes` — Create promo discount code.

### 3. `orders.py` (Cart, Checkout & Order Processing)
- **Endpoints:**
  - `POST /orders` — Process guest purchase order, generate formatted ticket pass codes, apply promo codes, and issue tickets.
  - `POST /orders/validate-promo` — Atomic promo code validation (checks expiration, event match, and remaining uses).
  - `POST /orders/lookup` — Query ticket wallet by purchaser email or order ID.
  - `PUT /orders/{order_id}/cancel` — Cancel order and return ticket inventory.
  - `POST /orders/{order_id}/refund-request` — Request order refund from organizer/admin.

### 4. `tickets.py` (Digital Ticket Passes & PDF Generation)
- **Endpoints:**
  - `GET /tickets/{ticket_code}` — Retrieve digital ticket pass status.
  - `GET /tickets/{ticket_code}/pdf` — Dynamically generate and stream printable PDF ticket with QR code using ReportLab.
  - `GET /tickets/users/me/tickets` — List active user ticket passes.

### 5. `transfers.py` (Peer-to-Peer Pass Transfers)
- **Endpoints:**
  - `POST /transfers/{ticket_code}/transfer` — Transfer ticket pass ownership to a guest email address.
  - `GET /transfers/{ticket_code}/transfers` — View pass transfer audit log.

### 6. `resale.py` (Secondary Resale Marketplace Exchange)
- **Endpoints:**
  - `GET /resale/listings` — Browse secondary ticket resale marketplace.
  - `POST /resale/tickets/{ticket_code}` — List ticket pass for secondary resale (enforces price-cap rules).
  - `POST /resale/tickets/{ticket_code}/remove` — Delist pass from secondary market.
  - `POST /resale/{listing_id}/purchase` — Purchase resale pass (re-issues new ticket code to buyer).

### 7. `checkin.py` (Gate Entry Check-in Portal)
- **Endpoints:**
  - `POST /checkin/scan` — Gate entry scanner endpoint (validates ticket code, checks duplicate use, marks `is_used = True`, records check-in timestamp).
  - `GET /checkin/ticket/{ticket_code}` — Look up check-in status.

### 8. `organizer.py` (Organizer Analytics & Payouts)
- **Endpoints:**
  - `GET /organizer/dashboard` — Overview metrics (total revenue, tickets sold, active events).
  - `GET /organizer/events/{event_id}/analytics` — Single event analytics & ticket sales breakdown.
  - `GET /organizer/events/{event_id}/attendees` — Export attendee roster in JSON, CSV, or PDF format.
  - `GET /organizer/payouts` & `POST /organizer/payouts` — Request revenue payout settlements.

### 9. `admin.py` (Platform Governance & Moderation Console)
- **Endpoints:**
  - `GET /admin/dashboard` — Platform revenue, commission earnings, total events, total organizers.
  - `GET/PUT /admin/events` — Moderator queue for approving/rejecting organizer events.
  - `GET/PUT /admin/payouts` — Process organizer payout settlement requests.
  - `GET/PUT /admin/refunds` — Approve or reject order refund requests.
  - `GET/PUT /admin/resale` — Moderate secondary resale listings.
  - `PUT /admin/config/commission` — Update global platform commission rate.
  - `GET /admin/audit-logs` — Review security audit logs.

### 10. `health.py` (System Uptime Health Check)
- **Endpoints:**
  - `GET /health` — Returns `{"status": "healthy", "service": "alphapass-api", "version": "2.0.0"}`.

---

## 3. Database Abstraction Layer (`app/db/dynamodb.py`)

All database interactions use **Boto3** targeting Amazon DynamoDB tables:

- **DynamoDB Client & Resource Initializer**: Automatically picks table names from environment variables (`EVENTS_TABLE`, `ORDERS_TABLE`, etc.) or defaults to dev names.
- **Helper Functions**:
  - `get_item(table_name, key_dict)`
  - `put_item(table_name, item_dict)`
  - `update_item(table_name, key_dict, update_expression, expression_values)`
  - `delete_item(table_name, key_dict)`
  - `query_gsi(table_name, index_name, key_condition_expression, expression_values)`
  - `scan_table(table_name, filter_expression, expression_values)`
- **Atomic Operations**: Used for promo code usage increments (`SET usage_count = usage_count + 1`) and ticket availability decrements (`SET quantity_available = quantity_available - :qty`) to prevent overselling race conditions.

---

## 4. PDF Ticket Engine (`app/core/pdf.py`)

Printable ticket passes are dynamically rendered using **ReportLab**:
- Generates 300 DPI vector PDF tickets formatted with event title, venue, date/time, ticket tier, attendee name, and ticket pass code.
- Draws QR code matrix matching the ticket code for instant gate scanning.
- Streamed directly to the client as an inline attachment (`application/pdf`).

---

## 5. Automated Test Suite (`backend/tests/`)

The backend includes a comprehensive pytest suite (`46/46 tests passed`):

- **`test_auth.py`**: Admin & Organizer registration, login, bad password rejections, profile retrieval.
- **`test_dynamodb.py`**: Low-level CRUD operations against mock/in-memory DynamoDB tables.
- **`test_events.py`**: Event creation, publishing, ticket type addition, banner upload, category listing, search filtering.
- **`test_orders.py`**: Guest order checkout, promo code validation, oversell prevention, order cancellations, order lookup.
- **`test_tickets.py`**: Ticket pass lookup, check-in scanning, double check-in rejection, PDF report rendering.
- **`test_new_features.py`**: Group purchase discounts, platform commission config updates, governance moderation queues.
- **`test_health.py`**: System health check ping.

```bash
# Execute full backend test suite locally
cd backend
pytest -v
```
