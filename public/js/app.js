// RxBridge Frontend Application Controller
import {
  apiLogin,
  apiLogout,
  apiGetMe,
  apiUpdateSettings,
  apiCreateIntake,
  apiGetWaitingQueue,
  apiCompletePrescription,
  apiCreateDirectPrescription,
  apiGetHistory,
  apiGetPrescription,
  apiDeletePrescription,
  apiGetPatient,
  apiGetPatientTimeline,
  apiAutocompleteMedicines,
  apiAddCustomMedicine,
  apiGetPharmacyPrescriptions,
  apiDispensePrescription,
  apiUploadLabReport,
  apiGetDashboardStats,
  apiChatAgent,
  getToken,
  getStoredUser,
  clearToken,
  clearStoredUser
} from './api.js';

// Application State
let currentUser = null;
let currentRole = 'doctor';
let doctorSettings = {};
let editingRxId = null;
let medicines = [];
let pendingSignatureData = null;
let returningPatientData = null;
let currentViewRx = null;
let cachedHistory = [];
let cachedPharmacy = [];
let cachedWaiting = [];

// Autocomplete State
let activeSuggestionBox = null;
let selectedSuggestionIndex = -1;
let currentSuggestions = [];

// Security timers
let failedLoginAttempts = 0;
let lockoutEndTime = null;
let inactivityTimer = null;
let inactivityWarningTimer = null;

// Utility: HTML Escaping
function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function normMobile(raw) {
  if (!raw) return '';
  const digits = String(raw).replace(/\D/g, '');
  return digits.length >= 10 ? digits.slice(-10) : digits;
}

function isValidMobile(raw) {
  const m = normMobile(raw);
  return /^[6-9]\d{9}$/.test(m);
}

function patientInitials(name) {
  if (!name) return '—';
  return name.trim().split(/\s+/).map(p => p[0].toUpperCase() + '.').join(' ');
}

// Quick Demo Login Helper
window.fillDemo = function(email, pass) {
  document.getElementById('loginEmail').value = email;
  document.getElementById('loginPass').value = pass;
  window.doLogin();
};

// Screen Navigation
window.showScreen = function(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(screenId);
  if (target) target.classList.add('active');
};

window.showDash = function() {
  window.showScreen('dashScreen');
};

// Tab Switching
window.switchTab = function(tabName) {
  // Update button active states for current role tabs
  const container = currentRole === 'staff' 
    ? document.getElementById('staffTabs') 
    : (currentRole === 'pharmacy' ? document.getElementById('pharmacyTabs') : document.getElementById('doctorTabs'));
  
  if (container) {
    container.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  }

  // Hide all panels
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  // Show target panel
  const targetPanel = document.getElementById(tabName + 'Tab');
  if (targetPanel) targetPanel.classList.add('active');

  // Load specific tab data
  if (tabName === 'waiting') loadWaitingPatients();
  if (tabName === 'history') loadPrescriptions();
  if (tabName === 'pharmacy') loadPharmacyPrescriptions();
  if (tabName === 'dashboard') updateDashboardStats();
  if (tabName === 'settings') fillDoctorSettingsForm();
};

// Role UI Adjustment
function applyRoleUI(role) {
  currentRole = role;
  const roleBadge = document.getElementById('roleBadge');
  const doctorEmail = document.getElementById('doctorEmail');
  const doctorTabs = document.getElementById('doctorTabs');
  const staffTabs = document.getElementById('staffTabs');
  const pharmacyTabs = document.getElementById('pharmacyTabs');
  const doctorOnlyFields = document.getElementById('doctorOnlyFields');
  const staffBanner = document.getElementById('staffBanner');
  const saveBtnLabel = document.getElementById('saveBtnLabel');

  if (roleBadge) {
    roleBadge.textContent = role.toUpperCase();
    roleBadge.className = 'role-badge ' + (role === 'staff' ? 'staff' : (role === 'pharmacy' ? 'pharmacy' : ''));
  }

  if (doctorEmail) {
    doctorEmail.textContent = currentUser?.email || '—';
  }

  // Toggle Tab bars
  if (doctorTabs) doctorTabs.style.display = role === 'doctor' ? 'flex' : 'none';
  if (staffTabs) staffTabs.style.display = role === 'staff' ? 'flex' : 'none';
  if (pharmacyTabs) pharmacyTabs.style.display = role === 'pharmacy' ? 'flex' : 'none';

  // Role specifics
  if (role === 'staff') {
    if (doctorOnlyFields) doctorOnlyFields.style.display = 'none';
    if (staffBanner) staffBanner.style.display = 'block';
    if (saveBtnLabel) saveBtnLabel.textContent = 'Send to Doctor';
    window.switchTab('write');
  } else if (role === 'pharmacy') {
    window.switchTab('pharmacy');
  } else {
    // Doctor
    if (doctorOnlyFields) doctorOnlyFields.style.display = 'block';
    if (staffBanner) staffBanner.style.display = 'none';
    if (saveBtnLabel) saveBtnLabel.textContent = editingRxId ? 'Update & Finalize Rx' : 'Save Prescription';
    window.switchTab('waiting');
  }
}

// Inactivity & Lockout
function resetInactivityTimer() {
  clearTimeout(inactivityTimer);
  clearTimeout(inactivityWarningTimer);

  inactivityWarningTimer = setTimeout(() => {
    alert('You will be logged out in 5 minutes due to inactivity.');
  }, 25 * 60 * 1000);

  inactivityTimer = setTimeout(() => {
    alert('Logged out due to inactivity.');
    window.doLogout();
  }, 30 * 60 * 1000);
}

// Login
window.doLogin = async function() {
  const email = document.getElementById('loginEmail').value.trim();
  const pass = document.getElementById('loginPass').value;
  const btn = document.getElementById('loginBtn');
  const err = document.getElementById('loginError');

  if (lockoutEndTime && Date.now() < lockoutEndTime) {
    const mins = Math.ceil((lockoutEndTime - Date.now()) / 60000);
    err.textContent = `Too many failed attempts. Locked for ${mins} minute(s).`;
    err.style.display = 'block';
    return;
  }

  if (!email || !pass) {
    err.textContent = 'Please enter both email and password.';
    err.style.display = 'block';
    return;
  }

  err.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="login-spinner"></span> Signing in...';

  try {
    const res = await apiLogin(email, pass);
    failedLoginAttempts = 0;
    currentUser = res.user;
    currentRole = res.user.role;
    doctorSettings = {
      doctorName: res.user.doctor_name || '',
      regNo: res.user.reg_no || '',
      qualification: res.user.qualification || '',
      clinicName: res.user.clinic_name || '',
      clinicAddress: res.user.clinic_address || '',
      clinicPhone: res.user.clinic_phone || '',
      signatureData: res.user.signature_data || '',
    };

    resetInactivityTimer();
    applyRoleUI(currentRole);
    window.showScreen('dashScreen');
  } catch (e) {
    const isAuthErr = e.status === 401 || (e.message && e.message.toLowerCase().includes('credential')) || (e.message && e.message.toLowerCase().includes('incorrect'));
    if (isAuthErr) {
      failedLoginAttempts++;
      if (failedLoginAttempts >= 3) {
        lockoutEndTime = Date.now() + 15 * 60 * 1000;
        err.textContent = 'Too many failed attempts. Account locked for 15 minutes.';
      } else {
        err.textContent = e.message || 'Login failed. Please check credentials.';
      }
    } else {
      err.textContent = e.message || 'Connection error. Please try again.';
    }
    err.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
};

// Logout
window.doLogout = async function() {
  try {
    await apiLogout();
  } catch (e) {
    console.error(e);
  }
  clearTimeout(inactivityTimer);
  clearTimeout(inactivityWarningTimer);
  currentUser = null;
  editingRxId = null;
  medicines = [];
  window.showScreen('loginScreen');
};

// Vitals & BMI
window.updateBmi = function() {
  const w = parseFloat(document.getElementById('ptWeight')?.value);
  const h = parseFloat(document.getElementById('ptHeight')?.value);
  const el = document.getElementById('ptBmi');
  if (!el) return;

  if (w > 0 && h > 0) {
    const heightInMeters = h / 100;
    const bmi = (w / (heightInMeters * heightInMeters)).toFixed(1);
    el.textContent = bmi;
    el.setAttribute('data-value', bmi);
  } else {
    el.textContent = '—';
    el.removeAttribute('data-value');
  }
};

window.markConsentTouched = function() {
  const note = document.getElementById('consentNote');
  if (!note) return;
  const off = document.getElementById('consentOffers')?.checked;
  const ref = document.getElementById('consentRefill')?.checked;
  if (off || ref) {
    note.textContent = `Consent recorded by ${currentUser?.email || 'staff'} just now.`;
    note.style.display = 'block';
  } else {
    note.textContent = '';
    note.style.display = 'none';
  }
};

// Returning Patient Lookup
window.lookupReturningPatient = async function() {
  const rawMobile = document.getElementById('ptMobile')?.value;
  const mobile = normMobile(rawMobile);
  const banner = document.getElementById('returningPatientBanner');
  if (!mobile || mobile.length < 10) {
    if (banner) banner.style.display = 'none';
    return;
  }

  try {
    const res = await apiGetPatient(mobile);
    if (res.found) {
      returningPatientData = res;
      if (banner) {
        banner.innerHTML = `👋 Returning patient found: <strong>${esc(res.name)}</strong> (${esc(res.ageGender)}). <button type="button" onclick="fillReturningPatient()" style="margin-left:8px;background:#0d9488;color:#fff;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:12px;">Auto-fill</button>`;
        banner.style.display = 'block';
      }
      renderLabReports(res.reports || []);
    } else {
      returningPatientData = null;
      if (banner) banner.style.display = 'none';
      renderLabReports(res.reports || []);
    }
  } catch (e) {
    console.warn('Patient lookup failed:', e);
  }
};

window.fillReturningPatient = function() {
  if (!returningPatientData) return;
  document.getElementById('ptName').value = returningPatientData.name || '';
  document.getElementById('ptAge').value = returningPatientData.ageGender || '';
  if (returningPatientData.weight) document.getElementById('ptWeight').value = returningPatientData.weight;
  if (returningPatientData.height) document.getElementById('ptHeight').value = returningPatientData.height;
  if (document.getElementById('consentOffers')) document.getElementById('consentOffers').checked = !!returningPatientData.consentOffers;
  if (document.getElementById('consentRefill')) document.getElementById('consentRefill').checked = !!returningPatientData.consentRefill;
  window.updateBmi();
  window.markConsentTouched();
};

// Lab Reports
function renderLabReports(reports) {
  const list = document.getElementById('labReportsList');
  if (!list) return;
  if (!reports || reports.length === 0) {
    list.innerHTML = '<div style="font-size:12px;color:#94a3b8;">No lab reports on file.</div>';
    return;
  }
  list.innerHTML = reports.map(r => `
    <div style="border:1px solid #cbd5e1;border-radius:8px;padding:6px;width:110px;text-align:center;background:#fff;">
      <a href="${esc(r.url)}" target="_blank" title="View Full Report">
        <img src="${esc(r.url)}" style="width:100%;height:75px;object-fit:cover;border-radius:4px;" alt="Report Thumbnail">
      </a>
      <div style="font-size:10px;color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:4px;">${esc(r.fileName)}</div>
    </div>
  `).join('');
}

window.uploadLabReport = async function() {
  const fileInput = document.getElementById('labReportInput');
  const mobileInput = document.getElementById('ptMobile');
  const statusEl = document.getElementById('labUploadStatus');
  const mobile = normMobile(mobileInput?.value);

  if (!mobile || !isValidMobile(mobile)) {
    alert('Please enter a valid 10-digit Indian patient mobile number (starting with 6, 7, 8, or 9) first.');
    return;
  }
  if (!fileInput?.files?.[0]) {
    alert('Please select a JPG/PNG lab report file to upload.');
    return;
  }

  const file = fileInput.files[0];
  if (file.size > 10 * 1024 * 1024) {
    alert('File size exceeds 10 MB limit.');
    return;
  }

  statusEl.textContent = '⏳ Uploading report...';
  statusEl.style.color = '#0d9488';

  try {
    const res = await apiUploadLabReport(mobile, file);
    statusEl.textContent = '✅ Lab report uploaded successfully!';
    statusEl.style.color = '#15803d';
    fileInput.value = '';
    // Refresh lab reports
    window.lookupReturningPatient();
  } catch (e) {
    statusEl.textContent = '❌ Upload failed: ' + e.message;
    statusEl.style.color = '#ef4444';
  }
};

// Medicines Form Handling
window.initMedicines = function() {
  medicines = [{ name: '', dose: '', duration: '', frequency: '', foodRelation: '', timing: [] }];
  window.renderMedicines();
};

window.addMedicine = function() {
  medicines.push({ name: '', dose: '', duration: '', frequency: '', foodRelation: '', timing: [] });
  window.renderMedicines();
};

window.removeMed = function(idx) {
  if (medicines.length <= 1) {
    medicines = [{ name: '', dose: '', duration: '', frequency: '', foodRelation: '', timing: [] }];
  } else {
    medicines.splice(idx, 1);
  }
  window.renderMedicines();
};

window.updateMed = function(idx, field, val) {
  if (medicines[idx]) {
    medicines[idx][field] = val;
  }
};

window.toggleTiming = function(idx, slot) {
  if (!medicines[idx]) return;
  const timings = medicines[idx].timing || [];
  const pos = timings.indexOf(slot);
  if (pos === -1) timings.push(slot);
  else timings.splice(pos, 1);
  medicines[idx].timing = timings;
};

// Dose shorthand expander: '101' -> '1-0-1', '111' -> '1-1-1'
window.handleDoseShorthand = function(e, idx) {
  if (e.key === ' ' || e.key === 'Tab') {
    const val = e.target.value.trim();
    if (/^[01]{3,4}$/.test(val)) {
      e.preventDefault();
      const expanded = val.split('').join('-');
      e.target.value = expanded;
      window.updateMed(idx, 'dose', expanded);
    }
  }
};

window.renderMedicines = function() {
  const container = document.getElementById('medicineList');
  if (!container) return;

  container.innerHTML = medicines.map((m, idx) => `
    <div class="med-row" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px;margin-bottom:10px;">
      <div style="display:grid;grid-template-columns:1fr 110px 100px 32px;gap:8px;align-items:center;">
        <div style="position:relative;">
          <input type="text" placeholder="Medicine name" value="${esc(m.name)}"
            oninput="handleMedInput(event, ${idx})"
            onkeydown="handleMedKeydown(event, ${idx})"
            style="width:100%;padding:8px;border:1.5px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:'Inter',sans-serif;">
          <div class="med-suggestions" id="sug_${idx}" style="display:none;position:absolute;top:100%;left:0;right:0;background:#fff;border:1px solid #cbd5e1;border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.1);z-index:20;max-height:180px;overflow-y:auto;"></div>
        </div>
        <input type="text" placeholder="Dose (101)" value="${esc(m.dose)}"
          onkeydown="handleDoseShorthand(event, ${idx})"
          oninput="updateMed(${idx}, 'dose', this.value)"
          style="width:100%;padding:8px;border:1.5px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:'Inter',sans-serif;">
        <input type="text" placeholder="Duration" value="${esc(m.duration)}"
          oninput="updateMed(${idx}, 'duration', this.value)"
          style="width:100%;padding:8px;border:1.5px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:'Inter',sans-serif;">
        <button type="button" onclick="removeMed(${idx})" style="background:#fee2e2;color:#ef4444;border:none;border-radius:6px;height:34px;width:32px;cursor:pointer;font-weight:700;">×</button>
      </div>

      <div style="display:flex;gap:12px;margin-top:8px;align-items:center;flex-wrap:wrap;font-size:12px;">
        <select onchange="updateMed(${idx}, 'frequency', this.value)" style="padding:6px 8px;border:1px solid #cbd5e1;border-radius:6px;">
          <option value="">Frequency</option>
          <option value="OD" ${m.frequency==='OD'?'selected':''}>OD – Once daily</option>
          <option value="BD" ${m.frequency==='BD'?'selected':''}>BD – Twice daily</option>
          <option value="TDS" ${m.frequency==='TDS'?'selected':''}>TDS – Thrice daily</option>
          <option value="QID" ${m.frequency==='QID'?'selected':''}>QID – 4x daily</option>
          <option value="SOS" ${m.frequency==='SOS'?'selected':''}>SOS – As needed</option>
          <option value="STAT" ${m.frequency==='STAT'?'selected':''}>STAT – Immediately</option>
          <option value="HS" ${m.frequency==='HS'?'selected':''}>HS – At bedtime</option>
        </select>

        <select onchange="updateMed(${idx}, 'foodRelation', this.value)" style="padding:6px 8px;border:1px solid #cbd5e1;border-radius:6px;">
          <option value="">Food relation</option>
          <option value="Before food" ${m.foodRelation==='Before food'?'selected':''}>Before food</option>
          <option value="After food" ${m.foodRelation==='After food'?'selected':''}>After food</option>
          <option value="Empty stomach" ${m.foodRelation==='Empty stomach'?'selected':''}>Empty stomach</option>
        </select>

        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <input type="checkbox" ${(m.timing||[]).includes('morning')?'checked':''} onchange="toggleTiming(${idx}, 'morning')"> Morn
        </label>
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <input type="checkbox" ${(m.timing||[]).includes('afternoon')?'checked':''} onchange="toggleTiming(${idx}, 'afternoon')"> Aft
        </label>
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
          <input type="checkbox" ${(m.timing||[]).includes('evening')?'checked':''} onchange="toggleTiming(${idx}, 'evening')"> Eve
        </label>
      </div>
    </div>
  `).join('');
};

// Autocomplete Logic
window.handleMedInput = async function(e, idx) {
  const q = e.target.value.trim();
  window.updateMed(idx, 'name', e.target.value);
  const box = document.getElementById(`sug_${idx}`);
  if (!box) return;

  if (q.length < 2) {
    box.style.display = 'none';
    return;
  }

  try {
    const list = await apiAutocompleteMedicines(q);
    currentSuggestions = list;
    if (list.length === 0) {
      box.style.display = 'none';
      return;
    }
    box.innerHTML = list.map((item, sIdx) => `
      <div style="padding:8px 12px;font-size:12px;cursor:pointer;border-bottom:1px solid #f1f5f9;"
        onmousedown="selectSuggestion(${idx}, ${sIdx})">
        <strong>${esc(item.name)}</strong>
        <span style="color:#64748b;margin-left:6px;">${esc(item.dose || '')} ${esc(item.duration || '')}</span>
      </div>
    `).join('');
    box.style.display = 'block';
  } catch (err) {
    console.warn('Autocomplete error:', err);
  }
};

window.selectSuggestion = function(medIdx, sugIdx) {
  const chosen = currentSuggestions[sugIdx];
  if (!chosen || !medicines[medIdx]) return;
  medicines[medIdx].name = chosen.name;
  if (chosen.dose) medicines[medIdx].dose = chosen.dose;
  if (chosen.duration) medicines[medIdx].duration = chosen.duration;
  window.renderMedicines();
};

window.handleMedKeydown = function(e, idx) {
  // Hide suggestions on Enter / Esc
  if (e.key === 'Escape' || e.key === 'Enter') {
    const box = document.getElementById(`sug_${idx}`);
    if (box) box.style.display = 'none';
  }
};

// Waiting Queue
async function loadWaitingPatients() {
  const listEl = document.getElementById('waitingList');
  const countBadge = document.getElementById('waitingCount');
  if (!listEl) return;
  listEl.innerHTML = '<div class="loading">Loading waiting patients...</div>';

  try {
    const items = await apiGetWaitingQueue();
    cachedWaiting = items;
    if (countBadge) {
      countBadge.textContent = items.length;
      countBadge.style.display = items.length > 0 ? 'inline-block' : 'none';
    }

    if (items.length === 0) {
      listEl.innerHTML = '<div class="empty-state">No patients waiting in queue.</div>';
      return;
    }

    listEl.innerHTML = items.map(p => `
      <div class="rx-item" onclick="openWaitingIntake(${p.id})">
        <div class="rx-item-header">
          <div class="rx-patient-name">${esc(p.patient_name)} (${esc(p.patient_age_gender)})</div>
          <span class="badge wait">WAITING</span>
        </div>
        <div class="rx-meta">
          <span>📱 ${esc(p.patient_mobile)}</span>
          <span>⚖️ ${p.patient_weight ? p.patient_weight + ' kg' : '—'}</span>
          <span>🩺 BP: ${p.bp_sys ? p.bp_sys + '/' + p.bp_dia : '—'}</span>
          <span>Entered by: ${esc(p.created_by_email || 'Staff')}</span>
        </div>
        ${p.diagnosis ? `<div style="font-size:12px;color:#475569;margin-top:4px;">Complaint: ${esc(p.diagnosis)}</div>` : ''}
      </div>
    `).join('');
  } catch (e) {
    listEl.innerHTML = '<div class="error-msg" style="display:block;">Failed to load waiting list.</div>';
  }
}

window.openWaitingIntake = async function(id) {
  try {
    const rx = await apiGetPrescription(id);
    editingRxId = rx.id;
    
    // Fill Write Rx fields
    document.getElementById('ptName').value = rx.patient_name || '';
    document.getElementById('ptAge').value = rx.patient_age_gender || '';
    document.getElementById('ptMobile').value = rx.patient_mobile || '';
    document.getElementById('ptWeight').value = rx.patient_weight || '';
    document.getElementById('ptDiag').value = rx.diagnosis || '';
    document.getElementById('ptBpSys').value = rx.bp_sys || '';
    document.getElementById('ptBpDia').value = rx.bp_dia || '';
    document.getElementById('ptPulse').value = rx.pulse || '';
    document.getElementById('ptTemp').value = rx.temperature || '';
    document.getElementById('ptSpo2').value = rx.spo2 || '';
    document.getElementById('ptRr').value = rx.respiratory_rate || '';
    document.getElementById('ptHeight').value = rx.height || '';
    document.getElementById('ptSugar').value = rx.blood_sugar || '';
    if (rx.sugar_type) document.getElementById('ptSugarType').value = rx.sugar_type;

    if (document.getElementById('consentOffers')) document.getElementById('consentOffers').checked = !!rx.consent_offers;
    if (document.getElementById('consentRefill')) document.getElementById('consentRefill').checked = !!rx.consent_refill;

    window.updateBmi();
    window.markConsentTouched();

    // Switch to Write Rx tab
    window.switchTab('write');
    const saveBtn = document.getElementById('saveBtnLabel');
    if (saveBtn) saveBtn.textContent = 'Save Prescription (Complete Intake)';
  } catch (e) {
    alert('Failed to load patient intake details: ' + e.message);
  }
};

// Save Prescription / Intake
window.savePrescription = async function() {
  const name = document.getElementById('ptName')?.value.trim();
  const age = document.getElementById('ptAge')?.value.trim();
  const rawMobile = document.getElementById('ptMobile')?.value.trim();
  const mobile = normMobile(rawMobile);
  const weight = parseFloat(document.getElementById('ptWeight')?.value) || null;
  const diag = document.getElementById('ptDiag')?.value.trim();

  // Vitals
  const bpSys = parseInt(document.getElementById('ptBpSys')?.value) || null;
  const bpDia = parseInt(document.getElementById('ptBpDia')?.value) || null;
  const pulse = parseInt(document.getElementById('ptPulse')?.value) || null;
  const temp = parseFloat(document.getElementById('ptTemp')?.value) || null;
  const spo2 = parseInt(document.getElementById('ptSpo2')?.value) || null;
  const rr = parseInt(document.getElementById('ptRr')?.value) || null;
  const height = parseFloat(document.getElementById('ptHeight')?.value) || null;
  const bmi = parseFloat(document.getElementById('ptBmi')?.getAttribute('data-value')) || null;
  const sugar = parseInt(document.getElementById('ptSugar')?.value) || null;
  const sugarType = document.getElementById('ptSugarType')?.value || 'Random';

  const consentOffers = !!document.getElementById('consentOffers')?.checked;
  const consentRefill = !!document.getElementById('consentRefill')?.checked;

  if (!name || name.length < 2) { alert('Patient name must be at least 2 characters long.'); return; }
  if (!age || age.length < 2) { alert('Patient age / gender is required (e.g. 35/M or 28/F).'); return; }
  if (!mobile || !isValidMobile(mobile)) {
    alert('A valid 10-digit Indian mobile number (starting with 6, 7, 8, or 9) is required.');
    return;
  }

  // Vitals Plausibility Checks (BRD FR-2.4)
  if (weight && (weight < 1 || weight > 350)) {
    alert('Weight must be between 1 kg and 350 kg.');
    return;
  }
  if (bpSys && (bpSys < 60 || bpSys > 260)) {
    alert('Systolic blood pressure must be between 60 and 260 mmHg.');
    return;
  }
  if (bpDia && (bpDia < 40 || bpDia > 160)) {
    alert('Diastolic blood pressure must be between 40 and 160 mmHg.');
    return;
  }
  if (bpSys && bpDia && bpSys <= bpDia) {
    alert('Systolic BP must be strictly greater than Diastolic BP.');
    return;
  }
  if (pulse && (pulse < 30 || pulse > 220)) {
    alert('Pulse rate must be between 30 and 220 bpm.');
    return;
  }
  if (temp && (temp < 90 || temp > 110)) {
    alert('Temperature must be between 90°F and 110°F.');
    return;
  }
  if (spo2 && (spo2 < 50 || spo2 > 100)) {
    alert('SpO2 must be between 50% and 100%.');
    return;
  }

  const saveBtn = document.getElementById('saveRxBtn');
  saveBtn.disabled = true;

  try {
    if (currentRole === 'staff') {
      // Staff Intake Submission (BRD FR-2.6)
      const intakePayload = {
        patient_name: name,
        patient_age_gender: age,
        patient_mobile: mobile,
        patient_weight: weight,
        diagnosis: diag,
        bp_sys: bpSys,
        bp_dia: bpDia,
        pulse,
        temperature: temp,
        spo2,
        respiratory_rate: rr,
        height,
        bmi,
        blood_sugar: sugar,
        sugar_type: sugarType,
        consent_offers: consentOffers,
        consent_refill: consentRefill,
      };

      await apiCreateIntake(intakePayload);
      alert('✅ Patient intake details submitted! Record sent to doctor queue.');
      resetWriteForm();
      window.switchTab('history');
    } else {
      // Doctor Completion (BRD FR-4.7)
      const validMeds = medicines.filter(m => m.name && m.name.trim().length > 0);
      if (!diag) {
        alert('Diagnosis / Complaint is required to issue a prescription.');
        saveBtn.disabled = false;
        return;
      }
      if (validMeds.length === 0) {
        alert('At least one medicine is required to complete the prescription.');
        saveBtn.disabled = false;
        return;
      }

      const advice = document.getElementById('ptAdvice')?.value.trim() || '';
      const followUp = document.getElementById('ptFollowup')?.value.trim() || '';

      let rxResult = null;
      if (editingRxId) {
        // Complete waiting intake
        rxResult = await apiCompletePrescription(editingRxId, {
          diagnosis: diag,
          medicines: validMeds,
          advice,
          follow_up_date: followUp
        });
      } else {
        // Direct doctor entry (BRD 5.2)
        rxResult = await apiCreateDirectPrescription({
          patient_name: name,
          patient_age_gender: age,
          patient_mobile: mobile,
          patient_weight: weight,
          diagnosis: diag,
          bp_sys: bpSys,
          bp_dia: bpDia,
          pulse,
          temperature: temp,
          spo2,
          respiratory_rate: rr,
          height,
          bmi,
          blood_sugar: sugar,
          sugar_type: sugarType,
          consent_offers: consentOffers,
          consent_refill: consentRefill,
          medicines: validMeds,
          advice,
          follow_up_date: followUp
        });
      }

      resetWriteForm();
      editingRxId = null;
      window.viewRx(rxResult);
    }
  } catch (err) {
    alert('Error saving prescription: ' + err.message);
  } finally {
    saveBtn.disabled = false;
  }
};

function resetWriteForm() {
  document.getElementById('ptName').value = '';
  document.getElementById('ptAge').value = '';
  document.getElementById('ptMobile').value = '';
  document.getElementById('ptWeight').value = '';
  document.getElementById('ptDiag').value = '';
  document.getElementById('ptBpSys').value = '';
  document.getElementById('ptBpDia').value = '';
  document.getElementById('ptPulse').value = '';
  document.getElementById('ptTemp').value = '';
  document.getElementById('ptSpo2').value = '';
  document.getElementById('ptRr').value = '';
  document.getElementById('ptHeight').value = '';
  document.getElementById('ptSugar').value = '';
  if (document.getElementById('ptAdvice')) document.getElementById('ptAdvice').value = '';
  if (document.getElementById('ptFollowup')) document.getElementById('ptFollowup').value = '';
  if (document.getElementById('consentOffers')) document.getElementById('consentOffers').checked = false;
  if (document.getElementById('consentRefill')) document.getElementById('consentRefill').checked = false;
  window.updateBmi();
  window.markConsentTouched();
  window.initMedicines();
}

// History List
async function loadPrescriptions() {
  const listEl = document.getElementById('historyList');
  const searchInput = document.getElementById('historySearchInput');
  const search = searchInput ? searchInput.value.trim() : '';

  if (!listEl) return;
  listEl.innerHTML = '<div class="loading">Loading prescriptions...</div>';

  try {
    const items = await apiGetHistory(search);
    cachedHistory = items;
    window.renderPrescriptionList();
  } catch (e) {
    listEl.innerHTML = '<div class="error-msg" style="display:block;">Failed to load prescription history.</div>';
  }
}

window.renderPrescriptionList = function() {
  const listEl = document.getElementById('historyList');
  if (!listEl) return;

  if (cachedHistory.length === 0) {
    listEl.innerHTML = '<div class="empty-state">No completed prescriptions found.</div>';
    return;
  }

  listEl.innerHTML = cachedHistory.map(p => `
    <div class="rx-item">
      <div class="rx-item-header">
        <div class="rx-patient-name">${esc(p.patient_name)} (${esc(p.patient_age_gender)})</div>
        <span class="badge ${p.status === 'dispensed' ? 'ok' : 'wait'}">${p.status.toUpperCase()}</span>
      </div>
      <div class="rx-meta">
        <span>📋 ${esc(p.rx_number)}</span>
        <span>📱 ${esc(p.patient_mobile)}</span>
        <span>💊 ${p.medicines_count} medicines</span>
        <span>Doctor: ${esc(p.doctor_email || '—')}</span>
      </div>
      <div style="margin-top:8px;display:flex;gap:8px;">
        <button type="button" class="btn-demo" onclick="openPrescriptionById(${p.id})">👁️ View Rx</button>
        ${currentRole === 'doctor' ? `<button type="button" class="btn-demo" style="background:#fee2e2;color:#ef4444;" onclick="deleteRx(${p.id})">🗑️ Delete</button>` : ''}
      </div>
    </div>
  `).join('');
};

window.openPrescriptionById = async function(id) {
  try {
    const rx = await apiGetPrescription(id);
    window.viewRx(rx);
  } catch (e) {
    alert('Failed to load prescription: ' + e.message);
  }
};

window.deleteRx = async function(id) {
  if (!confirm('Are you sure you want to permanently delete this prescription?')) return;
  try {
    await apiDeletePrescription(id);
    alert('Prescription deleted.');
    loadPrescriptions();
  } catch (e) {
    alert('Delete failed: ' + e.message);
  }
};

// Pharmacy View
async function loadPharmacyPrescriptions() {
  const listEl = document.getElementById('pharmacyList');
  const searchInput = document.getElementById('pharmacySearchInput');
  const search = searchInput ? searchInput.value.trim() : '';

  if (!listEl) return;
  listEl.innerHTML = '<div class="loading">Loading consented prescriptions...</div>';

  try {
    const items = await apiGetPharmacyPrescriptions(search);
    cachedPharmacy = items;
    window.renderPharmacyList();
  } catch (e) {
    listEl.innerHTML = '<div class="error-msg" style="display:block;">Failed to load pharmacy view.</div>';
  }
}

window.renderPharmacyList = function() {
  const listEl = document.getElementById('pharmacyList');
  if (!listEl) return;

  if (cachedPharmacy.length === 0) {
    listEl.innerHTML = '<div class="empty-state">No consented prescriptions available for pharmacy.</div>';
    return;
  }

  listEl.innerHTML = cachedPharmacy.map(p => `
    <div class="rx-item">
      <div class="rx-item-header">
        <div class="rx-patient-name">${esc(p.patient_name)} (${esc(p.patient_age_gender)})</div>
        <span class="badge ${p.status === 'dispensed' ? 'ok' : 'wait'}">${p.status.toUpperCase()}</span>
      </div>
      <div class="rx-meta">
        <span>📋 ${esc(p.rx_number)}</span>
        <span>📱 ${esc(p.patient_mobile)}</span>
        <span>💊 ${p.medicines_count} medicines</span>
      </div>
      <div style="margin-top:8px;display:flex;gap:8px;">
        <button type="button" class="btn-demo" onclick="openPrescriptionById(${p.id})">👁️ View & Print</button>
        ${p.status !== 'dispensed' ? `<button type="button" class="btn-demo" style="background:#15803d;color:#fff;" onclick="markDispensed(${p.id})">✅ Mark Dispensed</button>` : '<span style="font-size:12px;color:#15803d;font-weight:600;align-self:center;">Dispensed</span>'}
      </div>
    </div>
  `).join('');
};

window.markDispensed = async function(id) {
  try {
    await apiDispensePrescription(id);
    alert('Prescription marked as dispensed!');
    loadPharmacyPrescriptions();
  } catch (e) {
    alert('Failed to mark dispensed: ' + e.message);
  }
};

// Patient Profile & Timeline
window.loadPatientProfile = async function() {
  const input = document.getElementById('patientLookupInput');
  const container = document.getElementById('patientProfileContainer');
  const mobile = normMobile(input?.value);

  if (!mobile || !isValidMobile(mobile)) {
    alert('Please enter a valid 10-digit Indian mobile number (starting with 6, 7, 8, or 9).');
    return;
  }

  container.innerHTML = '<div class="loading">Loading patient history...</div>';

  try {
    const data = await apiGetPatientTimeline(mobile);
    if (!data.visits || data.visits.length === 0) {
      container.innerHTML = '<div class="empty-state">No previous visits found for this number.</div>';
      return;
    }

    container.innerHTML = `
      <div class="card" style="margin-bottom:16px;">
        <div class="section-title">Longitudinal Visits (${data.visits.length})</div>
        ${data.visits.map(v => `
          <div style="padding:12px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;font-weight:600;font-size:14px;color:#0d9488;">
              <span>🗓️ ${esc(v.date)}</span>
              <span>${esc(v.rxNumber)}</span>
            </div>
            <div style="font-size:12px;color:#475569;margin-top:4px;">Diagnosis: <strong>${esc(v.diagnosis || '—')}</strong></div>
            <div style="font-size:12px;color:#64748b;margin-top:2px;">Doctor: ${esc(v.doctorName)} · Vitals: BP ${esc(v.vitals.bp)}, Pulse ${v.vitals.pulse || '—'}</div>
            <div style="font-size:12px;margin-top:6px;background:#f8fafc;padding:6px;border-radius:4px;">
              Medicines: ${v.medicines.map(m => `<span>${esc(m.name)} (${esc(m.dose)})</span>`).join(', ') || 'None'}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (e) {
    container.innerHTML = '<div class="error-msg" style="display:block;">Failed to load profile.</div>';
  }
};

// Dashboard Stats
async function updateDashboardStats() {
  try {
    const stats = await apiGetDashboardStats();
    if (document.getElementById('statToday')) document.getElementById('statToday').textContent = stats.today;
    if (document.getElementById('statMonth')) document.getElementById('statMonth').textContent = stats.thisMonth;
    if (document.getElementById('statPatients')) document.getElementById('statPatients').textContent = stats.distinctPatients;
    
    const topMedsList = document.getElementById('topMedicinesList');
    if (topMedsList) {
      if (!stats.topMedicines || stats.topMedicines.length === 0) {
        topMedsList.innerHTML = '<div class="empty-state">No prescription data yet.</div>';
      } else {
        topMedsList.innerHTML = stats.topMedicines.map(m => `
          <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #e2e8f0;font-size:13px;">
            <span>${esc(m.name)}</span>
            <strong>${m.count} prescribed</strong>
          </div>
        `).join('');
      }
    }
  } catch (e) {
    console.warn('Dashboard stats error:', e);
  }
}

// Doctor Settings
function fillDoctorSettingsForm() {
  document.getElementById('settingDoctorName').value = doctorSettings.doctorName || '';
  document.getElementById('settingRegNo').value = doctorSettings.regNo || '';
  document.getElementById('settingQualification').value = doctorSettings.qualification || '';
  document.getElementById('settingClinicName').value = doctorSettings.clinicName || '';
  document.getElementById('settingClinicAddress').value = doctorSettings.clinicAddress || '';
  document.getElementById('settingClinicPhone').value = doctorSettings.clinicPhone || '';
  if (doctorSettings.signatureData) {
    const preview = document.getElementById('settingSignaturePreview');
    preview.src = doctorSettings.signatureData;
    preview.style.display = 'block';
  }
}

window.handleSignatureFile = function(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function(e) {
      pendingSignatureData = e.target.result;
      const preview = document.getElementById('settingSignaturePreview');
      preview.src = pendingSignatureData;
      preview.style.display = 'block';
    };
    reader.readAsDataURL(input.files[0]);
  }
};

window.clearSignature = function() {
  pendingSignatureData = '';
  const preview = document.getElementById('settingSignaturePreview');
  preview.src = '';
  preview.style.display = 'none';
  document.getElementById('settingSignatureFile').value = '';
};

window.saveDoctorSettings = async function() {
  const payload = {
    doctor_name: document.getElementById('settingDoctorName').value.trim(),
    reg_no: document.getElementById('settingRegNo').value.trim(),
    qualification: document.getElementById('settingQualification').value.trim(),
    clinic_name: document.getElementById('settingClinicName').value.trim(),
    clinic_address: document.getElementById('settingClinicAddress').value.trim(),
    clinic_phone: document.getElementById('settingClinicPhone').value.trim(),
  };
  if (pendingSignatureData !== null) {
    payload.signature_data = pendingSignatureData;
  }

  try {
    const updated = await apiUpdateSettings(payload);
    doctorSettings = {
      doctorName: updated.doctor_name,
      regNo: updated.reg_no,
      qualification: updated.qualification,
      clinicName: updated.clinic_name,
      clinicAddress: updated.clinic_address,
      clinicPhone: updated.clinic_phone,
      signatureData: updated.signature_data,
    };
    const toast = document.getElementById('settingsToast');
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
  } catch (e) {
    alert('Settings save failed: ' + e.message);
  }
};

// Printable Prescription View (A4 Sheet + QR Code)
window.viewRx = function(rx) {
  currentViewRx = rx;
  const printArea = document.getElementById('rxPrintArea');
  if (!printArea) return;

  const doc = rx.doctor_info || doctorSettings;
  const issuedDate = rx.completed_at ? new Date(rx.completed_at) : new Date();
  const dateFormatted = issuedDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
  const timeFormatted = issuedDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  // Generate QR Code data pointing to verify page
  let qrImgTag = '';
  try {
    const qr = qrcode(0, 'M');
    const verifyUrl = `${window.location.origin}/verify.html?id=${encodeURIComponent(rx.rx_number || rx.id)}`;
    qr.addData(verifyUrl);
    qr.make();
    qrImgTag = `<img src="${qr.createDataURL(4, 8)}" style="width:75px;height:75px;" alt="Verification QR">`;
  } catch (e) {
    console.warn('QR generation failed:', e);
  }

  printArea.innerHTML = `
    <div class="rx-sheet" id="prescriptionSheet" style="background:#fff;max-width:800px;margin:20px auto;padding:32px;border:1px solid #cbd5e1;box-shadow:0 4px 16px rgba(0,0,0,0.06);position:relative;font-family:'Inter',sans-serif;color:#1e293b;">
      <div style="display:flex;justify-content:space-between;border-bottom:2px solid #0d9488;padding-bottom:16px;">
        <div>
          <h2 style="margin:0;font-size:22px;color:#1a2744;font-family:'Playfair Display',serif;">${esc(doc.doctorName || 'Dr. Physician')}</h2>
          <div style="font-size:13px;color:#64748b;margin-top:4px;">${esc(doc.qualification || 'MBBS')} · Reg No: <strong>${esc(doc.regNo || '—')}</strong></div>
          <div style="font-size:13px;font-weight:600;color:#0d9488;margin-top:4px;">${esc(doc.clinicName || 'Clinic')}</div>
          <div style="font-size:12px;color:#64748b;">${esc(doc.clinicAddress || '')} · 📞 ${esc(doc.clinicPhone || '')}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:14px;font-weight:700;color:#0d9488;">${esc(rx.rx_number)}</div>
          <div style="font-size:12px;color:#64748b;margin-top:4px;">${dateFormatted} · ${timeFormatted}</div>
          <div style="margin-top:8px;">${qrImgTag}</div>
        </div>
      </div>

      <!-- Patient Header -->
      <div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;background:#f8fafc;padding:12px;border-radius:8px;margin:16px 0;font-size:13px;">
        <div><strong>Patient:</strong> ${esc(rx.patient_name)}</div>
        <div><strong>Age/Gender:</strong> ${esc(rx.patient_age_gender)}</div>
        <div><strong>Mobile:</strong> +91 ${esc(rx.patient_mobile)}</div>
      </div>

      <!-- Vitals Strip -->
      <div style="display:flex;gap:16px;background:#f1f5f9;padding:8px 12px;border-radius:6px;font-size:12px;margin-bottom:16px;flex-wrap:wrap;">
        <span><strong>BP:</strong> ${rx.bp_sys ? rx.bp_sys + '/' + rx.bp_dia + ' mmHg' : '—'}</span>
        <span><strong>Pulse:</strong> ${rx.pulse ? rx.pulse + ' bpm' : '—'}</span>
        <span><strong>Temp:</strong> ${rx.temperature ? rx.temperature + ' °F' : '—'}</span>
        <span><strong>SpO2:</strong> ${rx.spo2 ? rx.spo2 + '%' : '—'}</span>
        <span><strong>BMI:</strong> ${rx.bmi || '—'}</span>
      </div>

      <div style="font-size:13px;margin-bottom:16px;">
        <strong>Diagnosis / Complaint:</strong> ${esc(rx.diagnosis || '—')}
      </div>

      <!-- Rx Watermark & Medicines -->
      <div style="position:relative;min-height:220px;">
        <div style="position:absolute;top:20px;left:40%;font-size:140px;color:rgba(13,148,136,0.05);font-family:serif;font-weight:700;pointer-events:none;">℞</div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="border-bottom:1.5px solid #cbd5e1;text-align:left;color:#475569;">
              <th style="padding:8px 4px;">#</th>
              <th style="padding:8px 4px;">Medicine Name</th>
              <th style="padding:8px 4px;">Dosage</th>
              <th style="padding:8px 4px;">Frequency</th>
              <th style="padding:8px 4px;">Duration</th>
              <th style="padding:8px 4px;">Instructions</th>
            </tr>
          </thead>
          <tbody>
            ${(rx.medicines || []).map((m, i) => `
              <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:10px 4px;color:#94a3b8;">${i + 1}</td>
                <td style="padding:10px 4px;font-weight:600;color:#1e293b;">${esc(m.name)}</td>
                <td style="padding:10px 4px;">${esc(m.dose)}</td>
                <td style="padding:10px 4px;">${esc(m.frequency || '—')}</td>
                <td style="padding:10px 4px;">${esc(m.duration)}</td>
                <td style="padding:10px 4px;color:#64748b;">${esc(m.food_relation || m.foodRelation || '')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>

      <!-- Advice & Follow-up -->
      ${rx.advice ? `
        <div style="margin-top:16px;padding:12px;background:#f8fafc;border-radius:6px;font-size:12px;">
          <strong>Advice / Dietary Instructions:</strong>
          <div style="margin-top:4px;white-space:pre-wrap;">${esc(rx.advice)}</div>
        </div>
      ` : ''}

      ${rx.follow_up_date ? `
        <div style="margin-top:12px;font-size:12px;color:#0d9488;font-weight:600;">
          🗓️ Follow-up: ${esc(rx.follow_up_date)}
        </div>
      ` : ''}

      <!-- Signature Block -->
      <div style="display:flex;justify-content:flex-end;margin-top:32px;">
        <div style="text-align:center;min-width:160px;">
          ${doc.signatureData ? `<img src="${doc.signatureData}" style="max-height:60px;display:block;margin:0 auto 4px;" alt="Signature">` : '<div style="height:50px;"></div>'}
          <div style="border-top:1px solid #94a3b8;padding-top:4px;font-size:12px;font-weight:600;">${esc(doc.doctorName || 'Doctor Signature')}</div>
        </div>
      </div>
    </div>
  `;

  window.showScreen('viewScreen');
};

// PDF Download
window.downloadRxPdf = async function() {
  const sheet = document.getElementById('prescriptionSheet');
  if (!sheet) return;

  try {
    const canvas = await html2canvas(sheet, { scale: 2, useCORS: true });
    const imgData = canvas.toDataURL('image/jpeg', 0.95);
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF('p', 'mm', 'a4');
    const width = pdf.internal.pageSize.getWidth();
    const height = (canvas.height * width) / canvas.width;
    pdf.addImage(imgData, 'JPEG', 0, 0, width, height);
    pdf.save(`${currentViewRx?.rx_number || 'Prescription'}.pdf`);
  } catch (e) {
    alert('PDF generation error: ' + e.message);
  }
};

// WhatsApp Sharing
window.shareRxOnWhatsapp = async function() {
  if (!currentViewRx) return;
  const mobile = normMobile(currentViewRx.patient_mobile);
  const rxNum = currentViewRx.rx_number || 'Rx';
  const text = encodeURIComponent(`Hello ${currentViewRx.patient_name}, here is your digital prescription ${rxNum} from ${doctorSettings.clinicName || 'RxBridge'}. You can view or verify it online here: ${window.location.origin}/verify.html?id=${encodeURIComponent(rxNum)}`);
  window.open(`https://wa.me/91${mobile}?text=${text}`, '_blank');
};

// Initialize on Page Load
document.addEventListener('DOMContentLoaded', async () => {
  window.initMedicines();

  // Check existing session
  const token = getToken();
  if (token) {
    try {
      const me = await apiGetMe();
      currentUser = me;
      currentRole = me.role;
      doctorSettings = {
        doctorName: me.doctor_name || '',
        regNo: me.reg_no || '',
        qualification: me.qualification || '',
        clinicName: me.clinic_name || '',
        clinicAddress: me.clinic_address || '',
        clinicPhone: me.clinic_phone || '',
        signatureData: me.signature_data || '',
      };
      resetInactivityTimer();
      applyRoleUI(currentRole);
      window.showScreen('dashScreen');
    } catch {
      clearToken();
      clearStoredUser();
      window.showScreen('loginScreen');
    }
  } else {
    window.showScreen('loginScreen');
  }

  // Keybindings
  document.getElementById('loginPass')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      window.doLogin();
    }
  });

  document.getElementById('historySearchInput')?.addEventListener('input', () => {
    loadPrescriptions();
  });

  document.getElementById('pharmacySearchInput')?.addEventListener('input', () => {
    loadPharmacyPrescriptions();
  });
});

// ═══════════════ AI ASSISTANT WIDGET LOGIC ═══════════════
let agentChatHistory = [];

window.toggleAgentChat = function() {
  const panel = document.getElementById('agentChatPanel');
  if (!panel) return;
  const isHidden = panel.style.display === 'none' || !panel.style.display;
  panel.style.display = isHidden ? 'flex' : 'none';
  if (isHidden) {
    document.getElementById('agentInput')?.focus();
  }
};

window.sendAgentQuickPrompt = function(promptText) {
  const input = document.getElementById('agentInput');
  if (input) {
    input.value = promptText;
    window.sendAgentMessage();
  }
};

window.sendAgentMessage = async function() {
  const input = document.getElementById('agentInput');
  const container = document.getElementById('agentMessages');
  const sendBtn = document.getElementById('agentSendBtn');
  const msg = input?.value.trim();
  if (!msg) return;

  // Append user message bubble
  const userBubble = document.createElement('div');
  userBubble.style.cssText = 'align-self:flex-end;background:#0d9488;color:#fff;border-radius:12px;border-top-right-radius:2px;padding:9px 13px;font-size:13px;max-width:85%;line-height:1.4;word-break:break-word;';
  userBubble.textContent = msg;
  container.appendChild(userBubble);
  input.value = '';
  container.scrollTop = container.scrollHeight;

  // Append loading bubble
  const loadingBubble = document.createElement('div');
  loadingBubble.style.cssText = 'align-self:flex-start;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:9px 13px;font-size:12px;color:#64748b;';
  loadingBubble.textContent = 'Thinking... विचार करत आहे...';
  container.appendChild(loadingBubble);
  container.scrollTop = container.scrollHeight;
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await apiChatAgent(msg, agentChatHistory);
    loadingBubble.remove();

    const botBubble = document.createElement('div');
    botBubble.style.cssText = 'align-self:flex-start;background:#fff;border:1px solid #e2e8f0;border-radius:12px;border-top-left-radius:2px;padding:10px 14px;font-size:13px;max-width:88%;color:#1e293b;line-height:1.45;word-break:break-word;box-shadow:0 1px 3px rgba(0,0,0,0.04);white-space:pre-wrap;';
    botBubble.innerHTML = esc(res.reply).replace(/\n/g, '<br>');
    container.appendChild(botBubble);

    agentChatHistory.push({ role: 'user', content: msg });
    agentChatHistory.push({ role: 'assistant', content: res.reply });
    if (agentChatHistory.length > 10) agentChatHistory = agentChatHistory.slice(-10);
  } catch (err) {
    loadingBubble.remove();
    const errBubble = document.createElement('div');
    errBubble.style.cssText = 'align-self:flex-start;background:#fee2e2;color:#b91c1c;border-radius:12px;padding:9px 13px;font-size:12px;';
    errBubble.textContent = 'I am very sorry, a connection issue occurred. Please try again.';
    container.appendChild(errBubble);
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    container.scrollTop = container.scrollHeight;
  }
};
