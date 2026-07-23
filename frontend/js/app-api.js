/**
 * AlphaPass API SDK & Shared Utility Script
 * Connects frontend pages to AWS API Gateway + Lambda backend
 */

const API_BASE_URL = window.ALPHAPASS_API_URL || '';

// Warn loudly in console if API URL is not configured
if (!API_BASE_URL) {
    console.error(
        '[AlphaPass] ALPHAPASS_API_URL is not set! ' +
        'All API calls will fail. Set window.ALPHAPASS_API_URL in your config or index.html.'
    );
}

// ── Generic API Fetch Handler ────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
    const token = localStorage.getItem('access_token') || localStorage.getItem('organizer_token') || localStorage.getItem('admin_token');

    // Transform request payload if needed
    let fetchOptions = { ...options };
    if (fetchOptions.body && typeof fetchOptions.body === 'string') {
        try {
            const bodyObj = JSON.parse(fetchOptions.body);
            // Handle /auth/organizer/signup payload mapping
            if (path === '/auth/organizer/signup') {
                if (!bodyObj.organization_name) {
                    bodyObj.organization_name = bodyObj.business_name || bodyObj.full_name || 'Organization';
                }
                if (!bodyObj.contact_name) {
                    bodyObj.contact_name = bodyObj.full_name || bodyObj.business_name || 'Contact Person';
                }
                fetchOptions.body = JSON.stringify(bodyObj);
            }
        } catch (e) {
            // retain original string
        }
    }

    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options.headers
    };

    try {
        const response = await fetch(`${API_BASE_URL}${path}`, { ...fetchOptions, headers });

        // ── 401 handling: token expired or invalid ─────────────────────────
        if (response.status === 401) {
            const isAuthEndpoint = path.includes('/auth/');
            if (!isAuthEndpoint) {
                _handleTokenExpiry();
                throw new Error('Session expired. Please log in again.');
            }
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            let errMsg = errData.detail || `Server error (${response.status})`;
            if (Array.isArray(errData.detail)) {
                errMsg = errData.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join(', ');
            }
            throw new Error(errMsg);
        }
        const data = await response.json();
        return normalizeResponse(path, data);
    } catch (err) {
        console.error(`[AlphaPass API Error] Request to ${API_BASE_URL}${path} failed:`, err.message);
        throw err;
    }
}

/**
 * Handle expired or invalid tokens: clear storage and prompt re-login.
 */
function _handleTokenExpiry() {
    const wasLoggedIn = !!(
        localStorage.getItem('access_token') ||
        localStorage.getItem('organizer_token') ||
        localStorage.getItem('admin_token')
    );

    localStorage.removeItem('access_token');
    localStorage.removeItem('organizer_token');
    localStorage.removeItem('admin_token');

    if (wasLoggedIn) {
        showToast('Your session has expired. Please log in again.', 'warning');
        // Redirect to login after a short delay so the toast is visible
        setTimeout(() => {
            const currentPage = window.location.pathname.split('/').pop() || '';
            // Only redirect if we are not already on a login page
            if (!currentPage.includes('login') && !currentPage.includes('index') && currentPage !== '') {
                const isOrganizer = !!localStorage.getItem('organizer_role');
                window.location.href = isOrganizer ? 'organizer-login.html' : 'login.html';
            }
        }, 2000);
    }
}

// ── Normalize API Responses for Uniform Frontend Usage ──────────────────────
function normalizeResponse(path, data) {
    const cleanPath = path.split('?')[0];

    // /events endpoint returns { items: [...], total, page, limit }
    // Preserve pagination metadata; expose items directly on the returned object
    if ((cleanPath === '/events' || cleanPath === '/events/search') && data && data.items) {
        const normalized = data.items.map(e => ({
            ...e,
            category_name: e.category_name || (e.category ? e.category.name : 'Event'),
            image_url: e.banner_image_url || e.thumbnail_url || e.image_url || 'img/header-img.jpg',
            min_price: e.min_price !== undefined ? parseFloat(e.min_price) : 0.00
        }));
        // Attach pagination metadata as non-enumerable properties so list
        // iteration still yields plain event objects while callers can access
        // data.total / data.page / data.limit if they need it.
        normalized._total = data.total;
        normalized._page = data.page;
        normalized._limit = data.limit;
        return normalized;
    }

    // Single event /events/{id}
    if (cleanPath.startsWith('/events/') && data && data.id) {
        return {
            ...data,
            category_name: data.category_name || (data.category ? data.category.name : 'Event'),
            image_url: data.banner_image_url || data.thumbnail_url || data.image_url || 'img/header-img.jpg',
            min_price: data.min_price !== undefined ? parseFloat(data.min_price) : 0.00,
            organizer_name: data.organizer_name || 'Official Organizer'
        };
    }

    return data;
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
    getItems() {
        return this.getCart();
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

// ── HTML Sanitizer (prevent XSS in dynamic text injection) ───────────────────
/**
 * Escapes user-controlled strings before injecting into innerHTML.
 * @param {string} str
 * @returns {string} HTML-entity-escaped string
 */
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
}

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
    const icon = type === 'success' ? 'fa-check-circle' : type === 'danger' ? 'fa-exclamation-triangle' : type === 'warning' ? 'fa-exclamation-circle' : 'fa-info-circle';
    // Use sanitizeHTML to prevent XSS from API error messages
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-bold py-2 px-3">
                <i class="fas ${icon} me-2"></i>
                ${sanitizeHTML(message)}
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
