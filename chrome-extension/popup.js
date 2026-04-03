const API = 'http://localhost:8000';

// Show current site
chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
  if (tabs[0]) {
    const url = new URL(tabs[0].url);
    document.getElementById('current-site').textContent = url.hostname;
  }
});

async function analyze() {
  const text = document.getElementById('input-text').value.trim();
  if (!text) return;

  document.getElementById('loading').style.display = 'block';
  document.getElementById('result').style.display = 'none';

  try {
    const res = await fetch(`${API}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    showResult(data);
  } catch (err) {
    document.getElementById('loading').style.display = 'none';
    alert('Cannot connect to ScamShield backend. Make sure it is running on localhost:8000');
  }
}

function showResult(data) {
  document.getElementById('loading').style.display = 'none';
  const v = data.verdict.toLowerCase();
  const icons = { scam: '🚨', suspicious: '⚠️', safe: '✅' };
  const resultEl = document.getElementById('result');
  resultEl.className = `result ${v}`;
  resultEl.style.display = 'block';
  const verdictEl = document.getElementById('verdict');
  verdictEl.textContent = `${icons[v]} ${data.verdict}`;
  verdictEl.className = `verdict ${v}`;
  document.getElementById('score').textContent = `Risk Score: ${data.overall_risk}/100`;
  document.getElementById('advice').textContent = data.advice;
}

// Allow Enter to submit
document.getElementById('input-text').addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'Enter') analyze();
});
