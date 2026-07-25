# AlphaPass Live Demonstration Guide & Script

> **Azubi Cloud & AI Academy — Project 2 (Team Alpha)**  
> **Target Audience:** Presentation Evaluators & Stakeholders  
> **Demo Duration:** 3–5 Minutes  
> **Prerequisite:** Deployed AlphaPass Platform on AWS / Localhost

---

## 1. Demo Preparation & Browser Setup

Before starting the live demonstration, prepare your browser tabs in advance:

| Tab # | Target Page / URL | Description / Purpose |
|:---:|:---|:---|
| **Tab 1** | `http://<frontend-url>/index.html` | Public Home Page & Event Explorer |
| **Tab 2** | `http://<frontend-url>/wallet.html` | Digital Pass Wallet & PDF Ticket Download |
| **Tab 3** | `http://<frontend-url>/checkin.html` | Gate Check-in Scanner & Ticket Validator |
| **Tab 4** | `http://<frontend-url>/organizer.html` | Event Organizer Portal |
| **Tab 5** | `http://<frontend-url>/admin.html` | Admin Governance & Moderation Console |

### Demo Credentials:
- **Organizer Account:** `organizer@alphapass.com` / `OrganizerPass2026!`
- **Admin Account:** `admin@alphapass.com` / `AdminPass2026!`
- **Test Promo Code:** `AZUBI20` (20% OFF)

---

## 2. Step-by-Step Live Demo Script

---

### Phase 1: The Event Organizer Workflow (Creating & Publishing an Event)
* **Goal:** Demonstrate event creation, cover image banner upload, ticket tier setup, and sales dashboard.

1. **Open Tab 4 (`organizer.html`):**
   - Log in using Organizer credentials (`organizer@alphapass.com`).
   - Highlight the **Organizer Dashboard** showing real-time revenue metrics, total tickets sold, and active events.
2. **Create New Event:**
   - Click **"Create Event"** button.
   - Enter Event Details:
     - **Title:** `Azubi Tech Summit 2026`
     - **Category:** `Technology`
     - **Venue:** `Accra International Conference Centre`
     - **Date:** Select next month's date.
   - **Upload Banner Image:** Click **"Choose File"** for Cover Image $\rightarrow$ Select image $\rightarrow$ Show toast notification: *"Image uploaded successfully to AWS S3!"*.
3. **Configure Ticket Pass Tiers & Governance Rules:**
   - Add Ticket Tier 1: `General Admission` — Price: `$50.00`, Quantity: `100`.
   - Add Ticket Tier 2: `VIP Pass` — Price: `$150.00`, Quantity: `20`.
   - Toggle Governance Rules: Enable *Resale Allowed*, set *Max Resale Price Markup* to `10%`.
   - Click **"Publish Event"** $\rightarrow$ Show confirmation: *"Event published live!"*.

> **💬 Speaker Talking Point:**  
> *"As an event organizer, I can create an event in under two minutes. Cover images upload directly to Amazon S3, ticket pass tiers are saved to DynamoDB, and governance rules—such as secondary resale price caps—are embedded directly into the event configuration."*

---

### Phase 2: The Ticket Buyer Experience (Browsing, Promos & Guest Checkout)
* **Goal:** Demonstrate public event discovery, promo code application, and guest checkout.

1. **Open Tab 1 (`index.html` / `events.html`):**
   - Refresh the page to show `Azubi Tech Summit 2026` appearing live on the featured events grid.
   - Filter by category `Technology` to show instant client-side filtering.
2. **Single Event Pass Selection (`single.html`):**
   - Click on `Azubi Tech Summit 2026`.
   - Highlight event venue map details, policy badges (*Resale Allowed*, *Refundable*).
   - Select **2 General Admission Passes** and click **"Add to Cart"**.
3. **Cart & Promo Code Validation (`cart.html`):**
   - Navigate to Cart.
   - Enter Promo Code: `AZUBI20` $\rightarrow$ Click **"Apply"**.
   - Point out the subtotal discount calculation ($100.00 subtotal $\rightarrow$ $80.00 total after 20% discount).
4. **Guest Checkout (`checkout.html`):**
   - Enter Guest Contact Details:
     - **Full Name:** `Kwame Mensah`
     - **Email:** `kwame@example.com`
     - **Phone:** `+233 24 123 4567`
   - Select Payment Method: `Mobile Money (MTN MoMo)`.
   - Click **"Complete Purchase"**.
   - Point out the Order Confirmation screen displaying the unique Order ID (e.g. `ORD-8F92A`) and generated Ticket Pass Codes (e.g. `TCK-9921-A`, `TCK-9921-B`).

> **💬 Speaker Talking Point:**  
> *"Our guest checkout experience requires no mandatory registration. Buyers can validate promo codes with atomic DynamoDB verification and place orders instantly. Formatted ticket pass codes are generated immediately upon checkout."*

---

### Phase 3: Digital Ticket Wallet, PDF Export & Resale Exchange
* **Goal:** Demonstrate ticket retrieval, ReportLab PDF ticket download, peer transfer, and price-capped secondary resale listing.

1. **Open Tab 2 (`wallet.html`):**
   - Enter Purchaser Email: `kwame@example.com` $\rightarrow$ Click **"Lookup Order"**.
   - Show the issued ticket passes rendered with ticket status badges (`Active`).
2. **Download Printable PDF Ticket:**
   - Click **"Download PDF"** on Ticket 1 (`TCK-9921-A`).
   - Open the downloaded PDF in the browser:
     - Highlight 300-DPI vector layout, event details, venue address, attendee name, and high-resolution QR code matrix generated by ReportLab.
3. **Peer-to-Peer Ticket Transfer:**
   - On Ticket 2 (`TCK-9921-B`), click **"Transfer Ticket"**.
   - Enter Recipient Email: `friend@example.com` $\rightarrow$ Click **"Confirm Transfer"**.
   - Show toast notification: *"Pass transferred successfully! New pass code issued to recipient."*.
4. **List Ticket for Secondary Resale:**
   - On Ticket 1 (`TCK-9921-A`), click **"List for Resale"**.
   - Face Value: `$50.00`. Attempt to enter Asking Price: `$100.00` (200% markup).
   - Click **"Submit Listing"** $\rightarrow$ Show validation error: *"Asking price exceeds event maximum allowed markup cap of 10% ($55.00 max)!"*.
   - Enter valid Asking Price: `$52.00` $\rightarrow$ Click **"Submit Listing"** $\rightarrow$ Show success toast.
   - Navigate to `resale.html` to show the resale listing active on the secondary marketplace.

> **💬 Speaker Talking Point:**  
> *"In the digital ticket wallet, buyers can download printable vector PDF tickets with QR codes, transfer passes to friends, or list passes on our resale market. Notice how our platform automatically blocks predatory scalping by enforcing maximum resale price caps set by the organizer."*

---

### Phase 4: Gate Entry Check-in Scanner (Security Validation)
* **Goal:** Demonstrate real-time gate entry scanning, status updating, and duplicate check-in rejection.

1. **Open Tab 3 (`checkin.html`):**
   - Select Event: `Azubi Tech Summit 2026`.
2. **First Check-in Attempt (Valid Pass):**
   - Enter Ticket Code: `TCK-9921-A` $\rightarrow$ Click **"Verify & Check In"**.
   - Point out **SUCCESS GREEN ALERT**:
     - *Status: CHECK-IN SUCCESSFUL*
     - *Attendee: Kwame Mensah*
     - *Pass Tier: General Admission*
     - *Timestamp: Just now*
3. **Second Check-in Attempt (Duplicate Pass Rejection):**
   - Re-enter the exact same Ticket Code: `TCK-9921-A` $\rightarrow$ Click **"Verify & Check In"**.
   - Point out **DANGER RED ALERT**:
     - *Status: ENTRY REJECTED — DUPLICATE TICKET!*
     - *Reason: Ticket code TCK-9921-A was already checked in at 17:51 UTC!*

> **💬 Speaker Talking Point:**  
> *"At the event venue gate, staff use our check-in scanner. When a pass is scanned for the first time, DynamoDB atomically updates `is_used = True` and records the timestamp. If anyone attempts to reuse a cloned or copied pass, our system rejects it instantly, eliminating gate fraud."*

---

### Phase 5: Admin Governance Console & Moderation Queues
* **Goal:** Demonstrate administrative platform oversight, event approvals, payout processing, and security audit logs.

1. **Open Tab 5 (`admin.html`):**
   - Log in using Admin credentials (`admin@alphapass.com`).
   - Highlight **Platform Dashboard Stats**: Total Platform Revenue, Active Organizers, Global Commission Rate (e.g. `5.0%`).
2. **Process Organizer Payout Request:**
   - Navigate to **Payouts Queue** tab.
   - Locate pending payout request from Organizer ($450.00 net revenue after 5% platform fee).
   - Click **"Process Payout"** $\rightarrow$ Status changes from `Pending` to `Settled`.
3. **Review Audit Logs & Commission Config:**
   - View **Platform Audit Logs** showing recorded governance events.
   - Update Commission Rate: Change from `5.0%` to `5.5%` $\rightarrow$ Click **"Save Settings"** $\rightarrow$ Show confirmation toast.

> **💬 Speaker Talking Point:**  
> *"Finally, platform administrators maintain full control through our governance console. Admins review and settle organizer payout requests, moderate resale listings, process order refunds, and adjust platform commission rates in real time."*

---

## 3. Summary of Live Demo Achievements

| Demo Phase | Feature Demonstrated | Key AWS / Code Component |
|---|---|---|
| **Phase 1** | Event creation & cover image upload | S3 Bucket Direct Image Upload & DynamoDB `events` Table |
| **Phase 2** | Guest checkout & promo validation | FastAPI `/orders` router & DynamoDB Atomic Counter |
| **Phase 3** | PDF ticket export & price-capped resale | ReportLab Vector Engine & Resale Price Cap Validation |
| **Phase 4** | Gate QR check-in & duplicate rejection | FastAPI `/checkin/scan` router & Atomic `is_used` Flag |
| **Phase 5** | Admin payout settlement & commission | FastAPI `/admin/payouts` router & Platform Settings |
