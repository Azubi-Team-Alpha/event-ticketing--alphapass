/**
 * AlphaPass API SDK & Shared Utility Script
 * Connects frontend pages to FastAPI backend (default http://localhost:8000)
 * Includes mock/demo fallback data so frontend is 100% functional even if backend is offline.
 */

const API_BASE_URL = window.ALPHAPASS_API_URL || 'http://localhost:8000';

// ── Demo / Seed Data for Offline Fallback ────────────────────────────────────
const DEMO_CATEGORIES = [
    { id: "cat-1", name: "Music & Concerts", description: "Live shows, festivals & tours" },
    { id: "cat-2", name: "Tech & Cloud Summits", description: "Developer conferences, AI & AWS summits" },
    { id: "cat-3", name: "Business & Startup", description: "Networking, pitch days & workshops" },
    { id: "cat-4", name: "Arts & Theatre", description: "Plays, comedy & exhibitions" },
    { id: "cat-5", name: "Sports & Gaming", description: "Tournaments, esports & matches" },
    { id: "cat-6", name: "Workshops & Masterclasses", description: "Skill building & hands-on bootcamps" }
];

const DEMO_EVENTS = [
    {
        id: "evt-cloud-2026",
        title: "AWS & Cloud AI Summit Accra 2026",
        description: "Join West Africa's largest gathering of Cloud Engineers, DevOps specialists, and AI practitioners. Featuring keynotes from AWS heroes, hands-on serverless labs, and networking.",
        category_id: "cat-2",
        category_name: "Tech & Cloud Summits",
        venue_name: "Accra Digital Centre",
        address: "Ring Road West",
        city: "Accra",
        country: "Ghana",
        is_online: false,
        starts_at: "2026-09-15T09:00:00",
        ends_at: "2026-09-16T18:00:00",
        status: "published",
        min_price: 150.00,
        image_url: "img/carousel-1.jpg",
        organizer_name: "Team Alpha Tech Hub",
        policies: "Refunds available up to 48 hours prior to event start. Digital QR ticket required at entry.",
        ticket_types: [
            { id: "tt-cloud-1", name: "General Admission", description: "Access to all keynotes and expo hall", price: 150.00, quantity: 300, remaining: 180, benefits: ["Keynote Access", "Expo Hall", "Swag Bag"] },
            { id: "tt-cloud-2", name: "VIP Developer Pass", description: "Front row seating, VIP lunch & workshop access", price: 350.00, quantity: 50, remaining: 22, benefits: ["VIP Lunch", "Workshop Pass", "Speaker Meet & Greet", "Swag Bag"] }
        ]
    },
    {
        id: "evt-afro-fest",
        title: "Afrobeat Horizon Music Festival",
        description: "An unforgettable night of world-class Afrobeat hits, food trucks, light shows, and surprise guest appearances at the beach front.",
        category_id: "cat-1",
        category_name: "Music & Concerts",
        venue_name: "Labadi Beach Arena",
        address: "Labadi Beach Road",
        city: "Accra",
        country: "Ghana",
        is_online: false,
        starts_at: "2026-10-02T18:00:00",
        ends_at: "2026-10-03T04:00:00",
        status: "published",
        min_price: 120.00,
        image_url: "img/carousel-2.png",
        organizer_name: "Live Nation West Africa",
        policies: "18+ only. ID check at gate. No outside drinks permitted.",
        ticket_types: [
            { id: "tt-afro-1", name: "Standard Entry", description: "Regular entry to main arena", price: 120.00, quantity: 1000, remaining: 410, benefits: ["Arena Access", "Food Court Access"] },
            { id: "tt-afro-2", name: "VIP Lounge Pass", description: "Elevated viewing deck, complimentary drinks & private bar", price: 280.00, quantity: 150, remaining: 35, benefits: ["VIP Deck", "Complimentary Drinks", "Private Bar & Restrooms"] }
        ]
    },
    {
        id: "evt-startup-pitch",
        title: "Pan-African Startup Pitch & Capital Forum",
        description: "Connect early-stage founders with venture capitalists, angel networks, and ecosystem builders across Africa.",
        category_id: "cat-3",
        category_name: "Business & Startup",
        venue_name: "Kempinski Hotel Gold Coast City",
        address: "Gamel Abdul Nasser Avenue",
        city: "Accra",
        country: "Ghana",
        is_online: false,
        starts_at: "2026-11-10T10:00:00",
        ends_at: "2026-11-10T17:00:00",
        status: "published",
        min_price: 200.00,
        image_url: "img/header-img.jpg",
        organizer_name: "Azubi Capital Ventures",
        policies: "Dress code: Business Casual. Digital ticket check-in.",
        ticket_types: [
            { id: "tt-pitch-1", name: "Attendee Ticket", description: "Access to pitch presentations & open networking", price: 200.00, quantity: 200, remaining: 95, benefits: ["Pitch Sessions", "Networking Coffee"] },
            { id: "tt-pitch-2", name: "Investor & Founder Pass", description: "Access to closed door deal room & VIP dinner", price: 500.00, quantity: 50, remaining: 14, benefits: ["Deal Room", "Founders Dinner", "1-on-1 Matchmaking"] }
        ]
    },
    {
        id: "evt-esports-ghana",
        title: "Ghana Esports & Gaming Championship 2026",
        description: "Ultimate competitive gaming tournament for EA FC 26, Tekken 8, Valorant & Street Fighter 6. Massive prize pool!",
        category_id: "cat-5",
        category_name: "Sports & Gaming",
        venue_name: "Silverbird Cinemas & Arena",
        address: "Accra Mall",
        city: "Accra",
        country: "Ghana",
        is_online: false,
        starts_at: "2026-11-20T11:00:00",
        ends_at: "2026-11-21T20:00:00",
        status: "published",
        min_price: 80.00,
        image_url: "img/product-1.png",
        organizer_name: "Esports Ghana Guild",
        policies: "Gamers must register handle before event day.",
        ticket_types: [
            { id: "tt-game-1", name: "Spectator Pass", description: "Watch all stage matches & try out gaming booths", price: 80.00, quantity: 500, remaining: 230, benefits: ["Stage Watching", "Free Play Booths"] },
            { id: "tt-game-2", name: "Player Competitor Pass", description: "Official tournament entry for 1 title", price: 150.00, quantity: 128, remaining: 40, benefits: ["Tournament Bracket Entry", "Player Jersey", "Free Play"] }
        ]
    }
];

// ── Generic API Fetch Handler with Fallback ──────────────────────────────────
async function apiFetch(path, options = {}) {
    const token = localStorage.getItem('access_token') || localStorage.getItem('organizer_token') || localStorage.getItem('admin_token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options.headers
    };

    try {
        const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error (${response.status})`);
        }
        return await response.json();
    } catch (err) {
        console.warn(`[AlphaPass API] Connection to ${API_BASE_URL}${path} failed or offline. Using local handler/fallback if applicable:`, err.message);
        return handleFallback(path, options);
    }
}

// ── Offline Fallback Router ──────────────────────────────────────────────────
function handleFallback(path, options) {
    const method = (options.method || 'GET').toUpperCase();
    const cleanPath = path.split('?')[0];

    // GET /events
    if (cleanPath === '/events' && method === 'GET') {
        const urlParams = new URLSearchParams(path.includes('?') ? path.split('?')[1] : '');
        const search = urlParams.get('search') ? urlParams.get('search').toLowerCase() : '';
        const cat = urlParams.get('category_id');

        let list = [...DEMO_EVENTS];
        if (search) {
            list = list.filter(e => e.title.toLowerCase().includes(search) || e.description.toLowerCase().includes(search) || e.city.toLowerCase().includes(search));
        }
        if (cat) {
            list = list.filter(e => e.category_id === cat);
        }
        return list;
    }

    // GET /events/categories or /categories
    if ((cleanPath === '/events/categories' || cleanPath === '/categories') && method === 'GET') {
        return DEMO_CATEGORIES;
    }

    // GET /events/{id}
    if (cleanPath.startsWith('/events/') && method === 'GET') {
        const id = cleanPath.replace('/events/', '');
        const evt = DEMO_EVENTS.find(e => e.id === id) || DEMO_EVENTS[0];
        return evt;
    }

    // POST /orders/validate-promo
    if (cleanPath === '/orders/validate-promo' && method === 'POST') {
        const body = JSON.parse(options.body || '{}');
        const code = (body.code || '').toUpperCase();
        if (code === 'ALPHA10' || code === 'AZUBI20' || code === 'DISCOUNT10') {
            return { valid: true, code, discount_percent: 15.0, message: "15% Promo Discount Applied!" };
        }
        return { valid: false, code, discount_percent: 0, message: "Invalid or expired promo code." };
    }

    // POST /orders
    if (cleanPath === '/orders' && method === 'POST') {
        const body = JSON.parse(options.body || '{}');
        const orderId = 'ORD-' + Math.floor(100000 + Math.random() * 900000);
        const ticketCode = 'TKT-' + Math.floor(100000 + Math.random() * 900000);
        const newOrder = {
            id: orderId,
            order_id: orderId,
            event_id: body.event_id || "evt-cloud-2026",
            guest_name: body.guest_name || "Guest Attendee",
            guest_email: body.guest_email || "guest@example.com",
            total_amount: body.total_amount || 150.00,
            status: "PAID",
            tickets: [
                {
                    ticket_code: ticketCode,
                    ticket_type_name: "General Admission",
                    attendee_name: body.guest_name,
                    attendee_email: body.guest_email,
                    qr_code: `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${ticketCode}`
                }
            ],
            created_at: new Date().toISOString()
        };
        // Save to local storage for persistent guest wallet testing
        const existing = JSON.parse(localStorage.getItem('alphapass_guest_orders') || '[]');
        existing.push(newOrder);
        localStorage.setItem('alphapass_guest_orders', JSON.stringify(existing));

        return newOrder;
    }

    // POST /orders/lookup
    if (cleanPath === '/orders/lookup' && method === 'POST') {
        const body = JSON.parse(options.body || '{}');
        const email = (body.email || '').toLowerCase();
        const existing = JSON.parse(localStorage.getItem('alphapass_guest_orders') || '[]');
        const matched = existing.find(o => o.guest_email.toLowerCase() === email);
        if (matched) return matched;
        // Return default demo order if none in storage
        return {
            id: "ORD-984210",
            order_id: "ORD-984210",
            guest_name: body.email.split('@')[0] || "AlphaPass Guest",
            guest_email: body.email,
            total_amount: 150.00,
            status: "PAID",
            tickets: [
                {
                    ticket_code: "TKT-883921",
                    ticket_type_name: "VIP Developer Pass",
                    attendee_name: "Demo Guest",
                    attendee_email: body.email,
                    qr_code: "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=TKT-883921"
                }
            ]
        };
    }

    // GET /tickets/{code}/status
    if (cleanPath.startsWith('/tickets/') && cleanPath.endsWith('/status')) {
        const code = cleanPath.split('/')[2];
        return {
            ticket_code: code,
            status: "VALID",
            event_title: "AWS & Cloud AI Summit Accra 2026",
            attendee_name: "Alex Mensah",
            attendee_email: "alex@example.com",
            qr_code: `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${code}`
        };
    }

    // POST /auth/organizer/login
    if (cleanPath === '/auth/organizer/login' && method === 'POST') {
        return {
            access_token: "demo_organizer_token_12345",
            token_type: "bearer",
            role: "organizer",
            organizer_id: "org-001",
            full_name: "Team Alpha Organizer",
            email: "organizer@alphapass.io"
        };
    }

    // POST /auth/admin/login
    if (cleanPath === '/auth/admin/login' && method === 'POST') {
        return {
            access_token: "demo_admin_token_67890",
            token_type: "bearer",
            role: "admin",
            admin_id: "admin-001",
            full_name: "AlphaPass Lead Admin",
            email: "admin@alphapass.io"
        };
    }

    // GET /resale/listings
    if (cleanPath === '/resale/listings' && method === 'GET') {
        return [
            {
                id: "resale-1",
                listing_id: "resale-1",
                ticket_code: "TKT-RESALE-77",
                event_title: "AWS & Cloud AI Summit Accra 2026",
                original_price: 350.00,
                asking_price: 300.00,
                seller_email: "techie99@example.com",
                status: "ACTIVE"
            },
            {
                id: "resale-2",
                listing_id: "resale-2",
                ticket_code: "TKT-RESALE-88",
                event_title: "Afrobeat Horizon Music Festival",
                original_price: 280.00,
                asking_price: 240.00,
                seller_email: "musicfan@example.com",
                status: "ACTIVE"
            }
        ];
    }

    // POST /checkin/scan
    if (cleanPath === '/checkin/scan' && method === 'POST') {
        const body = JSON.parse(options.body || '{}');
        const code = body.ticket_code || 'UNKNOWN';
        if (code.toUpperCase().includes('INVALID') || code.toUpperCase().includes('USED')) {
            return { success: false, message: `Ticket ${code} has already been scanned or is invalid!`, status: "ALREADY_USED" };
        }
        return { success: true, message: `Check-in Verified for ${code}! Welcome to the event.`, status: "CHECKED_IN", timestamp: new Date().toLocaleTimeString() };
    }

    // Default response
    return { status: "success", message: "Operation completed (Demo Mode)" };
}

// ── Local Storage Cart Manager ───────────────────────────────────────────────
const CartManager = {
    getCart() {
        try {
            return JSON.parse(localStorage.getItem('alphapass_cart') || '[]');
        } catch (e) {
            return [];
        }
    },
    addItem(item) {
        const cart = this.getCart();
        const existingIndex = cart.findIndex(c => c.ticket_type_id === item.ticket_type_id && c.event_id === item.event_id);
        if (existingIndex > -1) {
            cart[existingIndex].quantity += item.quantity;
        } else {
            cart.push(item);
        }
        localStorage.setItem('alphapass_cart', JSON.stringify(cart));
        this.updateCartBadge();
    },
    removeItem(index) {
        const cart = this.getCart();
        cart.splice(index, 1);
        localStorage.setItem('alphapass_cart', JSON.stringify(cart));
        this.updateCartBadge();
    },
    clear() {
        localStorage.removeItem('alphapass_cart');
        this.updateCartBadge();
    },
    getTotal() {
        const cart = this.getCart();
        return cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    },
    updateCartBadge() {
        const cart = this.getCart();
        const count = cart.reduce((sum, item) => sum + item.quantity, 0);
        const badges = document.querySelectorAll('.cart-count-badge');
        badges.forEach(b => b.textContent = count);
    }
};

// ── UI Alert Toast ───────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    let container = document.getElementById('alphapass-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'alphapass-toast-container';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgClass = type === 'success' ? 'bg-success' : type === 'danger' ? 'bg-danger' : type === 'warning' ? 'bg-warning text-dark' : 'bg-primary';
    toast.className = `toast align-items-center text-white ${bgClass} border-0 show`;
    toast.role = 'alert';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-bold py-2 px-3">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'danger' ? 'fa-exclamation-triangle' : 'fa-info-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        if (toast && toast.parentElement) toast.remove();
    }, 4000);
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
    CartManager.updateCartBadge();
});
