/**
 * ScamShield AI — Content Script
 * Injects risk overlays on LinkedIn, Indeed, WhatsApp Web
 */
const API = 'http://localhost:8000';
const SITE = window.location.hostname;

// ── LinkedIn job cards ─────────────────────────────────────────
function scanLinkedInJobs() {
  const cards = document.querySelectorAll('.job-card-container, .jobs-search-results__list-item');
  cards.forEach(card => {
    if (card.dataset.ssScanned) return;
    card.dataset.ssScanned = '1';
    const titleEl = card.querySelector('.job-card-list__title, .base-search-card__title');
    const companyEl = card.querySelector('.job-card-container__company-name, .base-search-card__subtitle');
    if (!titleEl) return;
    const text = `${titleEl.textContent} ${companyEl?.textContent || ''}`;
    analyzeAndBadge(card, text, 'linkedin');
  });
}

// ── Indeed job cards ───────────────────────────────────────────
function scanIndeedJobs() {
  const cards = document.querySelectorAll('.job_seen_beacon, .tapItem');
  cards.forEach(card => {
    if (card.dataset.ssScanned) return;
    card.dataset.ssScanned = '1';
    const text = card.innerText?.slice(0, 500) || '';
    if (text.length < 20) return;
    analyzeAndBadge(card, text, 'indeed');
  });
}

// ── WhatsApp Web messages ──────────────────────────────────────
function scanWhatsAppMessages() {
  const msgs = document.querySelectorAll('.message-in .copyable-text, ._21Ahp');
  msgs.forEach(msg => {
    if (msg.dataset.ssScanned) return;
    msg.dataset.ssScanned = '1';
    const text = msg.innerText?.slice(0, 500) || '';
    if (text.length < 30) return;
    const parent = msg.closest('.message-in') || msg.parentElement;
    if (parent) analyzeAndBadge(parent, text, 'whatsapp');
  });
}

// ── Core: analyze + inject badge ──────────────────────────────
async function analyzeAndBadge(el, text, source) {
  try {
    const res = await fetch(`${API}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data.overall_risk < 20) return; // skip clearly safe

    const badge = createBadge(data, source);
    el.style.position = 'relative';
    el.appendChild(badge);
  } catch (_) {}
}

function createBadge(data, source) {
  const v = data.verdict.toLowerCase();
  const colors = { scam: '#ef4444', suspicious: '#f59e0b', safe: '#10b981' };
  const icons  = { scam: '🚨', suspicious: '⚠️', safe: '✅' };
  const color  = colors[v] || '#64748b';

  const badge = document.createElement('div');
  badge.className = 'ss-badge';
  badge.style.cssText = `
    position: absolute; top: 8px; right: 8px; z-index: 9999;
    background: ${color}22; border: 1px solid ${color}66;
    border-radius: 6px; padding: 4px 10px;
    font-size: 11px; font-weight: 700; color: ${color};
    font-family: 'Segoe UI', sans-serif; cursor: pointer;
    backdrop-filter: blur(4px);
  `;
  badge.textContent = `${icons[v]} ScamShield: ${data.overall_risk}/100`;
  badge.title = data.advice;

  badge.addEventListener('click', e => {
    e.stopPropagation();
    showDetailPanel(data);
  });

  return badge;
}

// ── Detail panel ───────────────────────────────────────────────
function showDetailPanel(data) {
  document.getElementById('ss-panel')?.remove();
  const v = data.verdict.toLowerCase();
  const panel = document.createElement('div');
  panel.id = 'ss-panel';
  panel.style.cssText = `
    position: fixed; bottom: 24px; right: 24px; z-index: 99999;
    width: 320px; background: #141c2e; border: 1px solid #1e2d4a;
    border-radius: 14px; padding: 18px; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    font-family: 'Segoe UI', sans-serif; color: #e2e8f0;
    animation: ssSlideIn .3s ease;
  `;
  const verdictColors = { scam: '#ef4444', suspicious: '#f59e0b', safe: '#10b981' };
  const color = verdictColors[v] || '#64748b';
  panel.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div style="font-weight:800;font-size:1rem;color:${color}">
        ${{ scam:'🚨 SCAM DETECTED', suspicious:'⚠️ SUSPICIOUS', safe:'✅ LOOKS SAFE' }[v]}
      </div>
      <button onclick="document.getElementById('ss-panel').remove()" style="background:transparent;border:none;color:#64748b;cursor:pointer;font-size:1.1rem">✕</button>
    </div>
    <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:10px">Risk Score: <strong style="color:${color}">${data.overall_risk}/100</strong></div>
    <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:12px;line-height:1.5">${data.advice}</div>
    <div style="display:flex;gap:8px">
      <a href="http://localhost:8000" target="_blank" style="flex:1;background:linear-gradient(135deg,#3b82f6,#6366f1);color:#fff;padding:8px;border-radius:7px;text-align:center;font-size:0.8rem;font-weight:700;text-decoration:none">Full Report</a>
      <a href="https://cybercrime.gov.in" target="_blank" style="flex:1;background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);color:#fca5a5;padding:8px;border-radius:7px;text-align:center;font-size:0.8rem;font-weight:700;text-decoration:none">Report Crime</a>
    </div>
  `;
  document.body.appendChild(panel);
  setTimeout(() => panel.remove(), 12000);
}

// ── Observer for dynamic content ──────────────────────────────
const observer = new MutationObserver(() => {
  if (SITE.includes('linkedin.com')) scanLinkedInJobs();
  else if (SITE.includes('indeed.com')) scanIndeedJobs();
  else if (SITE.includes('whatsapp.com')) scanWhatsAppMessages();
});

observer.observe(document.body, { childList: true, subtree: true });

// Initial scan
setTimeout(() => {
  if (SITE.includes('linkedin.com')) scanLinkedInJobs();
  else if (SITE.includes('indeed.com')) scanIndeedJobs();
  else if (SITE.includes('whatsapp.com')) scanWhatsAppMessages();
}, 2000);
