import { API_BASE } from './constants';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function uploadVideo(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function getJobStatus(jobId) {
  return request(`/jobs/${jobId}/status`);
}

export async function getAnalytics(jobId) {
  return request(`/jobs/${jobId}/analytics`);
}

export async function getEvents(jobId) {
  return request(`/jobs/${jobId}/events`);
}

export async function getZones() {
  return request('/zones');
}

export async function createZone(zone) {
  return request('/zones', {
    method: 'POST',
    body: JSON.stringify(zone),
  });
}

export async function deleteZone(zoneId) {
  return request(`/zones/${zoneId}`, { method: 'DELETE' });
}

export async function updateSettings(settings) {
  return request('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

export async function getHealth() {
  return request('/health');
}

export async function getDemoAnalytics() {
  return request('/demo/analytics');
}

export async function getDemoEvents() {
  return request('/demo/events');
}

export function getStreamUrl(jobId) {
  return `${API_BASE}/jobs/${jobId}/stream`;
}

export function getDemoStreamUrl() {
  return `${API_BASE}/demo/stream`;
}

export function getWebSocketUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/live`;
}
