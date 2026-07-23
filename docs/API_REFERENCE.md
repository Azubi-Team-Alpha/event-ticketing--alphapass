# 🎟️ AlphaPass Comprehensive API Reference Guide

This document provides a detailed endpoint reference for the **AlphaPass REST API**.

**Base Production Endpoint**: `https://{api_id}.execute-api.{region}.amazonaws.com/dev`  
**Interactive Specs**: Available locally at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc`.

---

## 🔒 Authentication & Authorization Headers

Protected endpoints require a standard Bearer token in the `Authorization` request header:

```http
Authorization: Bearer <your_jwt_access_token>
```

### Roles:
- **Guest / Public**: No token required.
- **Organizer**: Token obtained via `POST /auth/organizer/login`.
- **Admin**: Token obtained via `POST /auth/admin/login`.

---

## 1. System & Health

### `GET /health`
Returns system status and API version.
- **Auth**: Public
- **Response `200 OK`**:
  ```json
  {
    "status": "ok",
    "app": "AlphaPass API",
    "version": "2.0.0"
  }
  ```

---

## 2. Event Catalog & Discovery

### `GET /events`
List published events with optional filtering and search.
- **Auth**: Public
- **Query Parameters**:
  - `search` *(string, optional)*: Filter by title, description, or city.
  - `category_id` *(string, optional)*: Filter by event category UUID.
  - `city` *(string, optional)*: Filter by city.
  - `page` *(int, default: 1)*: Page number.
  - `limit` *(int, default: 50)*: Items per page.
- **Response `200 OK`**:
  ```json
  {
    "items": [
      {
        "id": "evt-cloud-2026",
        "organizer_id": "org-001",
        "category_name": "Technology",
        "title": "Accra Tech & AI Carnival 2026",
        "description": "Premier West Africa Tech Conference",
        "banner_image_url": "https://alphapass-assets-dev.s3.amazonaws.com/events/banners/cover.jpg",
        "venue_name": "Accra Digital Centre",
        "city": "Accra",
        "country": "Ghana",
        "starts_at": "2026-08-15T09:00:00Z",
        "ends_at": "2026-08-15T18:00:00Z",
        "min_price": 100.0,
        "status": "published",
        "ticket_types": [
          {
            "id": "tt-gen",
            "name": "General Admission",
            "price": "100.00",
            "quantity": 500,
            "quantity_sold": 45,
            "quantity_remaining": 455,
            "is_sold_out": false
          }
        ]
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 50
  }
  ```

### `GET /events/{event_id}`
Retrieve complete details and ticket pass tiers for a single event.
- **Auth**: Public
- **Response `200 OK`**: `EventResponse` object.
- **Response `404 Not Found`**: `{ "detail": "Event not found" }`

### `GET /events/categories`
List available event categories.
- **Auth**: Public
- **Response `200 OK`**: Array of `EventCategoryResponse`.

---

## 3. Orders, Reservations & Payments

### `POST /orders`
Create a guest order for one or more ticket pass tiers.
- **Auth**: Public / Guest
- **Request Body**:
  ```json
  {
    "event_id": "evt-cloud-2026",
    "guest_name": "Alice Johnson",
    "guest_email": "alice@example.com",
    "guest_phone": "+233240000000",
    "items": [
      {
        "ticket_type_id": "tt-gen",
        "quantity": 2,
        "attendee_name": "Alice Johnson",
        "attendee_email": "alice@example.com"
      }
    ],
    "promo_code": "ALPHA10",
    "payment_method": "Mobile Money"
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "id": "ORD-882103",
    "event_id": "evt-cloud-2026",
    "guest_name": "Alice Johnson",
    "guest_email": "alice@example.com",
    "total_amount": "180.00",
    "discount_amount": "20.00",
    "status": "confirmed",
    "created_at": "2026-07-23T09:00:00Z",
    "tickets": [
      {
        "id": "tkt-001",
        "ticket_code": "TKT-882103-1",
        "attendee_name": "Alice Johnson",
        "attendee_email": "alice@example.com",
        "qr_code": "https://alphapass-assets-dev.s3.amazonaws.com/tickets/qr/TKT-882103-1.png",
        "status": "active"
      }
    ]
  }
  ```

### `POST /orders/lookup`
Retrieve wallet orders matching guest purchaser email.
- **Auth**: Public
- **Request Body**: `{ "email": "alice@example.com", "order_id": "ORD-882103" }`
- **Response `200 OK`**: Array of `OrderResponse`.

### `POST /orders/validate-promo`
Check promo code validity and calculate discount percentage.
- **Auth**: Public
- **Request Body**: `{ "code": "ALPHA10", "event_id": "evt-cloud-2026" }`
- **Response `200 OK`**: `{ "valid": true, "discount_percent": 10.0, "message": "Promo code applied successfully!" }`

### `POST /orders/{order_id}/cancel`
Cancel guest order and invalidate issued ticket passes.
- **Auth**: Public
- **Request Body**: `{ "guest_email": "alice@example.com" }`
- **Response `200 OK`**: `{ "message": "Order cancelled" }`

---

## 4. Ticket Pass PDF & Verification

### `GET /tickets/{ticket_code}`
Fetch pass status and ticket details.
- **Auth**: Public
- **Response `200 OK`**: `TicketResponse` object.

### `GET /tickets/{ticket_code}/pdf`
Download printable PDF ticket pass file.
- **Auth**: Public
- **Response `200 OK`**: Binary PDF file (`Content-Type: application/pdf`).

---

## 5. Secondary Resale Market & Transfers

### `GET /resale/listings`
Browse active resale listings.
- **Auth**: Public
- **Query Parameters**: `event_id` *(optional)*
- **Response `200 OK`**: Array of `ResaleListingResponse`.

### `POST /resale/tickets/{ticket_code}`
List an active ticket pass on the resale exchange.
- **Auth**: Public (Seller email validation)
- **Request Body**:
  ```json
  {
    "seller_name": "Alice Johnson",
    "seller_email": "alice@example.com",
    "asking_price": 105.00
  }
  ```
- **Response `201 Created`**: `ResaleListingResponse` object.

### `POST /resale/{listing_id}/purchase`
Purchase a resale ticket pass.
- **Auth**: Public
- **Request Body**: `{ "buyer_name": "Bob Marley", "buyer_email": "bob@example.com" }`
- **Response `201 Created`**: Newly issued `TicketResponse` for buyer.

### `POST /transfers/{ticket_code}/transfer`
Transfer a ticket pass to another recipient.
- **Auth**: Public (Guest email validation)
- **Query Parameter**: `guest_email` *(string, required)*
- **Request Body**: `{ "recipient_name": "Charlie", "recipient_email": "charlie@example.com" }`
- **Response `200 OK`**: `{ "message": "Ticket transferred successfully" }`

---

## 6. Gate Check-In & Gate Scanner

### `POST /checkin/scan`
Scan QR code ticket pass at event gate entrance.
- **Auth**: Organizer / Admin (`Bearer <organizer_token>`)
- **Request Body**: `{ "ticket_code": "TKT-882103-1" }`
- **Response `200 OK`**:
  ```json
  {
    "valid": true,
    "message": "✅ Check-in successful! Welcome!",
    "attendee_name": "Alice Johnson",
    "ticket_type_name": "General Admission",
    "event_title": "Accra Tech & AI Carnival 2026"
  }
  ```

---

## 7. Organizer Management Portal

### `POST /auth/organizer/signup`
Register new organizer account.
- **Request Body**: `{ "full_name": "Sam Kwesi", "business_name": "Alpha Events Ltd", "email": "sam@alpha.com", "password": "securepassword" }`

### `POST /auth/organizer/login`
Authenticate organizer.
- **Request Body**: `{ "email": "sam@alpha.com", "password": "securepassword" }`
- **Response `200 OK`**: `{ "access_token": "eyJhb...", "token_type": "bearer" }`

### `GET /organizer/dashboard`
Get organizer analytics and sales metrics.
- **Auth**: Organizer Bearer Token
- **Response `200 OK`**:
  ```json
  {
    "total_events": 5,
    "published_events": 4,
    "total_orders": 42,
    "total_tickets_sold": 85,
    "gross_revenue": "8500.00",
    "platform_fees": "425.00",
    "net_earnings": "8075.00",
    "pending_payout": "8075.00"
  }
  ```

### `POST /events/upload-banner`
Upload cover banner image to AWS S3 bucket.
- **Auth**: Organizer Bearer Token
- **Request Body**: Multipart form data (`file`)
- **Response `200 OK`**: `{ "image_url": "https://alphapass-assets-dev.s3.us-east-1.amazonaws.com/events/banners/uuid_banner.jpg" }`

### `GET /organizer/events/{event_id}/attendees`
Export event attendee roster.
- **Auth**: Organizer Bearer Token
- **Query Parameter**: `format` (`json` or `csv`)
- **Response `200 OK`**: Array of attendee objects or CSV download stream.

---

## 8. Admin Governance & Platform Moderation

### `POST /auth/admin/login`
Authenticate administrator console.
- **Request Body**: `{ "email": "admin@alphapass.alphateam.live", "password": "adminpassword" }`

### `GET /admin/dashboard`
Fetch platform governance overview.
- **Auth**: Admin Bearer Token
- **Response `200 OK`**: `{ "total_events": 12, "published_events": 10, "total_organizers": 8, "total_platform_fees": "1425.00" }`

### `GET /admin/events`
List all events across platform including drafts and pending reviews.
- **Auth**: Admin Bearer Token

### `PUT /admin/events/{id}/approve`
Approve or reject event listing submission.
- **Auth**: Admin Bearer Token
- **Request Body**: `{ "approved": true }`
- **Response `200 OK`**: `{ "message": "Event approved and published live" }`

### `PUT /admin/config/commission`
Set global platform fee percentage.
- **Auth**: Admin Bearer Token
- **Request Body**: `{ "commission_percent": 5.0 }`
- **Response `200 OK`**: `{ "message": "Commission updated to 5.0%" }`
