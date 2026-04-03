/* ScamShield AI — app.js v5.0 (Backend Auth, no Firebase SDK) */
const API = window.location.origin;

/* ── Auth gate (backend JWT) ── */
(function() {
  if (window.location.pathname.includes("auth")) return;
  const t = new URLSearchParams(window.location.search).get("token");
  if (t) {
    localStorage.setItem("ss_token", t);
    fetch(API + "/auth/me", { headers: { Authorization: "Bearer " + t } })
      .then(r => r.json()).then(u => {
        localStorage.setItem("ss_user", JSON.stringify({ name:u.name||"", email:u.email||"", avatar:u.avatar||"", phone:u.phone||"", uid:u.id||"" }));
        window.history.replaceState({}, "", "/");
      }).catch(() => {});
    return;
  }
  if (!localStorage.getItem("ss_token")) window.location.replace("/auth");
})();

/* ── Token / user helpers ── */
function getToken() { return localStorage.getItem("ss_token"); }
function getUser()  { try { return JSON.parse(localStorage.getItem("ss_user") || "null"); } catch { return null; } }
function logout()   { localStorage.removeItem("ss_token"); localStorage.removeItem("ss_user"); window.location.replace("/auth"); }

/* ── API helper ── */
async function apiFetch(path, opts) {
  opts = opts || {};
  const token = getToken();
  const headers = Object.assign({ "Content-Type": "application/json" }, token ? { Authorization: "Bearer " + token } : {}, opts.headers || {});
  const res = await fetch(API + path, Object.assign({}, opts, { headers }));
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || "HTTP " + res.status); }
  return res.json();
}

/* ── Theme ── */
function initTheme() {
  const t = localStorage.getItem("ss_theme") || "dark";
  document.documentElement.setAttribute("data-theme", t);
  const el = document.getElementById("theme-icon"); if (el) el.textContent = t === "dark" ? "☀️" : "🌙";
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("ss_theme", next);
  const el = document.getElementById("theme-icon"); if (el) el.textContent = next === "dark" ? "☀️" : "🌙";
  if (window._radarChart) updateChartTheme();
  if (typeof loadGraph === "function") loadGraph();
}

/* ── User area ── */
function renderUserArea() {
  const area = document.getElementById("user-area"); if (!area) return;
  const user = getUser();
  if (!user) { area.innerHTML = `<a href="/auth" style="background:var(--accent);color:#fff;padding:7px 16px;border-radius:8px;font-weight:600;font-size:.85rem;text-decoration:none">Sign In</a>`; return; }
  const initials = (user.name||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();
  const av = user.avatar ? `<img src="${user.avatar}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>` : initials;
  area.innerHTML = `<div class="user-pill"><div class="user-avatar">${av}</div><span>${user.name||user.phone||"User"}</span><button class="logout-btn" onclick="logout()" title="Sign out">✕</button></div>`;
}

/* ── Samples ── */
const SAMPLES = {
  telegram: "Earn ₹8,000 per day from home! Simple Telegram tasks — like YouTube videos, subscribe channels.\nJoin our Telegram group NOW — limited seats only!\nPay ₹500 registration fee to activate your account.\nDaily payment guaranteed. WhatsApp karo abhi: 9876543210\nUPI: taskpay99@okaxis",
  fake_job: "URGENT HIRING — Amazon Task Team\nWork from home, earn ₹10,000/day. No experience needed.\nOffer expires in 2 hours — don't miss!\nSend your Aadhaar card and PAN card to confirm your slot.\nRegistration fee: ₹1,000 (refundable)\nContact: hiringnow-india.com",
  phishing: "Dear Candidate, your application at Infosys Task Force has been selected!\nTo confirm your joining, please share your OTP received on your registered mobile.\nAlso verify your bank account details for salary processing.\nHurry — offer expires today only. Click: http://earnmoney-daily.in/verify",
  brand_impersonation: "Google Work From Home Program — Earn ₹15,000/day!\nYou have been selected from our database. Congratulations!\nNo experience required. Flexible hours. Be your own boss.\nContact our HR: google.hiring2024@gmail.com\nLimited slots — act fast!",
  legit: "Hi, I am reaching out from the Talent Acquisition team at Tata Consultancy Services.\nWe reviewed your profile on LinkedIn and would like to schedule a technical interview for the Software Engineer role.\nThe interview will be conducted via Zoom next week.\nNo fees are involved at any stage of our hiring process.\nRegards, HR Team | careers@tcs.com | tcs.com"
};
function loadSample(key) { document.getElementById("input-text").value = SAMPLES[key]; document.querySelectorAll(".tab")[0].click(); }

/* ── Tab switching ── */
function switchTab(tab, btn) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  document.getElementById("tab-" + tab).classList.add("active");
  if (btn) btn.classList.add("active");
}

/* ── Image OCR ── */
var _imgB64 = null;
function handleImageSelect(e) { if (e.target.files[0]) _loadImg(e.target.files[0]); }
function handleDrop(e) { e.preventDefault(); var f = e.dataTransfer.files[0]; if (f && f.type.startsWith("image/")) _loadImg(f); }
function _loadImg(file) {
  var r = new FileReader();
  r.onload = function(e) {
    _imgB64 = e.target.result.split(",")[1];
    document.getElementById("img-preview").src = e.target.result;
    document.getElementById("img-preview-wrap").classList.remove("hidden");
    document.getElementById("upload-zone").classList.add("hidden");
  };
  r.readAsDataURL(file);
}
function clearImage() {
  _imgB64 = null;
  document.getElementById("img-preview-wrap").classList.add("hidden");
  document.getElementById("upload-zone").classList.remove("hidden");
  document.getElementById("img-input").value = "";
}

/* ── Core analysis ── */
async function runAnalysis() {
  var activeTab = (document.querySelector(".tab.active") || {}).dataset && document.querySelector(".tab.active").dataset.tab;
  var text = (document.getElementById("input-text") || {}).value && document.getElementById("input-text").value.trim() || "";
  var domain = (document.getElementById("input-domain") || {}).value && document.getElementById("input-domain").value.trim() || "";
  if (activeTab === "image" && !_imgB64) { alert("Please select a screenshot first."); return; }
  if (activeTab === "text" && !text) { alert("Please paste a message to analyze."); return; }
  if (activeTab === "domain" && !domain) { alert("Please enter a domain or URL."); return; }
  _setLoading(true);
  var rc = document.getElementById("result-card"); if (rc) rc.classList.add("hidden");
  try {
    var data;
    if (activeTab === "image") {
      var fd = new FormData();
      var blob = await (await fetch("data:image/png;base64," + _imgB64)).blob();
      fd.append("file", blob, "screenshot.png");
      var token = getToken();
      var res = await fetch(API + "/analyze/image", { method:"POST", body:fd, headers: token ? { Authorization:"Bearer "+token } : {} });
      if (!res.ok) throw new Error("Server error " + res.status);
      data = await res.json();
    } else {
      var payload = {};
      if (text) payload.text = text;
      if (domain) payload.domain = domain;
      data = await apiFetch("/analyze", { method:"POST", body:JSON.stringify(payload) });
    }
    renderResult(data);
    _updatePersonalScore(data);
    _loadStats();
  } catch (err) {
    alert("Analysis failed: " + err.message + "\n\nMake sure the backend is running on port 8000.");
  } finally { _setLoading(false); }
}
function _setLoading(on) {
  var btn = document.getElementById("analyze-btn"); if (btn) btn.disabled = on;
  var bt = document.getElementById("btn-text"); if (bt) bt.classList.toggle("hidden", on);
  var bl = document.getElementById("btn-loader"); if (bl) bl.classList.toggle("hidden", !on);
}

/* ── Render result ── */
var _radarChart = null;
function renderResult(data) {
  var v = data.verdict.toLowerCase();
  var icons = { scam:"🚨", suspicious:"⚠️", safe:"✅" };
  var labels = { scam:"SCAM DETECTED", suspicious:"SUSPICIOUS", safe:"LOOKS SAFE" };
  var langMap = { hindi:"🇮�� Hindi", telugu:"🇮🇳 Telugu", hinglish:"🇮🇳 Hinglish" };
  document.getElementById("verdict-banner").className = "verdict-banner " + v;
  document.getElementById("verdict-icon").textContent = icons[v];
  var lbl = document.getElementById("verdict-label"); lbl.textContent = labels[v]; lbl.className = "verdict-label " + v;
  document.getElementById("verdict-score").textContent = data.overall_risk;
  var lang = document.getElementById("verdict-lang"); if (lang) lang.textContent = langMap[data.language] || "";
  var fill = document.getElementById("risk-fill"); fill.className = "risk-fill " + v; fill.style.width = "0%";
  setTimeout(function() { fill.style.width = data.overall_risk + "%"; }, 80);
  var adv = document.getElementById("advice-box"); adv.textContent = data.advice; adv.className = "advice-box " + v;
  _renderBreakdown(data.category_scores || {});
  var list = document.getElementById("factors-list"); list.innerHTML = "";
  if (!data.factors || !data.factors.length) {
    list.innerHTML = "<p style=\"color:var(--muted);font-size:.88rem\">No specific risk signals detected.</p>";
  } else {
    data.factors.forEach(function(f) {
      var item = document.createElement("div"); item.className = "factor-item";
      item.innerHTML = "<div class=\"factor-icon\">" + f.icon + "</div><div class=\"factor-body\"><div class=\"factor-header\"><span class=\"factor-label\">" + f.label + "</span><span class=\"factor-badge " + f.severity + "\">" + f.severity.toUpperCase() + "</span></div><div class=\"factor-score-bar\"><div class=\"factor-score-fill " + f.severity + "\" style=\"width:" + f.score + "%\"></div></div><div class=\"factor-explanation\">" + f.explanation + "</div></div>";
      list.appendChild(item);
    });
  }
  var rc = document.getElementById("result-card"); rc.classList.remove("hidden"); rc.scrollIntoView({ behavior:"smooth", block:"start" });
}
var CAT_COLORS = { content:"#3b82f6", email:"#f59e0b", url:"#8b5cf6", salary:"#ec4899", network:"#ef4444", behavior:"#10b981" };
function _renderBreakdown(scores) {
  var cats = Object.keys(scores).filter(function(k) { return scores[k] > 0; });
  var bs = document.querySelector(".breakdown-section"); if (!cats.length) { if (bs) bs.style.display="none"; return; } if (bs) bs.style.display="";
  var ctx = document.getElementById("radar-chart"); if (ctx) ctx = ctx.getContext("2d");
  if (ctx) {
    if (_radarChart) { _radarChart.destroy(); _radarChart = null; }
    var isDark = document.documentElement.getAttribute("data-theme") !== "light";
    _radarChart = new Chart(ctx, { type:"radar", data:{ labels:Object.keys(scores).map(function(k){return k.charAt(0).toUpperCase()+k.slice(1);}), datasets:[{ data:Object.values(scores), backgroundColor:"rgba(239,68,68,0.15)", borderColor:"#ef4444", borderWidth:2, pointBackgroundColor:"#ef4444", pointRadius:4 }] }, options:{ responsive:true, maintainAspectRatio:true, scales:{ r:{ min:0, max:100, ticks:{display:false}, grid:{color:isDark?"rgba(255,255,255,0.08)":"rgba(0,0,0,0.08)"}, pointLabels:{color:isDark?"#94a3b8":"#64748b",font:{size:11}} } }, plugins:{legend:{display:false}} } });
    window._radarChart = _radarChart;
  }
  var barsEl = document.getElementById("breakdown-bars"); if (!barsEl) return; barsEl.innerHTML = "";
  Object.entries(scores).forEach(function(entry) {
    var cat = entry[0], val = entry[1], color = CAT_COLORS[cat] || "#64748b";
    var row = document.createElement("div"); row.className = "bar-row";
    row.innerHTML = "<span class=\"bar-label\">" + cat + "</span><div class=\"bar-track\"><div class=\"bar-fill\" style=\"width:0%;background:" + color + "\" data-val=\"" + val + "\"></div></div><span class=\"bar-val\">" + val + "</span>";
    barsEl.appendChild(row);
  });
  setTimeout(function() { barsEl.querySelectorAll(".bar-fill").forEach(function(b) { b.style.width = b.dataset.val + "%"; }); }, 100);
}
function updateChartTheme() {
  var scores = {}; document.querySelectorAll(".bar-row").forEach(function(r) { var l=r.querySelector(".bar-label"); var v=r.querySelector(".bar-val"); if(l&&v) scores[l.textContent.toLowerCase()]=parseInt(v.textContent||"0"); });
  if (Object.keys(scores).length) _renderBreakdown(scores);
}

/* ── Personal safety score ── */
var _scanHistory = JSON.parse(localStorage.getItem("ss_scan_history") || "[]");
function _updatePersonalScore(data) {
  _scanHistory.push({ verdict:data.verdict, risk:data.overall_risk, ts:Date.now() });
  if (_scanHistory.length > 50) _scanHistory.shift();
  localStorage.setItem("ss_scan_history", JSON.stringify(_scanHistory));
  var total=_scanHistory.length, scams=_scanHistory.filter(function(s){return s.verdict==="SCAM";}).length;
  var avgRisk=Math.round(_scanHistory.reduce(function(a,s){return a+s.risk;},0)/total);
  var safetyScore=Math.max(0,100-avgRisk);
  var el=document.getElementById("safety-score-body"); if(!el) return;
  var color=safetyScore>=70?"var(--green)":safetyScore>=40?"var(--yellow)":"var(--red)";
  el.innerHTML="<div style=\"display:flex;align-items:center;gap:16px;flex-wrap:wrap\"><div style=\"font-size:2rem;font-weight:900;color:"+color+"\">"+safetyScore+"/100</div><div><div style=\"font-size:.88rem;color:var(--text2)\">Based on your last "+total+" scan(s)</div><div style=\"font-size:.82rem;color:var(--muted)\">"+scams+" scam(s) detected · Avg risk: "+avgRisk+"/100</div></div></div>";
  var ss=document.getElementById("safety-score-section"); if(ss) ss.style.display="";
}

/* ── Share ── */
function shareResult() {
  var verdict=document.getElementById("verdict-label").textContent, score=document.getElementById("verdict-score").textContent;
  var text="ScamShield AI: "+verdict+" (Risk: "+score+"/100)\nCheck job offers at "+window.location.origin+"\nHelpline: 1930";
  if (navigator.share) navigator.share({ title:"ScamShield AI Warning", text:text }).catch(function(){});
  else navigator.clipboard.writeText(text).then(function(){showToast("Warning copied!");});
}

/* ── Stats ── */
async function _loadStats() {
  try {
    var s = await apiFetch("/stats");
    function animCount(id, val) {
      var el=document.getElementById(id); if(!el||!val) return;
      var c=0, step=Math.ceil(val/30);
      var t=setInterval(function(){c=Math.min(c+step,val);el.textContent=c.toLocaleString("en-IN");if(c>=val)clearInterval(t);},40);
    }
    animCount("stat-scanned", s.total_scanned); animCount("stat-detected", s.scams_detected);
  } catch(e) {}
}

/* ── Reports ── */
async function loadReports() {
  var list=document.getElementById("reports-list"); if(!list) return;
  list.innerHTML="<div class=\"feed-loading\">Loading...</div>";
  var type=(document.getElementById("filter-type")||{}).value||"";
  var state=(document.getElementById("filter-state")||{}).value||"";
  var url="/reports?limit=30";
  if(type) url+="&scam_type="+encodeURIComponent(type);
  if(state) url+="&state="+encodeURIComponent(state);
  try {
    var reports=await apiFetch(url); list.innerHTML="";
    if(!reports.length){list.innerHTML="<div class=\"feed-loading\">No reports found.</div>";return;}
    reports.forEach(function(r){
      var v=r.verdict.toLowerCase(), item=document.createElement("div"); item.className="report-item";
      item.innerHTML="<div class=\"report-risk "+v+"\">"+r.risk+"</div><div class=\"report-body\"><div class=\"report-type\">"+r.type+"</div><div class=\"report-snippet\">\""+r.snippet+"\"</div><div class=\"report-meta\"><span>📍 "+r.location+(r.state?", "+r.state:"")+"</span><span>🕐 "+r.time+"</span>"+(r.is_verified?"<span style=\"color:var(--green)\">✅ Verified</span>":"")+"<button class=\"upvote-btn\" onclick=\"upvote('"+r.id+"',this)\">👍 "+r.upvotes+" Confirmed</button></div></div>";
      list.appendChild(item);
    });
  } catch(e){list.innerHTML="<div class=\"feed-loading\">Could not load reports.</div>";}
}
async function upvote(id, btn) {
  try{await apiFetch("/reports/"+id+"/upvote",{method:"POST"});}catch(e){}
  var n=parseInt(btn.textContent.match(/\d+/)[0])+1; btn.textContent="👍 "+n+" Confirmed"; btn.style.color="var(--green)"; btn.style.borderColor="var(--green)";
}

/* ── Trust Graph ── */
async function loadGraph() {
  try{var d=await apiFetch("/graph/data");drawGraph(d.nodes,d.links);}catch(e){_drawDemoGraph();}
}
function drawGraph(nodes,links){
  var canvas=document.getElementById("graph-canvas"); if(!canvas) return;
  var ctx=canvas.getContext("2d"),W=canvas.width,H=canvas.height;
  var isDark=document.documentElement.getAttribute("data-theme")!=="light";
  var colors={root:"#8b5cf6",phone:"#ef4444",upi:"#f59e0b",domain:"#3b82f6",email:"#10b981",company:"#ec4899"};
  var root=nodes.find(function(n){return n.group==="root";}), others=nodes.filter(function(n){return n.group!=="root";});
  var pos={}; pos[root.id]={x:W/2,y:H/2};
  others.forEach(function(n,i){var angle=(i/others.length)*Math.PI*2-Math.PI/2,r=Math.min(W,H)*0.37;pos[n.id]={x:W/2+Math.cos(angle)*r,y:H/2+Math.sin(angle)*r};});
  ctx.clearRect(0,0,W,H); ctx.fillStyle=isDark?"#0f1628":"#f8fafc"; ctx.fillRect(0,0,W,H);
  links.forEach(function(l){var s=pos[l.source],t=pos[l.target];if(!s||!t)return;ctx.beginPath();ctx.moveTo(s.x,s.y);ctx.lineTo(t.x,t.y);ctx.strokeStyle=isDark?"rgba(59,130,246,0.18)":"rgba(59,130,246,0.25)";ctx.lineWidth=1;ctx.stroke();});
  nodes.forEach(function(n){var p=pos[n.id];if(!p)return;var r=n.group==="root"?22:13,color=colors[n.group]||"#64748b";ctx.shadowColor=color;ctx.shadowBlur=14;ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fillStyle=color+"28";ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=2;ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle=isDark?"#e2e8f0":"#1e293b";ctx.font=n.group==="root"?"bold 10px Segoe UI":"9px Segoe UI";ctx.textAlign="center";ctx.fillText(n.label.length>20?n.label.slice(0,18)+"…":n.label,p.x,p.y+r+13);});
}
function _drawDemoGraph(){drawGraph([{id:"root",label:"🛡️ ScamShield DB",group:"root"},{id:"p1",label:"📞 9876543210",group:"phone"},{id:"p2",label:"📞 7654321098",group:"phone"},{id:"u1",label:"💳 taskpay99@okaxis",group:"upi"},{id:"u2",label:"💳 earn.daily@paytm",group:"upi"},{id:"d1",label:"🌐 earnmoney-daily.in",group:"domain"},{id:"d2",label:"🌐 quickjobs-india.com",group:"domain"},{id:"d3",label:"🌐 telegram-tasks.co.in",group:"domain"}],[{source:"root",target:"p1"},{source:"root",target:"p2"},{source:"root",target:"u1"},{source:"root",target:"u2"},{source:"root",target:"d1"},{source:"root",target:"d2"},{source:"root",target:"d3"}]);}

/* ── Toast ── */
function showToast(msg){var t=document.getElementById("toast");if(!t)return;t.textContent=msg;t.style.display="block";setTimeout(function(){t.style.display="none";},3000);}

/* ── FAQ ── */
function toggleFaq(el){el.parentElement.classList.toggle("open");}

/* ── API Docs ── */
async function tryEndpoint(path){
  var re=document.getElementById("api-try-result"),oe=document.getElementById("api-try-output");
  if(!re||!oe)return; re.classList.remove("hidden"); oe.textContent="Loading...";
  try{var d=await apiFetch("/"+path);oe.textContent=JSON.stringify(d,null,2);}catch(err){oe.textContent="Error: "+err.message;}
  re.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function copyText(text){navigator.clipboard.writeText(text).then(function(){showToast("Copied!");});}

/* ── Contact ── */
async function submitContact(e){
  e.preventDefault();
  var btn=document.getElementById("contact-submit-btn"),txt=document.getElementById("contact-btn-text"),ldr=document.getElementById("contact-btn-loader");
  if(btn)btn.disabled=true; if(txt)txt.classList.add("hidden"); if(ldr)ldr.classList.remove("hidden");
  try{
    await apiFetch("/contact",{method:"POST",body:JSON.stringify({name:document.getElementById("c-name").value,email:document.getElementById("c-email").value,subject:document.getElementById("c-subject").value,message:document.getElementById("c-message").value})});
    var f=document.getElementById("contact-form");if(f)f.reset();
    var s=document.getElementById("contact-success");if(s)s.classList.remove("hidden");
  }catch(e){showToast("Error sending message. Please try again.");}
  finally{if(btn)btn.disabled=false;if(txt)txt.classList.remove("hidden");if(ldr)ldr.classList.add("hidden");}
}

/* ── Newsletter ── */
async function subscribeNewsletter(e){
  e.preventDefault();
  var email=(document.getElementById("nl-email")||{}).value;
  try{await apiFetch("/newsletter/subscribe",{method:"POST",body:JSON.stringify({email:email})});}catch(e){}
  var m=document.getElementById("nl-msg");if(m)m.style.display="block";
  var i=document.getElementById("nl-email");if(i)i.value="";
}

/* ── Dashboard ── */
async function loadDashboard(){
  var user=getUser();
  var ne=document.getElementById("dash-user-name");if(ne)ne.textContent=(user&&(user.name||user.phone))||"Guest";
  var history=JSON.parse(localStorage.getItem("ss_scan_history")||"[]");
  var total=history.length,scams=history.filter(function(s){return s.verdict==="SCAM";}).length;
  var safe=history.filter(function(s){return s.verdict==="SAFE";}).length;
  var avgRisk=total?Math.round(history.reduce(function(a,s){return a+s.risk;},0)/total):0;
  var safetyScore=Math.max(0,100-avgRisk);
  function set(id,v){var el=document.getElementById(id);if(el)el.textContent=v;}
  set("dash-safety",safetyScore);set("dash-total",total);set("dash-scams",scams);set("dash-safe",safe);
  if(user){var n=document.getElementById("acc-name");if(n)n.value=user.name||"";var em=document.getElementById("acc-email");if(em)em.value=user.email||"";var ph=document.getElementById("acc-phone");if(ph)ph.value=user.phone||"";}
  _renderScansTable(history.slice(-10).reverse());
  _renderTrendChart(history);
  if(user){
    try{
      var token=getToken();
      if(token){
        var scansData=await fetch(API+"/scans/my",{headers:{Authorization:"Bearer "+token}}).then(function(r){return r.ok?r.json():null;});
        var prefs=await fetch(API+"/auth/preferences",{headers:{Authorization:"Bearer "+token}}).then(function(r){return r.ok?r.json():null;});
        if(scansData&&scansData.length)_renderScansTable(scansData);
        if(prefs){var te=document.getElementById("toggle-email");if(te)te.checked=prefs.email_alerts;var ts=document.getElementById("toggle-sms");if(ts)ts.checked=prefs.sms_alerts;var td=document.getElementById("toggle-digest");if(td)td.checked=prefs.weekly_digest;}
      }
    }catch(e){}
  }
}
function _renderScansTable(scans){
  var tbody=document.getElementById("scans-tbody");if(!tbody)return;
  if(!scans||!scans.length){tbody.innerHTML="<tr><td colspan=\"4\" style=\"text-align:center;color:var(--muted);padding:24px\">No scans yet.</td></tr>";return;}
  tbody.innerHTML=scans.map(function(s){
    var cls=s.verdict==="SCAM"?"scam":s.verdict==="SUSPICIOUS"?"suspicious":"safe";
    var date=s.created_at?new Date(s.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short"}):new Date(s.ts||Date.now()).toLocaleDateString("en-IN",{day:"2-digit",month:"short"});
    var snippet=((s.input_text||s.text||"")).slice(0,45)+"…";
    return "<tr><td>"+date+"</td><td><span class=\"badge "+cls+"\">"+s.verdict+"</span></td><td>"+(s.risk_score||s.risk||"-")+"/100</td><td style=\"max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap\">"+snippet+"</td></tr>";
  }).join("");
}
var _trendChart=null;
function _renderTrendChart(history){
  var ctx=document.getElementById("trend-chart");if(!ctx)return;
  if(_trendChart){_trendChart.destroy();_trendChart=null;}
  var last7=history.slice(-7),isDark=document.documentElement.getAttribute("data-theme")!=="light";
  _trendChart=new Chart(ctx,{type:"line",data:{labels:last7.map(function(_,i){return"Scan "+(i+1);}),datasets:[{data:last7.map(function(s){return Math.max(0,100-(s.risk||s.risk_score||0));}),borderColor:"#3b82f6",backgroundColor:"rgba(59,130,246,0.1)",borderWidth:2,pointRadius:3,fill:true,tension:0.4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:isDark?"#64748b":"#94a3b8",font:{size:10}}},y:{min:0,max:100,grid:{color:isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.05)"},ticks:{color:isDark?"#64748b":"#94a3b8",font:{size:10}}}}}});
}
async function quickAnalyze(){
  var text=(document.getElementById("quick-input")||{}).value&&document.getElementById("quick-input").value.trim();if(!text)return;
  var res=document.getElementById("quick-result");if(res)res.textContent="Analyzing…";
  try{var data=await apiFetch("/analyze",{method:"POST",body:JSON.stringify({text:text})});var color=data.verdict==="SCAM"?"var(--red)":data.verdict==="SUSPICIOUS"?"var(--yellow)":"var(--green)";if(res)res.innerHTML="<span style=\"color:"+color+";font-weight:700\">"+data.verdict+"</span> — Risk: "+data.overall_risk+"/100";}
  catch(e){if(res)res.textContent="Error. Is the backend running?";}
}
async function saveAlerts(){
  var token=getToken();if(!token){showToast("Sign in to save preferences.");return;}
  var prefs={email_alerts:(document.getElementById("toggle-email")||{}).checked,sms_alerts:(document.getElementById("toggle-sms")||{}).checked,weekly_digest:(document.getElementById("toggle-digest")||{}).checked};
  try{await apiFetch("/auth/preferences",{method:"PUT",body:JSON.stringify(prefs)});showToast("✅ Preferences saved!");}catch(e){showToast("Error saving.");}
}
async function saveAccount(){
  var token=getToken();if(!token){showToast("Sign in to update account.");return;}
  var data={name:(document.getElementById("acc-name")||{}).value,email:(document.getElementById("acc-email")||{}).value};
  try{await apiFetch("/auth/me",{method:"PUT",body:JSON.stringify(data)});var user=getUser();if(user){user.name=data.name;localStorage.setItem("ss_user",JSON.stringify(user));renderUserArea();}showToast("✅ Account updated!");}catch(e){showToast("Error updating account.");}
}
function confirmDelete(){
  if(confirm("Permanently delete your account and all data? This cannot be undone.")){
    var token=getToken();
    fetch(API+"/auth/me",{method:"DELETE",headers:{Authorization:"Bearer "+token}}).finally(function(){localStorage.clear();window.location.replace("/auth");});
  }
}

/* ── Graph stats ── */
async function loadGraphStats(){
  try{var s=await apiFetch("/stats");function set(id,v){var el=document.getElementById(id);if(el)el.textContent=v||"-";}set("gs-total",s.total_scanned);set("gs-scams",s.scams_detected);set("gs-phones",s.unique_phones_flagged);set("gs-upi",s.unique_upi_flagged);}catch(e){}
}

/* ── SPA Navigation ── */
var PAGE_INIT={};
function navigate(page,snavEl){
  document.querySelectorAll(".spa-page").forEach(function(p){p.classList.remove("active");});
  var target=document.getElementById("page-"+page);if(target)target.classList.add("active");
  document.querySelectorAll(".snav").forEach(function(a){a.classList.remove("active");});
  var ms=document.querySelector(".snav[data-page=\""+page+"\"]");if(ms)ms.classList.add("active");
  document.querySelectorAll(".tnav").forEach(function(a){a.classList.remove("active");});
  var mt=document.querySelector(".tnav[data-page=\""+page+"\"]");if(mt)mt.classList.add("active");
  var sb=document.getElementById("spa-sidebar");if(sb)sb.classList.remove("open");
  window.location.hash=page==="home"?"":page;
  if(!PAGE_INIT[page]){PAGE_INIT[page]=true;if(page==="feed")loadReports();if(page==="graph"){loadGraph();loadGraphStats();}if(page==="dashboard")loadDashboard();}
}
function toggleSidebar(){var sb=document.getElementById("spa-sidebar");if(sb)sb.classList.toggle("open");}
function routeFromHash(){
  var hash=window.location.hash.replace("#","")||"home";
  var valid=["home","feed","graph","dashboard","about","contact","api-docs"];
  navigate(valid.indexOf(hash)>=0?hash:"home");
}
function updateLoginNav(){
  var user=getUser(),loginNav=document.getElementById("snav-login");if(!loginNav)return;
  if(user){loginNav.innerHTML="📊 <span>Dashboard</span>";loginNav.dataset.page="dashboard";loginNav.onclick=function(){navigate("dashboard",loginNav);};}
  else{loginNav.innerHTML="🔐 <span>Sign In</span>";loginNav.dataset.page="login";loginNav.onclick=function(){navigate("login",loginNav);};}
}

/* ── Init ── */
document.addEventListener("DOMContentLoaded", function() {
  initTheme(); renderUserArea(); updateLoginNav(); routeFromHash(); _loadStats();
  window.addEventListener("hashchange", routeFromHash);
  var di=document.getElementById("input-domain");if(di)di.addEventListener("keydown",function(e){if(e.key==="Enter")runAnalysis();});
  var observer=new MutationObserver(function(){if(typeof loadGraph==="function")loadGraph();});
  observer.observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
});

