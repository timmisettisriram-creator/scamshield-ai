// dashboard.js — ScamShield AI Dashboard

const API = '';

async function loadDashboard() {
  try {
    const [me, stats, scans] = await Promise.all([
      apiFetch('/auth/me'),
      apiFetch('/stats'),
      apiFetch('/scans/my')
    ]);
    if (me) {
      document.getElementById('user-name').textContent = me.name || me.email || 'User';
      document.getElementById('acc-name').value = me.name || '';
      document.getElementById('acc-email').value = me.email || '';
      document.getElementById('acc-phone').value = me.phone || '';
    }
    if (stats) {
      document.getElementById('safety-score').textContent = stats.safety_score ?? '—';
      document.getElementById('total-scans').textContent = stats.total_scans ?? '—';
      document.getElementById('scams-caught').textContent = stats.scams_caught ?? '—';
      document.getElementById('safe-count').textContent = stats.safe_count ?? '—';
      renderTrendChart(stats.trend || []);
    }
    if (scans) renderScansTable(scans);
  } catch (e) { console.error('Dashboard load error:', e); }
}

function renderScansTable(scans) {
  const tbody = document.getElementById('scans-tbody');
  if (!scans.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:30px">No scans yet. <a href="/#analyzer">Analyze something!</a></td></tr>';
    return;
  }
  tbody.innerHTML = scans.map(s => {
    const cls = s.verdict === 'SCAM' ? 'scam' : s.verdict === 'SUSPICIOUS' ? 'suspicious' : 'safe';
    const date = new Date(s.created_at).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
    const snippet = (s.input_text || '').slice(0, 50) + ((s.input_text || '').length > 50 ? '…' : '');
    return `<tr>
      <td>${date}</td>
      <td><span class="badge ${cls}">${s.verdict}</span></td>
      <td>${s.risk_score ?? '—'}/100</td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${s.input_text || ''}">${snippet || '—'}</td>
      <td><button class="action-btn" onclick="viewScan('${s.id}')">View</button></td>
    </tr>`;
  }).join('');
}

function renderTrendChart(trend) {
  const ctx = document.getElementById('trend-chart');
  if (!ctx) return;
  const labels = trend.length ? trend.map(t => t.label) : ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const data   = trend.length ? trend.map(t => t.score) : [72, 68, 75, 80, 78, 85, 82];
  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{ data, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 2, pointRadius: 3, fill: true, tension: 0.4 }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 11 } } }, y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b', font: { size: 11 } } } } }
  });
}

function showSection(name, el) {
  document.querySelectorAll('[id^="section-"]').forEach(s => s.style.display = 'none');
  document.getElementById('section-' + name).style.display = 'block';
  document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
  if (el) el.classList.add('active');
}

async function quickAnalyze() {
  const text = document.getElementById('quick-input').value.trim();
  if (!text) return;
  const res = document.getElementById('quick-result');
  res.textContent = 'Analyzing…';
  try {
    const data = await apiFetch('/analyze', { method: 'POST', body: JSON.stringify({ text }) });
    if (data) {
      const cls = data.verdict === 'SCAM' ? 'color:var(--red)' : data.verdict === 'SUSPICIOUS' ? 'color:var(--yellow)' : 'color:var(--green)';
      res.innerHTML = `<span style="${cls};font-weight:700">${data.verdict}</span> — Risk Score: ${data.risk_score}/100`;
    }
  } catch(e) { res.textContent = 'Error analyzing. Please try again.'; }
}

async function saveAlerts() {
  const prefs = {
    email_alerts: document.getElementById('toggle-email').checked,
    sms_alerts: document.getElementById('toggle-sms').checked,
    weekly_digest: document.getElementById('toggle-digest').checked
  };
  try { await apiFetch('/auth/preferences', { method: 'PUT', body: JSON.stringify(prefs) }); } catch(_) {}
  showToast('Alert preferences saved!');
}

async function saveAccount() {
  const data = {
    name: document.getElementById('acc-name').value,
    email: document.getElementById('acc-email').value,
    phone: document.getElementById('acc-phone').value
  };
  try { await apiFetch('/auth/me', { method: 'PUT', body: JSON.stringify(data) }); } catch(_) {}
  showToast('Account updated!');
}

function confirmDelete() {
  if (confirm('Are you sure? This will permanently delete your account and all data.')) {
    apiFetch('/auth/me', { method: 'DELETE' }).then(() => { localStorage.clear(); window.location.href = '/'; }).catch(() => {});
  }
}

function viewScan(id) { window.location.href = `/#analyzer?scan=${id}`; }

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 3000);
}

async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) };
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

document.addEventListener('DOMContentLoaded', loadDashboard);
