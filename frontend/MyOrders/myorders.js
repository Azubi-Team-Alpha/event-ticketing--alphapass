/**
 * Order Management System Backend Orchestration Wireframe
 */

const API_BASE = "http://localhost:8000/api/orders";
let localOrdersCache = [];
let activeFilterString = "";
let selectedOrderId = null;

// --- INITIAL EVENT BINDINGS ---
document.getElementById('searchInput').addEventListener('input', handleSearch);
document.getElementById('closeViewBtn').addEventListener('click', () => closeModal('viewOverlay'));
document.getElementById('cancelConfirmBtn').addEventListener('click', () => closeModal('confirmOverlay'));
document.getElementById('executeConfirmBtn').addEventListener('click', executeCancellation);
document.getElementById('closeResultBtn').addEventListener('click', () => closeModal('resultOverlay'));

// --- BACKEND API CONNECTIONS ---
async function loadOrdersFromBackend() {
  try {
    const response = await fetch(`${API_BASE}/my-orders`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("token")}`
      }
    });

    if (!response.ok) throw new Error("Failed to fetch tickets");
    
    localOrdersCache = await response.json();
    renderOrdersTable();
  } catch (error) {
    console.error("API error, pulling fallback simulation data:", error);
    loadMockDataFallback();
  }
}

async function executeCancellation() {
  closeModal('confirmOverlay');
  openModal('processingOverlay');

  try {
    const response = await fetch(`${API_BASE}/${selectedOrderId}/cancel`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("token")}`
      }
    });

    closeModal('processingOverlay');

    if (response.ok) {
      const order = localOrdersCache.find(o => o.id === selectedOrderId);
      if (order) order.status = 'cancelled';
      
      showResult(true, "Order Cancelled", `Order reference ${selectedOrderId} updated successfully.`);
      renderOrdersTable();
    } else {
      const errorDetails = await response.json();
      showResult(false, "Cancellation Failed", errorDetails.detail || "Server rejected request.");
    }
  } catch (error) {
    closeModal('processingOverlay');
    
    // Asynchronous network fault protection mock simulation state toggle
    const order = localOrdersCache.find(o => o.id === selectedOrderId);
    if (order) {
      order.status = 'cancelled';
      showResult(true, "Order Cancelled (Simulation)", `Local state updated for reference ${selectedOrderId}.`);
      renderOrdersTable();
    } else {
      showResult(false, "Network Error", "Unable to establish stable backend tunnel link.");
    }
  }
}

// --- FILTER & RENDER LOGIC ---
function handleSearch() {
  activeFilterString = document.getElementById('searchInput').value.toLowerCase().trim();
  renderOrdersTable();
}

function renderOrdersTable() {
  const tbody = document.getElementById('ordersTableBody');
  tbody.innerHTML = '';

  const activeDataset = localOrdersCache.filter(order => {
    if (!activeFilterString) return true;
    return order.id.toLowerCase().includes(activeFilterString) || 
           order.event.title.toLowerCase().includes(activeFilterString) ||
           order.event.venue.toLowerCase().includes(activeFilterString);
  });

  if (activeDataset.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #888; padding: 30px;">No tickets match your search parameters.</td></tr>`;
    return;
  }

  const now = new Date();

  activeDataset.forEach(order => {
    const eventDate = new Date(order.event.starts_at);
    const diffInHours = (eventDate - now) / (1000 * 60 * 60);
    
    let canCancel = true;
    let reason = "";

    if (order.status === 'cancelled') {
      canCancel = false;
      reason = "Already Cancelled";
    } else if (diffInHours < 24) {
      canCancel = false;
      reason = "Locked (Starts in less than 24h)";
    }

    const row = document.createElement('tr');
    row.innerHTML = `
      <td><strong>${order.id}</strong></td>
      <td>
        <div style="font-weight:600">${order.event.title}</div>
        <div style="font-size:12px; color:#666">Items: ${order.items ? order.items.length : 1} ticket(s)</div>
      </td>
      <td>
        <div>${eventDate.toLocaleDateString()}</div>
        <div style="font-size:12px; color:#666">${order.event.venue}</div>
      </td>
      <td><span class="badge ${order.status}">${order.status}</span></td>
      <td>
        <div class="action-btns">
          <button class="btn-sm btn-view" data-id="${order.id}">View</button>
          <button class="btn-sm btn-cancel" 
            data-id="${order.id}"
            ${!canCancel ? 'disabled' : ''}
            title="${reason}">
            ${canCancel ? 'Cancel' : 'Locked'}
          </button>
        </div>
      </td>
    `;
    
    // Explicit event attaching layout hooks
    row.querySelector('.btn-view').addEventListener('click', () => launchViewModal(order.id));
    if (canCancel) {
      row.querySelector('.btn-cancel').addEventListener('click', () => launchCancelModal(order.id));
    }
    
    tbody.appendChild(row);
  });
}

// --- INTERACTIVE ACTION MODALS CONTROLLERS ---
function launchViewModal(id) {
  const order = localOrdersCache.find(o => o.id === id);
  if (!order) return;

  document.getElementById('viewEventName').innerText = order.event.title;
  document.getElementById('viewOrderNumber').innerText = `ID Reference: ${order.id}`;
  document.getElementById('viewEventDate').innerText = new Date(order.event.starts_at).toLocaleString();
  document.getElementById('viewVenue').innerText = order.event.venue;
  document.getElementById('viewTickets').innerText = `${order.items ? order.items.length : 1} Unit(s)`;
  document.getElementById('viewAmount').innerText = `$${order.total_amount}`;

  openModal('viewOverlay');
}

function launchCancelModal(id) {
  selectedOrderId = id;
  document.getElementById('confirmText').innerText = `Are you absolutely certain you want to cancel booking registry ${id}?`;
  openModal('confirmOverlay');
}

function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

function showResult(isSuccess, title, msg) {
  document.getElementById('resultIcon').innerText = isSuccess ? '✅' : '❌';
  document.getElementById('resultIcon').style.color = isSuccess ? 'var(--success)' : 'var(--danger)';
  document.getElementById('resultTitle').innerText = title;
  document.getElementById('resultMessage').innerText = msg;
  openModal('resultOverlay');
}

// --- STRUCTURAL NORMALIZATION FALLBACK DATA ---
function loadMockDataFallback() {
  localOrdersCache = [
    {
      id: "ORD-9951",
      total_amount: "120.00",
      status: "active",
      items: [{}, {}],
      event: { title: "Summer Music Festival 2026", starts_at: "2026-08-15T19:00:00", venue: "Grand Arena, Takoradi" }
    },
    {
      id: "ORD-2041",
      total_amount: "250.00",
      status: "active",
      items: [{}],
      event: { title: "Tech Conference Africa", starts_at: "2026-07-22T09:00:00", venue: "Digital Hub" }
    },
    {
      id: "ORD-1102",
      total_amount: "45.00",
      status: "cancelled",
      items: [{}, {}, {}],
      event: { title: "Stand-up Comedy Night", starts_at: "2026-09-01T20:00:00", venue: "Laugh Lounge" }
    }
  ];
  renderOrdersTable();
}

// Run boot sequencing lifecycle hooks
window.addEventListener('DOMContentLoaded', loadOrdersFromBackend);
