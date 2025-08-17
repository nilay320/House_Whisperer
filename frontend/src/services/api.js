// Minimal API helper for the frontend PWA

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiGet = async (path) => {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
};

export const apiPost = async (path, body) => {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
};

export const fetchReportSections = async () => {
  const data = await apiGet('/api/report_sections');
  return (data.sections || []).map(s => ({ key: s.key, label: s.label, includes: s.includes || [] }));
};

export const getApiBase = () => API_BASE;


