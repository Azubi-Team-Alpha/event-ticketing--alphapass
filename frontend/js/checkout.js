const API_BASE_URL = window.ALPHAPASS_API_URL || '';

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

// ---- Read URL params (event_id, type_id, qty) ----
const params = new URLSearchParams(window.location.search);
const eventId = params.get('event_id');
const preselectedTypeId = params.get('type_id');
const preselectedQty = params.get('qty');

if (preselectedQty) quantityInput.value = preselectedQty;

// ---- Populate ticket types dropdown ----
async function loadTicketTypes() {
  if (!eventId) return;
  try {
    const event = await apiFetch(`/events/${eventId}`);
    (event.ticket_types || []).forEach((t) => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = `${t.name} — GHS ${t.price}`;
      ticketTypeSelect.appendChild(opt);
    });
    if (preselectedTypeId) {
      ticketTypeSelect.value = preselectedTypeId;
    }
  } catch (err) {
    showAlert('error', 'Could not load ticket types for this event.');
  }
}
loadTicketTypes();

// ---- Validation ----
function clearErrors() {
  document.querySelectorAll('.error-text').forEach((el) => (el.textContent = ''));
  document.querySelectorAll('input, select').forEach((el) => el.classList.remove('invalid'));
}

function setFieldError(fieldId, message) {
  document.getElementById(`err-${fieldId}`).textContent = message;
  document.getElementById(fieldId).classList.add('invalid');
}

function validateForm() {
  clearErrors();
  let isValid = true;

  const name = guestNameInput.value.trim();
  const email = guestEmailInput.value.trim();
  const phone = guestPhoneInput.value.trim();
  const ticketTypeId = ticketTypeSelect.value;
  const quantity = Number(quantityInput.value);

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
  alertBox.textContent = message;
  alertBox.className = `alert ${type}`;
  alertBox.classList.remove('hidden');
}

function hideAlert() {
  alertBox.classList.add('hidden');
}

// ---- Promo code check ----
applyPromoBtn.addEventListener('click', async () => {
  const code = promoCodeInput.value.trim();
  if (!code) return;

  try {
    const data = await apiFetch(`/promo/${encodeURIComponent(code)}`);
    promoStatusEl.textContent = `Promo applied: ${data.discount_percent ?? ''}% off`;
    promoStatusEl.style.color = 'green';
  } catch (err) {
    promoStatusEl.textContent = 'Promo code not found or expired.';
    promoStatusEl.style.color = 'red';
  }
});

// ---- Submit handler ----
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideAlert();

  if (!validateForm()) {
    showAlert('error', 'Please fix the highlighted fields before continuing.');
    return;
  }

  const payload = {
    event_id: eventId,
    guest_name: guestNameInput.value.trim(),
    guest_email: guestEmailInput.value.trim(),
    guest_phone: guestPhoneInput.value.trim() || undefined,
    items: [
      {
        ticket_type_id: ticketTypeSelect.value,
        quantity: Number(quantityInput.value),
        attendee_name: guestNameInput.value.trim(),
        attendee_email: guestEmailInput.value.trim(),
      },
    ],
    promo_code: promoCodeInput.value.trim() || undefined,
  };

  submitBtn.disabled = true;
  submitBtn.textContent = 'Processing...';

  try {
    const order = await apiFetch('/orders', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    showAlert('success', 'Order placed! Check your email for ticket confirmation.');
    form.reset();
    // Optional: redirect to a confirmation page
    // window.location.href = `/tickets/${order.tickets[0].code}`;
  } catch (err) {
    showAlert('error', err.message || 'Something went wrong. Please try again.');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Complete Purchase';
  }
});
