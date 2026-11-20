// Pharma Bridge · Central Distributor & Fulfillment Hub Client

const API_BASE = (window.location.hostname === 'localhost' && window.location.port !== '8000')
  ? 'http://localhost:8000/api/v1'
  : '/api/v1';

let authToken = localStorage.getItem('pharma_distributor_token') || localStorage.getItem('rx_token') || '';
let currentDistUser = null;
let currentOrders = [];
let currentFilter = 'all';
let searchDebounceTimer = null;

function distHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`
  };
}

// ═══════════════ INITIALIZATION & AUTH ═══════════════
document.addEventListener('DOMContentLoaded', async () => {
  if (authToken) {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: distHeaders() });
      if (res.ok) {
        currentDistUser = await res.json();
        initDashboard();
        return;
      }
    } catch (e) {
      console.warn('Distributor auth token expired:', e);
    }
  }
  showLogin();
});

function showLogin() {
  document.getElementById('distLoginScreen').style.display = 'flex';
  document.getElementById('distMainContent').style.display = 'none';
}

function initDashboard() {
  document.getElementById('distLoginScreen').style.display = 'none';
  document.getElementById('distMainContent').style.display = 'block';
  document.getElementById('distributorUserEmail').textContent = currentDistUser?.email || 'Distributor';
  loadStats();
  loadOrders();
}

window.doDistributorLogin = async function() {
  const email = document.getElementById('distLoginEmail').value.trim();
  const password = document.getElementById('distLoginPass').value.trim();
  const errDiv = document.getElementById('distLoginError');
  errDiv.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      errDiv.textContent = d.detail || 'Invalid distributor login credentials';
      errDiv.style.display = 'block';
      return;
    }
    const data = await res.json();
    authToken = data.access_token;
    localStorage.setItem('pharma_distributor_token', authToken);
    currentDistUser = data.user;
    initDashboard();
  } catch (err) {
    errDiv.textContent = 'Connection error: ' + err.message;
    errDiv.style.display = 'block';
  }
};

window.distributorLogout = function() {
  localStorage.removeItem('pharma_distributor_token');
  authToken = '';
  currentDistUser = null;
  showLogin();
};

// ═══════════════ KPI STATS ═══════════════
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/distributor/stats`, { headers: distHeaders() });
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById('kpiPending').textContent = stats.pending || 0;
    document.getElementById('kpiDispatched').textContent = stats.out_for_delivery || 0;
    document.getElementById('kpiRefills').textContent = stats.refills_due_next_7_days || 0;
    document.getElementById('kpiCommissions').textContent = `₹${(stats.total_doctor_commission || 0).toLocaleString('en-IN')}`;
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
}

// ═══════════════ ORDERS QUEUE ═══════════════
window.filterOrdersByStatus = function(status) {
  currentFilter = status;
  loadOrders();
};

window.debouncedSearch = function() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(loadOrders, 300);
};

async function loadOrders() {
  const tbody = document.getElementById('distOrdersTableBody');
  const search = document.getElementById('distOrderSearch')?.value.trim();
  let url = `${API_BASE}/distributor/orders?status=${encodeURIComponent(currentFilter)}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await fetch(url, { headers: distHeaders() });
    if (!res.ok) throw new Error('Failed to fetch orders');
    const orders = await res.json();
    currentOrders = orders;
    renderOrders(orders);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#ef4444;">${err.message}</td></tr>`;
  }
}

function renderOrders(orders) {
  const tbody = document.getElementById('distOrdersTableBody');
  if (!orders || orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8;">No consented prescription orders found in this filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = orders.map(o => {
    const statusClass = `status-${o.fulfillment_status}`;
    const medsShort = o.medicines.map(m => m.name).slice(0, 3).join(', ') + (o.medicines.length > 3 ? '...' : '');
    return `
      <tr>
        <td><strong>${esc(o.rx_number)}</strong><div style="font-size:11px;color:#64748b;">${o.completed_at ? new Date(o.completed_at).toLocaleDateString('en-IN') : ''}</div></td>
        <td>
          <strong>${esc(o.patient_name)}</strong> (${esc(o.patient_age_gender)})
          <div style="font-size:11px;color:#0d9488;">📞 +91 ${esc(o.patient_mobile)}</div>
        </td>
        <td>
          ${esc(o.doctor_name)}
          <div style="font-size:11px;color:#64748b;">${esc(o.clinic_name)}</div>
        </td>
        <td>
          <span style="font-size:12px;">${esc(medsShort)}</span>
          <div style="font-size:11px;color:#64748b;">${o.medicines_count} item(s)</div>
        </td>
        <td><span class="status-pill ${statusClass}">${o.fulfillment_status.replace(/_/g, ' ')}</span></td>
        <td><strong>₹${o.estimated_value}</strong><div style="font-size:11px;color:#7c3aed;">Comm: ₹${o.doctor_commission}</div></td>
        <td>
          <button class="btn-action btn-pack" onclick="openOrderDetailModal(${o.id})">🔍 View & Pack</button>
          <button class="btn-action btn-wa" onclick="sendCourierWhatsApp(${o.id})">💬 Dispatch WhatsApp</button>
        </td>
      </tr>
    `;
  }).join('');
}

// ═══════════════ ORDER DETAILS & PACKING MODAL ═══════════════
window.openOrderDetailModal = function(orderId) {
  const order = currentOrders.find(o => o.id === orderId);
  if (!order) return;

  document.getElementById('modalRxNumber').textContent = `Order Fulfillment: ${order.rx_number}`;
  const content = document.getElementById('modalOrderContent');

  const medsRows = order.medicines.map(m => `
    <tr>
      <td style="padding:8px;border-bottom:1px solid #f1f5f9;"><strong>${esc(m.name)}</strong> ${m.is_chronic ? '<span style="font-size:10px;background:#fef3c7;color:#b45309;padding:2px 6px;border-radius:6px;">Chronic</span>' : ''}</td>
      <td style="padding:8px;border-bottom:1px solid #f1f5f9;">${esc(m.dose || '—')}</td>
      <td style="padding:8px;border-bottom:1px solid #f1f5f9;">${esc(m.frequency || '—')}</td>
      <td style="padding:8px;border-bottom:1px solid #f1f5f9;">${esc(m.food_relation || '—')}</td>
      <td style="padding:8px;border-bottom:1px solid #f1f5f9;"><strong>${esc(m.duration || '—')}</strong></td>
    </tr>
  `).join('');

  content.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;background:#f8fafc;padding:14px;border-radius:10px;margin-bottom:16px;font-size:13px;">
      <div>
        <strong>Patient:</strong> ${esc(order.patient_name)} (${esc(order.patient_age_gender)})<br>
        <strong>Phone:</strong> +91 ${esc(order.patient_mobile)}<br>
        <strong>Diagnosis:</strong> ${esc(order.diagnosis || 'General Consultation')}
      </div>
      <div>
        <strong>Prescribed By:</strong> ${esc(order.doctor_name)}<br>
        <strong>Hospital:</strong> ${esc(order.clinic_name)}<br>
        <strong>Official PDF:</strong> ${order.pdf_url ? `<a href="${order.pdf_url}" target="_blank" style="color:#0d9488;font-weight:600;">Download Cloud PDF ↗</a>` : '<span style="color:#94a3b8;">Pending upload</span>'}
      </div>
    </div>

    <h4 style="margin:12px 0 6px;color:#1a2744;">📦 Prescribed Medication Packing List</h4>
    <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:16px;">
      <thead>
        <tr style="background:#f1f5f9;text-align:left;">
          <th style="padding:8px;">Drug Name</th>
          <th style="padding:8px;">Dose</th>
          <th style="padding:8px;">Frequency</th>
          <th style="padding:8px;">Timing</th>
          <th style="padding:8px;">Duration</th>
        </tr>
      </thead>
      <tbody>${medsRows}</tbody>
    </table>

    <div style="margin-bottom:16px;">
      <label style="display:block;font-size:12px;font-weight:600;margin-bottom:6px;">Warehouse & Dispatch Notes</label>
      <input type="text" id="modalDispatchNotes" value="${esc(order.dispatch_notes || '')}" placeholder="e.g. Batch #49281, packed by warehouse team, courier assigned" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;font-size:13px;box-sizing:border-box;">
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid #e2e8f0;padding-top:16px;">
      <div style="font-size:12px;color:#64748b;">
        Current Status: <span class="status-pill status-${order.fulfillment_status}">${order.fulfillment_status.replace(/_/g, ' ')}</span>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn-action btn-pack" onclick="updateOrderStatus(${order.id}, 'packing')">📦 Mark Packing</button>
        <button class="btn-action btn-dispatch" onclick="updateOrderStatus(${order.id}, 'out_for_delivery')">🚚 Dispatch</button>
        <button class="btn-action" style="background:#15803d;color:#fff;" onclick="updateOrderStatus(${order.id}, 'delivered')">✅ Delivered</button>
      </div>
    </div>
  `;

  document.getElementById('orderDetailModal').style.display = 'flex';
};

window.closeOrderDetailModal = function() {
  document.getElementById('orderDetailModal').style.display = 'none';
};

window.updateOrderStatus = async function(orderId, nextStatus) {
  const notes = document.getElementById('modalDispatchNotes')?.value || '';
  try {
    const res = await fetch(`${API_BASE}/distributor/orders/${orderId}/status`, {
      method: 'POST',
      headers: distHeaders(),
      body: JSON.stringify({ status: nextStatus, notes })
    });
    if (!res.ok) throw new Error('Status update failed');
    closeOrderDetailModal();
    loadStats();
    loadOrders();
  } catch (e) {
    alert('Error updating status: ' + e.message);
  }
};

window.sendCourierWhatsApp = function(orderId) {
  const order = currentOrders.find(o => o.id === orderId);
  if (!order) return;
  const mobile = normMobile(order.patient_mobile);
  if (!mobile || mobile.length !== 10) {
    alert('Invalid patient phone number');
    return;
  }

  const pdfUrl = order.pdf_url || `${window.location.origin}/verify.html?id=${encodeURIComponent(order.rx_number)}`;
  const message = `Hello ${order.patient_name},\n\nYour prescribed medicines from ${order.doctor_name} at ${order.clinic_name} are verified and packed by Pharma Bridge.\n\n📦 Order Status: OUT FOR DELIVERY\n📄 View Prescription: ${pdfUrl}\n\nOur delivery associate is en route to your address. For support, reply to this message!\n\n— Pharma Bridge Fulfillment Hub`;

  window.open(`https://wa.me/91${mobile}?text=${encodeURIComponent(message)}`, '_blank');
};

// ═══════════════ TAB 2: CHRONIC 30-DAY REFILL PREDICTOR ═══════════════
async function loadRefills() {
  const tbody = document.getElementById('distRefillsTableBody');
  try {
    const res = await fetch(`${API_BASE}/distributor/refills`, { headers: distHeaders() });
    if (!res.ok) throw new Error('Failed to fetch refills');
    const refills = await res.json();
    renderRefills(refills);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#ef4444;">${err.message}</td></tr>`;
  }
}

function renderRefills(refills) {
  const tbody = document.getElementById('distRefillsTableBody');
  if (!refills || refills.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8;">No chronic refill candidates detected in active cycle.</td></tr>`;
    return;
  }

  tbody.innerHTML = refills.map(r => {
    const urgencyColor = r.days_until_refill <= 3 ? '#ef4444' : (r.days_until_refill <= 7 ? '#f59e0b' : '#0d9488');
    return `
      <tr>
        <td><strong>${esc(r.patient_name)}</strong></td>
        <td>+91 ${esc(r.patient_mobile)}</td>
        <td>${esc(r.doctor_name)}<div style="font-size:11px;color:#64748b;">${esc(r.clinic_name)}</div></td>
        <td><span style="font-size:12px;">${esc(r.chronic_medicines.join(', '))}</span></td>
        <td><strong style="color:${urgencyColor};">${r.days_until_refill <= 0 ? 'Due Today' : `In ${r.days_until_refill} days`}</strong><div style="font-size:11px;color:#64748b;">Target: ${r.estimated_refill_date}</div></td>
        <td><span class="status-pill" style="background:#fef3c7;color:#b45309;">${esc(r.urgency)}</span></td>
        <td>
          <button class="btn-action btn-wa" onclick="sendRefillWhatsApp('${esc(r.patient_name)}', '${esc(r.patient_mobile)}', '${esc(r.doctor_name)}', '${esc(r.chronic_medicines.join(', '))}', '${esc(r.estimated_refill_date)}')">📲 Send WhatsApp Refill</button>
        </td>
      </tr>
    `;
  }).join('');
}

window.sendRefillWhatsApp = function(name, mobile, doctor, meds, targetDate) {
  const cleanMobile = normMobile(mobile);
  const msg = `Hello ${name},\n\nYour 30-day maintenance medicine supply (${meds}) prescribed by ${doctor} is due for refill on ${targetDate}.\n\nPharma Bridge can deliver your genuine refill directly to your doorstep today at partner discounted prices.\n\nReply 'YES' to confirm dispatch!\n\n— Pharma Bridge Care Team`;
  window.open(`https://wa.me/91${cleanMobile}?text=${encodeURIComponent(msg)}`, '_blank');
};

// ═══════════════ TAB 3: DOCTOR COMMISSIONS ═══════════════
async function loadCommissions() {
  const tbody = document.getElementById('distCommissionsTableBody');
  try {
    const res = await fetch(`${API_BASE}/distributor/commissions`, { headers: distHeaders() });
    if (!res.ok) throw new Error('Failed to load commissions');
    const data = await res.json();
    renderCommissions(data);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#ef4444;">${err.message}</td></tr>`;
  }
}

function renderCommissions(list) {
  const tbody = document.getElementById('distCommissionsTableBody');
  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#94a3b8;">No doctor commission activity recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(d => `
    <tr>
      <td><strong>${esc(d.doctor_name)}</strong></td>
      <td>${esc(d.clinic_name)}</td>
      <td><span style="font-size:12px;color:#64748b;">${esc(d.doctor_email)}</span></td>
      <td><strong>${d.orders_count}</strong></td>
      <td>${d.medicines_dispensed}</td>
      <td><strong>₹${d.total_order_value.toLocaleString('en-IN')}</strong></td>
      <td><span style="color:#0d9488;font-weight:700;">${d.commission_rate}%</span></td>
      <td><strong style="color:#7c3aed;font-size:14px;">₹${d.commission_payable.toLocaleString('en-IN')}</strong></td>
    </tr>
  `).join('');
}

// ═══════════════ TAB SWITCHING ═══════════════
window.switchDistTab = function(tabName) {
  document.querySelectorAll('.dist-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');

  document.getElementById('tabOrders').style.display = tabName === 'orders' ? 'block' : 'none';
  document.getElementById('tabRefills').style.display = tabName === 'refills' ? 'block' : 'none';
  document.getElementById('tabCommissions').style.display = tabName === 'commissions' ? 'block' : 'none';

  if (tabName === 'refills') loadRefills();
  if (tabName === 'commissions') loadCommissions();
};

function esc(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, s => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[s]));
}

function normMobile(val) {
  return String(val || '').replace(/\D/g, '').slice(-10);
}
