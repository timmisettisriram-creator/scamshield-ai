// Context menu — right-click any selected text to scan
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'scamshield-scan',
    title: '🛡️ Scan with ScamShield AI',
    contexts: ['selection'],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== 'scamshield-scan') return;
  const text = info.selectionText;
  try {
    const res = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    const msg = `ScamShield AI: ${data.verdict} (${data.overall_risk}/100)\n${data.advice}`;
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (m) => alert(m),
      args: [msg],
    });
  } catch (_) {}
});
