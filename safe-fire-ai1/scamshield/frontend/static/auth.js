/**
 * ScamShield AI — auth.js (Backend OTP — works without Firebase Phone Auth)
 * Google Sign-In uses Firebase popup. Phone OTP uses our backend.
 */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, onAuthStateChanged }
  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const fbApp  = initializeApp({
  apiKey:"AIzaSyD0N0L34gKVtb2CZP7PgajTrd8VeuvROp0",
  authDomain:"safe-fire-ai1.firebaseapp.com",
  projectId:"safe-fire-ai1",
  storageBucket:"safe-fire-ai1.firebasestorage.app",
  messagingSenderId:"311058590739",
  appId:"1:311058590739:web:9dbfe613c6d1f962f623e6"
});
const fbAuth = getAuth(fbApp);
const API    = window.location.origin;

// Apply saved theme
(function(){
  const t = localStorage.getItem("ss_theme")||"dark";
  document.documentElement.setAttribute("data-theme",t);
})();

// If already logged in, skip auth page
if (localStorage.getItem("ss_token")) {
  window.location.replace("/");
}

// Google sign-in redirects back with ?token= — handle it
(function(){
  const t = new URLSearchParams(window.location.search).get("token");
  if (t) {
    localStorage.setItem("ss_token", t);
    fetch(API+"/auth/me",{headers:{Authorization:"Bearer "+t}})
      .then(r=>r.json()).then(u=>{
        localStorage.setItem("ss_user",JSON.stringify({
          name:u.name||"",email:u.email||"",avatar:u.avatar||"",phone:u.phone||"",uid:u.id||""
        }));
      }).catch(()=>{}).finally(()=>window.location.replace("/"));
  }
})();

// Google sign-in via Firebase popup (works if Google is enabled in Firebase Console)
// Falls back to backend redirect if popup fails
window.authWithGoogle = async function() {
  clearMsgs("si"); clearMsgs("su");
  try {
    const provider = new GoogleAuthProvider();
    provider.addScope("email"); provider.addScope("profile");
    const result = await signInWithPopup(fbAuth, provider);
    const user = result.user;
    const token = await user.getIdToken();
    // Exchange Firebase token for our backend JWT
    const res = await fetch(API+"/auth/firebase-token", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({id_token: token})
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("ss_token", data.token);
      localStorage.setItem("ss_user", JSON.stringify(data.user));
      window.location.replace("/");
    } else {
      // Store Firebase token directly and redirect
      localStorage.setItem("ss_token", token);
      localStorage.setItem("ss_user", JSON.stringify({
        name:user.displayName||"",email:user.email||"",
        avatar:user.photoURL||"",phone:"",uid:user.uid
      }));
      window.location.replace("/");
    }
  } catch (err) {
    if (err.code==="auth/popup-closed-by-user"||err.code==="auth/cancelled-popup-request") return;
    // If Firebase Google not enabled, fall back to backend OAuth redirect
    if (err.code==="auth/operation-not-allowed"||err.code==="auth/configuration-not-found") {
      window.location.href = API+"/auth/google";
      return;
    }
    showMsg("si","error",friendlyError(err));
    showMsg("su","error",friendlyError(err));
  }
};

// Tab switching
window.showTab = function(tab) {
  document.querySelectorAll(".auth-tab").forEach(t=>t.classList.remove("active"));
  document.querySelectorAll(".auth-panel").forEach(p=>p.classList.remove("active"));
  document.getElementById("tab-"+tab).classList.add("active");
  document.getElementById("panel-"+tab).classList.add("active");
};

// ── Phone OTP via backend ──────────────────────────────────────
let siPhone="", suPhone="", suName="", suEmail="";

window.siSendOTP = async function() {
  const phone = document.getElementById("si-phone").value.trim();
  if (phone.length!==10||!/^[6-9]/.test(phone)){showMsg("si","error","Enter a valid 10-digit Indian mobile number.");return;}
  clearMsgs("si");
  setBtnLoading("si-send-btn","si-send-text","si-send-load",true);
  try {
    const res = await fetch(API+"/auth/otp/send",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({phone})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail||"Failed to send OTP");
    siPhone = phone;
    document.getElementById("si-step-phone").classList.add("hidden");
    document.getElementById("si-step-otp").classList.remove("hidden");
    // Show OTP on screen if dev mode
    const info = document.getElementById("si-otp-info");
    if (data.dev_otp) {
      info.innerHTML = `OTP sent! <strong style="color:var(--green);font-size:1.2rem;letter-spacing:.1em">${data.dev_otp}</strong><br><small style="color:var(--muted)">Dev mode — enter this OTP above</small>`;
    } else {
      info.textContent = `OTP sent to +91 ${phone}. Valid for 5 minutes.`;
    }
    document.querySelectorAll("#si-otp-row .otp-cell")[0].focus();
    startTimer("si",30);
  } catch(err){showMsg("si","error",err.message);}
  finally{setBtnLoading("si-send-btn","si-send-text","si-send-load",false);}
};

window.siVerifyOTP = async function() {
  const otp = getOTP("si");
  if (otp.length!==6){showMsg("si","error","Enter the complete 6-digit OTP.");return;}
  clearMsgs("si");
  setBtnLoading("si-verify-btn","si-verify-text","si-verify-load",true);
  try {
    const res = await fetch(API+"/auth/otp/verify",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({phone:siPhone,otp})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail||"Verification failed");
    localStorage.setItem("ss_token",data.token);
    localStorage.setItem("ss_user",JSON.stringify(data.user));
    showMsg("si","success","Signed in! Redirecting...");
    setTimeout(()=>window.location.replace("/"),800);
  } catch(err){
    showMsg("si","error",err.message);
    document.getElementById("si-otp-row").style.animation="shake .4s ease";
    setTimeout(()=>document.getElementById("si-otp-row").style.animation="",400);
  }
  finally{setBtnLoading("si-verify-btn","si-verify-text","si-verify-load",false);}
};

window.siResend = async function(){
  document.getElementById("si-step-otp").classList.add("hidden");
  document.getElementById("si-step-phone").classList.remove("hidden");
  clearOTP("si"); await window.siSendOTP();
};
window.siBack = function(){
  document.getElementById("si-step-otp").classList.add("hidden");
  document.getElementById("si-step-phone").classList.remove("hidden");
  clearOTP("si"); clearMsgs("si");
};

window.suSendOTP = async function() {
  const name  = document.getElementById("su-name").value.trim();
  const phone = document.getElementById("su-phone").value.trim();
  const email = document.getElementById("su-email").value.trim();
  const agree = document.getElementById("su-agree").checked;
  if (!name){showMsg("su","error","Please enter your full name.");return;}
  if (phone.length!==10||!/^[6-9]/.test(phone)){showMsg("su","error","Enter a valid 10-digit mobile number.");return;}
  if (!agree){showMsg("su","error","Please agree to the Terms to continue.");return;}
  clearMsgs("su");
  setBtnLoading("su-send-btn","su-send-text","su-send-load",true);
  try {
    const res = await fetch(API+"/auth/otp/send",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({phone})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail||"Failed to send OTP");
    suPhone=phone; suName=name; suEmail=email;
    document.getElementById("su-step-phone").classList.add("hidden");
    document.getElementById("su-step-otp").classList.remove("hidden");
    const info = document.getElementById("su-otp-info");
    if (data.dev_otp) {
      info.innerHTML = `OTP sent! <strong style="color:var(--green);font-size:1.2rem;letter-spacing:.1em">${data.dev_otp}</strong><br><small style="color:var(--muted)">Dev mode — enter this OTP above</small>`;
    } else {
      info.textContent = `OTP sent to +91 ${phone}. Valid for 5 minutes.`;
    }
    document.querySelectorAll("#su-otp-row .otp-cell")[0].focus();
    startTimer("su",30);
  } catch(err){showMsg("su","error",err.message);}
  finally{setBtnLoading("su-send-btn","su-send-text","su-send-load",false);}
};

window.suVerifyOTP = async function() {
  const otp = getOTP("su");
  if (otp.length!==6){showMsg("su","error","Enter the complete 6-digit OTP.");return;}
  clearMsgs("su");
  setBtnLoading("su-verify-btn","su-verify-text","su-verify-load",true);
  try {
    const res = await fetch(API+"/auth/otp/verify",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({phone:suPhone,otp})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail||"Verification failed");
    const user = {...data.user, name:suName||data.user.name, email:suEmail||data.user.email};
    localStorage.setItem("ss_token",data.token);
    localStorage.setItem("ss_user",JSON.stringify(user));
    showMsg("su","success","Account created! Redirecting...");
    setTimeout(()=>window.location.replace("/"),800);
  } catch(err){
    showMsg("su","error",err.message);
    document.getElementById("su-otp-row").style.animation="shake .4s ease";
    setTimeout(()=>document.getElementById("su-otp-row").style.animation="",400);
  }
  finally{setBtnLoading("su-verify-btn","su-verify-text","su-verify-load",false);}
};

window.suResend = async function(){
  document.getElementById("su-step-otp").classList.add("hidden");
  document.getElementById("su-step-phone").classList.remove("hidden");
  clearOTP("su"); await window.suSendOTP();
};
window.suBack = function(){
  document.getElementById("su-step-otp").classList.add("hidden");
  document.getElementById("su-step-phone").classList.remove("hidden");
  clearOTP("su"); clearMsgs("su");
};

// OTP cell helpers
window.cellInput = function(el,idx,prefix){
  el.value=el.value.replace(/\D/g,"");
  if(el.value){
    el.classList.add("filled");
    const cells=document.querySelectorAll("#"+prefix+"-otp-row .otp-cell");
    if(idx<5)cells[idx+1].focus();
    else{if(prefix==="si")window.siVerifyOTP();else window.suVerifyOTP();}
  }else el.classList.remove("filled");
};
window.cellKey = function(event,idx,prefix){
  if(event.key==="Backspace"){
    const cells=document.querySelectorAll("#"+prefix+"-otp-row .otp-cell");
    if(!cells[idx].value&&idx>0){cells[idx-1].value="";cells[idx-1].classList.remove("filled");cells[idx-1].focus();}
  }
};
function getOTP(p){return[...document.querySelectorAll("#"+p+"-otp-row .otp-cell")].map(c=>c.value).join("");}
function clearOTP(p){document.querySelectorAll("#"+p+"-otp-row .otp-cell").forEach(c=>{c.value="";c.classList.remove("filled");});}

// Timer
const _timers={};
function startTimer(prefix,seconds){
  clearInterval(_timers[prefix]);
  document.getElementById(prefix+"-resend").classList.add("hidden");
  const el=document.getElementById(prefix+"-timer");
  let r=seconds; el.textContent="Resend in "+r+"s";
  _timers[prefix]=setInterval(()=>{
    r--;
    if(r<=0){clearInterval(_timers[prefix]);el.textContent="";document.getElementById(prefix+"-resend").classList.remove("hidden");}
    else el.textContent="Resend in "+r+"s";
  },1000);
}

// UI helpers
function showMsg(prefix,type,msg){
  ["error","success"].forEach(t=>{const e=document.getElementById(prefix+"-"+t);if(e)e.classList.add("hidden");});
  const el=document.getElementById(prefix+"-"+type);
  if(el){el.innerHTML=(type==="error"?"⚠️ ":"✅ ")+msg;el.classList.remove("hidden");}
}
function clearMsgs(p){["error","success"].forEach(t=>{const e=document.getElementById(p+"-"+t);if(e)e.classList.add("hidden");});}
function setBtnLoading(btnId,textId,loadId,loading){
  const btn=document.getElementById(btnId);if(btn)btn.disabled=loading;
  const txt=document.getElementById(textId);if(txt)txt.classList.toggle("hidden",loading);
  const ldr=document.getElementById(loadId);if(ldr)ldr.classList.toggle("hidden",!loading);
}
function friendlyError(err){
  const map={"auth/operation-not-allowed":"Google sign-in not enabled in Firebase Console.","auth/configuration-not-found":"Firebase not configured.","auth/popup-blocked":"Popup blocked — allow popups for this site.","auth/network-request-failed":"Network error. Check your connection."};
  return map[err.code]||err.message.replace("Firebase: ","").replace(/\s*\(auth\/[\w-]+\)\.?/,"");
}
