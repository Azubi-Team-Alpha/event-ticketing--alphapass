# 🎟️ AlphaPass (Ticket Hub) Frontend Integration Guide
**Azubi Cloud & AI Academy — Project 2 — Team Alpha Developer Reference**

This document serves as the integration manual for the frontend development team. It specifies all backend REST API endpoints, JSON request/response formats, database models, and deployment configurations.

---

## 🏛️ Serverless Architecture Overview

AlphaPass is built on a serverless AWS infrastructure designed with Terraform:
- **API Gateway (REST API):** Handled by Amazon API Gateway proxying requests to the AWS Lambda function.
- **FastAPI Backend (AWS Lambda):** The Python business logic runs inside Lambda, wrapped using the `Mangum` ASGI adapter.
- **DynamoDB Database:** The serverless database layer using Amazon DynamoDB tables for all application entities (events, orders, tickets, organizers, admins, promo codes, payouts, logs, and settings).
- **AWS S3:** Serves as the storage bucket for event banners and PDF check-in QR codes.
- **AWS SES:** Sends order confirmations and transactional emails.

---

## 💾 Database Schema (DynamoDB Tables)

The infrastructure contains 12 DynamoDB tables defined in Terraform. Your client-side requests interact with these models through the API Gateway endpoints.

### 1. Events Table (`alphapass-events-[env]`)
- **Hash Key:** `EventID` (String/UUID)
- **Primary Schema Fields:**
  ```json
  {
    "EventID": "string (UUID)",
    "title": "string",
    "description": "string",
    "venue_name": "string",
    "city": "string",
    "country": "string",
    "starts_at": "string (ISO 8601)",
    "ends_at": "string (ISO 8601)",
    "status": "string (draft | pending | published | cancelled | archived)",
    "ticket_types": [
      {
        "id": "string",
        "name": "string",
        "price": "number",
        "quantity": "integer",
        "quantity_sold": "integer",
        "is_active": "boolean"
      }
    ]
  }
  ```

### 2. Registrations Table (`alphapass-registrations-[env]`)
- **Hash Key:** `RegistrationID` (String/UUID)

### 3. Organizers Table (`alphapass-organizers-[env]`)
- **Hash Key:** `OrganizerID` (String/UUID)

### 4. Admins Table (`alphapass-admins-[env]`)
- **Hash Key:** `AdminID` (String/UUID)

### 5. Orders Table (`alphapass-orders-[env]`)
- **Hash Key:** `OrderID` (String/UUID)

### 6. Tickets Table (`alphapass-tickets-[env]`)
- **Hash Key:** `TicketID` (String/UUID)

### 7. Promo Codes Table (`alphapass-promo-codes-[env]`)
- **Hash Key:** `Code` (String)

### 8. Resale Listings Table (`alphapass-resale-listings-[env]`)
- **Hash Key:** `ListingID` (String/UUID)

### 9. Ticket Transfers Table (`alphapass-transfers-[env]`)
- **Hash Key:** `TransferID` (String/UUID)

### 10. Organizer Payouts Table (`alphapass-payouts-[env]`)
- **Hash Key:** `PayoutID` (String/UUID)

### 11. Platform Settings Table (`alphapass-platform-settings-[env]`)
- **Hash Key:** `SettingKey` (String)

### 12. Audit Logs Table (`alphapass-audit-logs-[env]`)
- **Hash Key:** `LogID` (String/UUID)

---

## 🔒 Authentication & Route Guards

The API uses standard JSON Web Tokens (JWT) for authentication.
- **Headers:** Authorization headers must contain the Bearer token:
  `Authorization: Bearer <access_token>`
- **Roles:** The token payload contains a `"role"` field (`admin` | `organizer`). Routes are guarded based on these roles.

---

## 🌐 SPA Frontend Pages & Endpoint Mapping

Whether your team builds the frontend using **React SPA (with React Router)** or **Pure HTML/JS**, the frontend should be structured around the following pages and features:

### 1. Public Guest Pages

#### 🏠 Event Explorer Page (`/`)
- **Features:** Search and list events, filter by category/city/date.
- **Endpoints:**
  - `GET /events` — Fetch all published events.
  - `GET /categories` — Fetch categories for filter dropdown.

#### 📄 Event Details Page (`/events/:id`)
- **Features:** Display detailed description, venue location, starts/ends dates, and ticket type selector.
- **Endpoints:**
  - `GET /events/{event_id}` — Get specific event details.

#### 🛒 Guest Checkout Page (`/checkout`)
- **Features:** Collect attendee details, apply promo code, and purchase ticket.
- **Endpoints:**
  - `POST /orders` — Place order/register guest.
  - `GET /promo/{code}` — Validate promo code.

#### 🎫 My Tickets Dashboard (`/tickets`)
- **Features:** Lookup ticket status, show QR code, download PDF pass.
- **Endpoints:**
  - `GET /tickets/{ticket_code}/status` — View ticket details.
  - `GET /tickets/{ticket_code}/pdf` — Download PDF ticket.

#### 🔄 Ticket Transfer Page (`/tickets/transfer`)
- **Features:** Securely transfer a ticket to another user.
- **Endpoints:**
  - `POST /transfers/{ticket_code}/transfer` — Transfer ticket to new owner.

#### 📈 Resale Marketplace (`/resale`)
- **Features:** View public resales or list a ticket.
- **Endpoints:**
  - `GET /resale` — Browse resale listings.
  - `POST /resale/tickets/{ticket_code}` — List ticket for resale.
  - `POST /resale/{listing_id}/purchase` — Purchase listed ticket.

---

### 2. Organizer Dashboard Pages

#### 🔑 Organizer Authentication (`/organizer/login` & `/organizer/signup`)
- **Features:** Sign up or sign in as an event organizer.
- **Endpoints:**
  - `POST /auth/organizer/signup` — Create account.
  - `POST /auth/organizer/login` — Retrieve organizer access token.

#### 📊 Organizer Dashboard Home (`/organizer/dashboard`)
- **Features:** List organizer's events, sales statistics, request payout.
- **Endpoints:**
  - `GET /auth/organizer/me` — Verify auth token and user role.
  - `GET /events/organizer` — Fetch organizer's drafted/published events.
  - `POST /payouts/request` — Request payout for event revenue.

#### ➕ Create/Edit Event Page (`/organizer/events/new` or `/organizer/events/:id/edit`)
- **Features:** Add event details, create and edit ticket types.
- **Endpoints:**
  - `POST /events/organizer` — Create new event draft.
  - `PUT /events/organizer/{event_id}` — Update event details.
  - `POST /events/organizer/{event_id}/ticket-types` — Add ticket type.
  - `POST /events/organizer/{event_id}/publish` — Submit event draft for approval.

#### 📷 Event Check-in Scanner (`/organizer/scan`)
- **Features:** QR Scanner camera interface to check in attendees.
- **Endpoints:**
  - `POST /checkin/scan` — Scan and validate ticket code.

---

### 3. Platform Admin Pages

#### 🔑 Admin Authentication (`/admin/login`)
- **Features:** Secure login page for platform administrators.
- **Endpoints:**
  - `POST /auth/admin/login` — Retrieve admin access token.

#### 🛡️ Admin Dashboard Home (`/admin/dashboard`)
- **Features:** View system audit logs, moderate events, approve payouts, update commission rate.
- **Endpoints:**
  - `GET /events/admin/pending` — List events awaiting approval.
  - `POST /events/admin/approve` — Approve event for publication.
  - `GET /payouts/admin/pending` — List pending payouts.
  - `POST /payouts/admin/approve` — Approve payout requests.
  - `GET /settings` — View global settings.
  - `POST /settings` — Update global parameters (e.g. commission rate).

---

## 🛠️ Frontend API Request Examples (JavaScript)

### Fetch Events with Filters
```javascript
async function getEvents(search = '', city = '') {
  const url = new URL('http://localhost:8000/events');
  if (search) url.searchParams.append('search', search);
  if (city) url.searchParams.append('city', city);
  
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to load events');
  return await response.json();
}
```

### Guest Checkout Request
```javascript
async function checkout(eventId, ticketTypeId, guestName, guestEmail) {
  const payload = {
    event_id: eventId,
    guest_name: guestName,
    guest_email: guestEmail,
    items: [
      { ticket_type_id: ticketTypeId, quantity: 1 }
    ]
  };

  const response = await fetch('http://localhost:8000/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Checkout failed');
  }
  return await response.json();
}
```
