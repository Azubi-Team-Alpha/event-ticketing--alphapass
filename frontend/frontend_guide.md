# 🎟️ AlphaPass (Ticket Hub) Frontend Integration Guide
**Azubi Cloud & AI Academy — Project 2 — Team Alpha Developer Reference**

This document is the complete guide for the frontend development team. It defines all serverless API endpoints, exact JSON request/response formats, DynamoDB table mappings, and logical frontend pages for building a robust Single Page Application (SPA) in React or Pure HTML/JS.

---

## 🏛️ Serverless Architecture & DynamoDB Mapping

The infrastructure relies on Amazon API Gateway, AWS Lambda (FastAPI with Mangum), and 12 dedicated DynamoDB tables:

1. **`alphapass-events-[env]`** (Hash Key: `EventID`): Stores details, settings, and nested ticket types for all events.
2. **`alphapass-registrations-[env]`** (Hash Key: `RegistrationID`): Stores guest registrations and ticket details.
3. **`alphapass-organizers-[env]`** (Hash Key: `OrganizerID`): Handles business and auth info for event organizers.
4. **`alphapass-admins-[env]`** (Hash Key: `AdminID`): Stores administrators credentials and roles.
5. **`alphapass-orders-[env]`** (Hash Key: `OrderID`): Manages financial and checkout metadata.
6. **`alphapass-tickets-[env]`** (Hash Key: `TicketID`): Manages physical scans, check-ins, and ticket codes.
7. **`alphapass-promo-codes-[env]`** (Hash Key: `Code`): Validation rules for discount promo codes.
8. **`alphapass-resale-listings-[env]`** (Hash Key: `ListingID`): Holds active ticket secondary market sales.
9. **`alphapass-transfers-[env]`** (Hash Key: `TransferID`): Logs historical transfer metadata.
10. **`alphapass-payouts-[env]`** (Hash Key: `PayoutID`): Organizer revenue payout status.
11. **`alphapass-platform-settings-[env]`** (Hash Key: `SettingKey`): Stores global fee parameters.
12. **`alphapass-audit-logs-[env]`** (Hash Key: `LogID`): Security audit log records.

---

## 🔒 Authentication & Headers

Access to secured endpoints requires a JSON Web Token (JWT) in the Authorization header:
- Header format: `Authorization: Bearer <access_token>`
- Token Roles: The payload contains a `"role"` parameter claiming either `"admin"` or `"organizer"`.

---

## 📦 Pydantic Input Schemas (JSON Schemas)

Your frontend forms must build payloads matching these exact schemas.

### 1. Unified Authentication Login
* **Expected Payload:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123"
  }
  ```

### 2. Organizer Signup (`POST /auth/organizer/signup`)
* **Expected Payload:**
  ```json
  {
    "email": "organizer@example.com",
    "full_name": "John Doe",
    "password": "securepassword123 (Min 8 characters)",
    "business_name": "Epic Events Inc (Optional)",
    "phone": "+233240000000 (Optional)"
  }
  ```

### 3. Event Creation (`POST /events/organizer`)
* **Expected Payload:**
  ```json
  {
    "title": "Cloud Security Summit 2026",
    "description": "Comprehensive cloud security summit",
    "policies": "No refunds after 24h prior to event.",
    "category_id": "category-uuid",
    "venue_name": "Accra Digital Center",
    "address": "Ring Road West",
    "city": "Accra",
    "country": "Ghana",
    "is_online": false,
    "online_url": null,
    "starts_at": "2026-08-20T09:00:00",
    "ends_at": "2026-08-20T17:00:00",
    "allow_transfers": true,
    "transfer_deadline_hours": 24,
    "max_transfers_per_ticket": 1,
    "allow_resale": true,
    "max_resale_markup_percent": 10.0,
    "group_discount_threshold": 5,
    "group_discount_percent": 15.0,
    "allow_refunds": true
  }
  ```

### 4. Ticket Type Creation (`POST /events/organizer/{event_id}/ticket-types`)
* **Expected Payload:**
  ```json
  {
    "name": "General Admission",
    "description": "Standard entry ticket",
    "benefits": ["Free drinks", "Speaker slides access"],
    "price": 50.00,
    "quantity": 150,
    "sales_start": "2026-07-21T09:00:00 (Optional)",
    "sales_end": "2026-08-19T18:00:00 (Optional)",
    "purchase_limit": 5,
    "min_purchase": 1,
    "sort_order": 0
  }
  ```

### 5. Guest Checkout Order (`POST /orders`)
* **Expected Payload:**
  ```json
  {
    "event_id": "event-uuid",
    "guest_name": "Alice Johnson",
    "guest_email": "alice@example.com",
    "guest_phone": "+233240111111 (Optional)",
    "items": [
      {
        "ticket_type_id": "ticket-type-uuid",
        "quantity": 2,
        "attendee_name": "Alice Johnson",
        "attendee_email": "alice@example.com"
      }
    ],
    "promo_code": "DISCOUNT10 (Optional)",
    "payment_reference": "ref-pay-12345 (Optional)",
    "payment_method": "Mobile Money (Optional)"
  }
  ```

---

## 🌐 Page-by-Page Integration Guidelines

### 1. Guest Views

#### 🏠 Page: Event Explorer (`/`)
1. Call `GET /events` to retrieve published events. Render as grid cards displaying title, date, venue, city, and min_price.
2. Call `GET /categories` to populate the Category filter dropdown.
3. Handle search and city filter inputs by appending `?search={query}&city={city}` parameters dynamically.

#### 📄 Page: Event Details (`/events/:id`)
1. Retrieve details via `GET /events/{id}`.
2. Display location, description, date ranges, and ticket types.
3. Manage selection quantity state and redirect to checkout `/checkout?event_id={id}&type_id={type_id}&qty={qty}`.

#### 🛒 Page: Checkout (`/checkout`)
1. Build order details form matching `OrderCreate` payload.
2. Allow promo verification: call `GET /promo/{code}`. If valid, update total price estimation.
3. Send checkout order via `POST /orders`. On success (201 Created), render order summary and ticket codes.

#### 🎫 Page: Ticket Wallet & Actions (`/tickets/:code`)
1. Lookup ticket details using `GET /tickets/{code}/status`.
2. Display validation status, attendee details, QR code, and download link to `GET /tickets/{code}/pdf`.
3. Provide forms to list for resale (`POST /resale/tickets/{code}`) or transfer ownership (`POST /transfers/{code}/transfer`).

---

### 2. Organizer Dashboard Views

#### 🔑 Page: Organizer Portal Auth (`/organizer`)
1. Provide Login and Registration forms.
2. Send sign in request to `POST /auth/organizer/login` and signup to `POST /auth/organizer/signup`.
3. Persist `access_token` and `role` properties in local storage on success.

#### 📊 Page: Organizer Dashboard Home (`/organizer/dashboard`)
1. Call `GET /auth/organizer/me` (requires Bearer header) to retrieve profile details.
2. Call `GET /events/organizer` to populate events table.
3. Call `GET /payouts/organizer` (if requesting revenue transfers) and request payout using `POST /payouts/request`.

#### ➕ Page: Create/Edit Event (`/organizer/events/new`)
1. Render event parameters matching `EventCreate` schema.
2. Submit details to `POST /events/organizer` (creates event in `draft` status).
3. Once the event is created, call `POST /events/organizer/{event_id}/ticket-types` to define pricing tier levels.
4. Click "Publish Event" to dispatch a `POST /events/organizer/{event_id}/publish` call, changing its status to `pending` (for admin moderation).

#### 📷 Page: Entry Scanner Console (`/organizer/scan`)
1. Integrate QR scanner camera library.
2. On QR scanning detection, capture ticket code and dispatch a `POST /checkin/scan` payload.
3. Render status screens depending on response validity (e.g. green for check-in successful, red for duplicate scan / already used).

---

### 3. Admin moderation Views

#### 🛡️ Page: Admin Console (`/admin/dashboard`)
1. Moderate pending events: call `GET /events/admin/pending`. Perform validation audits and invoke `POST /events/admin/approve` with `{ "approved": true }` to list on guest explorer.
2. Review payouts: call `GET /payouts/admin/pending` and approve organizer revenue transfers using `POST /payouts/admin/approve`.
3. Manage settings: call `GET /settings` and adjust commission rates using `POST /settings`.

---

## 🛠️ Complete JavaScript SDK Implementation Examples

### Authenticated Fetch Wrapper
```javascript
const API_BASE_URL = 'https://api.alphapass-ticketing.com'; // Change to actual API Gateway URL

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers
  };

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }
  return response.json();
}
```

### Guest Order Checkout
```javascript
async function submitCheckout(eventId, ticketTypeId, name, email, promoCode = null) {
  const payload = {
    event_id: eventId,
    guest_name: name,
    guest_email: email,
    items: [
      {
        ticket_type_id: ticketTypeId,
        quantity: 1,
        attendee_name: name,
        attendee_email: email
      }
    ],
    promo_code: promoCode
  };

  try {
    const result = await apiFetch('/orders', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    console.log('Checkout completed:', result);
    return result;
  } catch (error) {
    console.error('Checkout failed:', error.message);
    throw error;
  }
}
```

### Ticket Transfer Request
```javascript
async function transferTicket(ticketCode, fromEmail, toName, toEmail) {
  const payload = {
    to_name: toName,
    to_email: toEmail
  };

  try {
    const result = await apiFetch(`/transfers/${ticketCode}/transfer?guest_email=${encodeURIComponent(fromEmail)}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    console.log('Transfer logged:', result);
    return result;
  } catch (error) {
    console.error('Transfer failed:', error.message);
    throw error;
  }
}
```
