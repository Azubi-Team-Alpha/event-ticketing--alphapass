/**
 * AlphaPass Checkout Page Script
 * Handles ticket type loading, promo validation, and order submission.
 * Connects to AWS API Gateway backend via app-api.js apiFetch.
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^\+?[0-9]{7,15}$/;

// ---- Grab elements once ----
const form = document.getElementById('checkoutForm');
const alertBox = document.getElementById('alertBox');
const submitBtn = document.getElementById('submitBtn');

const guestNameInput = document.getElementById('guestName');
const guestEmailInput = document.getElementById('guestEmail');
const guestPhoneInput = document.getElementById('guestPhone');
const ticketTypeSelect = document.getElementById('ticketType');
const quantityInput = document.getElementById('quantity');
const promoCodeInput = document.getElementById('promoCode');
const promoStatusEl = document.getElementById('promoStatus');
const applyPromoBtn = document.getElementById('applyPromoBtn');
const eventTitleEl = document.getElementById('eventTitleDisplay');

// ---- Read URL params (event_id, type_id, qty) ----
const params = new URLSearchParams(window.location.search);
const eventId = params.get('event_id');
const preselectedTypeId = params.get('type_id');
const preselectedQty = params.get('qty');

if (preselectedQty && quantityInput) quantityInput.value = preselectedQty;

// Applied promo state
let appliedPromo = null;

// ---- Load event details & populate ticket types ----
async function loadEventAndTicketTypes() {
  if (!eventId) return;
  try {
    const event = await apiFetch(`/events/${eventId}`);

    // Show event title on page
    if (eventTitleEl) {
      eventTitleEl.textContent = event.title || 'Event Checkout';
    }
    document.title = `Checkout – ${event.title || 'AlphaPass'}`;

    // Populate ticket type options
    if (ticketTypeSelect) {
      (event.ticket_types || []).forEach((t) => {
        if (!t.is_active || t.quantity_remaining <= 0) return; // skip inactive/sold out
        const opt = document.createElement('option');
        opt.value = t.id;
        const remaining = t.quantity_remaining !== undefined ? ` (${t.quantity_remaining} left)` : '';
        opt.textContent = `${t.name} — GHS ${parseFloat(t.price).toFixed(2)}${remaining}`;
        opt.dataset.price = t.price;
        opt.dataset.limit = t.purchase_limit || 10;
        ticketTypeSelect.appendChild(opt);
      });
      if (preselectedTypeId) {
        ticketTypeSelect.value = preselectedTypeId;
      }
      updatePriceSummary();
    }
  } catch (err) {
    showAlert('error', 'Could not load event details. Please try again.');
  }
}
loadEventAndTicketTypes();

// ---- Update price summary on ticket type / qty change ----
function updatePriceSummary() {
  const summaryEl = document.getElementById('priceSummary');
  if (!summaryEl || !ticketTypeSelect) return;
  const selected = ticketTypeSelect.options[ticketTypeSelect.selectedIndex];
  const price = parseFloat(selected?.dataset?.price || 0);
  const qty = parseInt(quantityInput?.value || 1, 10);
  if (isNaN(price) || isNaN(qty)) return;
  const subtotal = price * qty;
  summaryEl.textContent = `Subtotal: GHS ${subtotal.toFixed(2)}`;
}

if (ticketTypeSelect) ticketTypeSelect.addEventListener('change', updatePriceSummary);
if (quantityInput) quantityInput.addEventListener('input', updatePriceSummary);

// ---- Validation ----
function clearErrors() {
  document.querySelectorAll('.error-text').forEach((el) => (el.textContent = ''));
  document.querySelectorAll('input, select').forEach((el) => el.classList.remove('invalid'));
}

function setFieldError(fieldId, message) {
  const errEl = document.getElementById(`err-${fieldId}`);
  const field = document.getElementById(fieldId);
  if (errEl) errEl.textContent = message;
  if (field) field.classList.add('invalid');
}

function validateForm() {
  clearErrors();
  let isValid = true;

  const name = guestNameInput?.value.trim();
  const email = guestEmailInput?.value.trim();
  const phone = guestPhoneInput?.value.trim();
  const ticketTypeId = ticketTypeSelect?.value;
  const quantity = Number(quantityInput?.value);

  if (!name) {
    setFieldError('guestName', 'Name is required.');
    isValid = false;
  }

  if (!email) {
    setFieldError('guestEmail', 'Email is required.');
    isValid = false;
  } else if (!EMAIL_REGEX.test(email)) {
    setFieldError('guestEmail', 'Enter a valid email address.');
    isValid = false;
  }

  if (phone && !PHONE_REGEX.test(phone)) {
    setFieldError('guestPhone', 'Enter a valid phone number (e.g. +233240000000).');
    isValid = false;
  }

  if (!ticketTypeId) {
    setFieldError('ticketType', 'Please select a ticket type.');
    isValid = false;
  }

  if (!quantity || quantity < 1) {
    setFieldError('quantity', 'Quantity must be at least 1.');
    isValid = false;
  }

  return isValid;
}

// ---- Alert helper ----
function showAlert(type, message) {
  if (!alertBox) return;
  alertBox.textContent = message;
  alertBox.className = `alert ${type}`;
  alertBox.classList.remove('hidden');
}

function hideAlert() {
  if (alertBox) alertBox.classList.add('hidden');
}

// ---- Promo code validation (uses correct POST endpoint) ----
if (applyPromoBtn) {
  applyPromoBtn.addEventListener('click', async () => {
    const code = promoCodeInput?.value.trim();
    if (!code || !eventId) return;

    applyPromoBtn.disabled = true;
    applyPromoBtn.textContent = 'Checking...';
    try {
      const data = await apiFetch(`/orders/validate-promo`, {
        method: 'POST',
        body: JSON.stringify({ code, event_id: eventId }),
      });
      if (data.valid) {
        appliedPromo = data;
        const discLabel = data.discount_type === 'percentage'
          ? `${parseFloat(data.discount_value).toFixed(0)}% off`
          : `GHS ${parseFloat(data.discount_value).toFixed(2)} off`;
        if (promoStatusEl) {
          promoStatusEl.textContent = `✅ Promo applied: ${discLabel}`;
          promoStatusEl.style.color = 'green';
        }
      } else {
        appliedPromo = null;
        if (promoStatusEl) {
          promoStatusEl.textContent = `❌ ${data.message || 'Invalid promo code'}`;
          promoStatusEl.style.color = 'red';
        }
      }
    } catch (err) {
      appliedPromo = null;
      if (promoStatusEl) {
        promoStatusEl.textContent = 'Could not validate promo code.';
        promoStatusEl.style.color = 'red';
      }
    } finally {
      applyPromoBtn.disabled = false;
      applyPromoBtn.textContent = 'Apply';
    }
  });
}

// ---- Submit handler ----
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlert();

    if (!validateForm()) {
      showAlert('error', 'Please fix the highlighted fields before continuing.');
      return;
    }

    const guestEmail = guestEmailInput.value.trim();
    const payload = {
      event_id: eventId,
      guest_name: guestNameInput.value.trim(),
      guest_email: guestEmail,
      guest_phone: guestPhoneInput?.value.trim() || undefined,
      items: [
        {
          ticket_type_id: ticketTypeSelect.value,
          quantity: Number(quantityInput.value),
          attendee_name: guestNameInput.value.trim(),
          attendee_email: guestEmail,
        },
      ],
      promo_code: appliedPromo ? (promoCodeInput?.value.trim() || undefined) : undefined,
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing…';

    try {
      const order = await apiFetch('/orders', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      showAlert('success', `Order confirmed! Order ID: ${order.id}. Redirecting to your wallet…`);
      form.reset();
      appliedPromo = null;
      if (promoStatusEl) promoStatusEl.textContent = '';

      // Redirect to wallet with email and order ID pre-filled after short delay
      setTimeout(() => {
        window.location.href = `wallet.html?email=${encodeURIComponent(guestEmail)}&order_id=${encodeURIComponent(order.id)}`;
      }, 2000);
    } catch (err) {
      showAlert('error', err.message || 'Something went wrong. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Complete Purchase';
    }
  });
}
