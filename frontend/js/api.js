// RxBridge API Client

const API_BASE = (window.location.hostname === 'localhost' && window.location.port !== '8000')
  ? 'http://localhost:8000/api/v1'
  : '/api/v1';

const TOKEN_KEY = 'rxbridge_token';
const USER_KEY = 'rxbridge_user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getStoredUser() {
  const u = localStorage.getItem(USER_KEY);
  return u ? JSON.parse(u) : null;
}

export function setStoredUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredUser() {
  localStorage.removeItem(USER_KEY);
}

export async function fetchWithAuth(endpoint, options = {}) {
  const token = getToken();
  const headers = options.headers || {};
  
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Only set application/json if body is not FormData
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !endpoint.includes('/auth/login')) {
    clearToken();
    clearStoredUser();
    throw new Error('Session expired. Please log in again.');
  }

  if (!res.ok) {
    let errMessage = 'Request failed';
    const text = await res.text();
    try {
      const errData = JSON.parse(text);
      errMessage = errData.detail || errData.message || (typeof errData === 'string' ? errData : JSON.stringify(errData));
    } catch {
      errMessage = text || res.statusText || 'Request failed';
    }
    throw new Error(errMessage);
  }

  return res.json();
}

// Authentication
export async function apiLogin(email, password) {
  const data = await fetchWithAuth('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function apiLogout() {
  try {
    await fetchWithAuth('/auth/logout', { method: 'POST' });
  } catch (e) {
    console.warn('Logout notification error:', e);
  } finally {
    clearToken();
    clearStoredUser();
  }
}

export async function apiGetMe() {
  return fetchWithAuth('/auth/me');
}

export async function apiUpdateSettings(settingsData) {
  return fetchWithAuth('/auth/settings', {
    method: 'PUT',
    body: JSON.stringify(settingsData),
  });
}

// Prescriptions
export async function apiCreateIntake(data) {
  return fetchWithAuth('/prescriptions/intake', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function apiGetWaitingQueue() {
  return fetchWithAuth('/prescriptions/waiting');
}

export async function apiCompletePrescription(id, data) {
  return fetchWithAuth(`/prescriptions/${id}/complete`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function apiCreateDirectPrescription(data) {
  return fetchWithAuth('/prescriptions/direct', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function apiGetHistory(search = '') {
  const q = search ? `?search=${encodeURIComponent(search)}` : '';
  return fetchWithAuth(`/prescriptions/history${q}`);
}

export async function apiGetPrescription(id) {
  return fetchWithAuth(`/prescriptions/${id}`);
}

export async function apiDeletePrescription(id) {
  return fetchWithAuth(`/prescriptions/${id}`, {
    method: 'DELETE',
  });
}

// Patients
export async function apiGetPatient(mobile) {
  return fetchWithAuth(`/patients/${encodeURIComponent(mobile)}`);
}

export async function apiGetPatientTimeline(mobile) {
  return fetchWithAuth(`/patients/${encodeURIComponent(mobile)}/timeline`);
}

// Medicines
export async function apiAutocompleteMedicines(query, limit = 8) {
  return fetchWithAuth(`/medicines/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function apiAddCustomMedicine(data) {
  return fetchWithAuth('/medicines/custom', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Pharmacy
export async function apiGetPharmacyPrescriptions(search = '') {
  const q = search ? `?search=${encodeURIComponent(search)}` : '';
  return fetchWithAuth(`/pharmacy/prescriptions${q}`);
}

export async function apiDispensePrescription(id) {
  return fetchWithAuth(`/pharmacy/prescriptions/${id}/dispense`, {
    method: 'POST',
  });
}

// Uploads
export async function apiUploadLabReport(mobile, file) {
  const formData = new FormData();
  formData.append('mobile', mobile);
  formData.append('file', file);
  return fetchWithAuth('/uploads/lab-report', {
    method: 'POST',
    body: formData,
  });
}

// Dashboard
export async function apiGetDashboardStats() {
  return fetchWithAuth('/dashboard/stats');
}

// AI Assistant
export async function apiChatAgent(message, history = []) {
  return fetchWithAuth('/agent/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });
}
