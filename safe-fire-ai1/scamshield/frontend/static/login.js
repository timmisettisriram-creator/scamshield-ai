const API = 'http://localhost:8000';
let currentPhone = '';
let resendInterval = null;

// ── Google Login ───────────────────────────────────────────────
function loginWithGoogle() {
  window.location.href = `${API}/auth/google`;
}

// ── Send OTP ───────────────────────────────────────────────────
async function sendOTP() {
  const phone = document.getElementById('phone-input').value.trim();
  if (phone.length !== 10) {
    showError('Enter a valid 10-digit mobile number.');
    return;
  }

  setBtnLoading('send-otp-btn', 'send-btn-text', 'send-btn-loader', true);
  hideMessages();

  try {
    const res = await fetch(`${API}/auth/otp/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to send OTP');

    currentPhone = phone;

    // Show OTP step
    document.getElementById('step-phone').classList.add('hidden');
    document.getElementById('step-otp').classList.remove('hidden');

    // Dev mode — show OTP hint
    const msg = data.dev_otp
      ? `OTP sent! [DEV MODE — OTP: ${data.dev_otp}]`
      : `OTP sent to +91 ${phone}. Valid for 5 minutes.`;
    document.getElementById('otp-sent-msg').textContent = msg;

    // Focus first box
    document.querySelectorAll('.otp-box')[0].focus();
    startResendTimer(30);

  } catch (err) {
    showError(err.message);
  } finally {
    setBtnLoading('send-otp-btn', 'send-btn-text', 'send-btn-loader', false);
  }
}

// ── OTP box navigation ─────────────────────────────────────────
function otpInput(el, idx) {
  el.value = el.value.replace(/\D/g, '');
  if (el.value) {
    el.classList.add('filled');
    const boxes = document.querySelectorAll('.otp-box');
    if (idx < 5) boxes[idx + 1].focus();
    else verifyOTP(); // auto-submit on last digit
  } else {
    el.classList.remove('filled');
  }
}

function otpKey(event, idx) {
  if (event.key === 'Backspace') {
    const boxes = document.querySelectorAll('.otp-box');
    if (!boxes[idx].value && idx > 0) {
      boxes[idx - 1].value = '';
      boxes[idx - 1].classList.remove('filled');
      boxes[idx - 1].focus();
    }
  }
}

function getOTPValue() {
  return [...document.querySelectorAll('.otp-box')].map(b => b.value).join('');
}

// ── Verify OTP ─────────────────────────────────────────────────
async function verifyOTP() {
  const otp = getOTPValue();
  if (otp.length !== 6) { showError('Enter the complete 6-digit OTP.'); return; }

  setBtnLoading('verify-btn', 'verify-btn-text', 'verify-btn-loader', true);
  hideMessages();

  try {
    const res = await fetch(`${API}/auth/otp/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: currentPhone, otp }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Verification failed');

    // Save token and redirect
    localStorage.setItem('ss_token', data.token);
    localStorage.setItem('ss_user', JSON.stringify(data.user));

    showSuccess('Verified! Redirecting...');
    setTimeout(() => { window.location.href = '/'; }, 1000);

  } catch (err) {
    showError(err.message);
    // Shake OTP boxes
    document.getElementById('otp-boxes').style.animation = 'shake .4s ease';
    setTimeout(() => document.getElementById('otp-boxes').style.animation = '', 400);
  } finally {
    setBtnLoading('verify-btn', 'verify-btn-text', 'verify-btn-loader', false);
  }
}

// ── Resend timer ───────────────────────────────────────────────
function startResendTimer(seconds) {
  clearInterval(resendInterval);
  document.getElementById('resend-btn').classList.add('hidden');
  const timerEl = document.getElementById('resend-timer');
  let remaining = seconds;
  timerEl.textContent = `Resend in ${remaining}s`;
  resendInterval = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(resendInterval);
      timerEl.textContent = '';
      document.getElementById('resend-btn').classList.remove('hidden');
    } else {
      timerEl.textContent = `Resend in ${remaining}s`;
    }
  }, 1000);
}

async function resendOTP() {
  document.getElementById('phone-input').value = currentPhone;
  document.getElementById('step-otp').classList.add('hidden');
  document.getElementById('step-phone').classList.remove('hidden');
  document.querySelectorAll('.otp-box').forEach(b => { b.value = ''; b.classList.remove('filled'); });
  await sendOTP();
}

function goBack() {
  document.getElementById('step-otp').classList.add('hidden');
  document.getElementById('step-phone').classList.remove('hidden');
  document.querySelectorAll('.otp-box').forEach(b => { b.value = ''; b.classList.remove('filled'); });
  clearInterval(resendInterval);
  hideMessages();
}

// ── Helpers ────────────────────────────────────────────────────
function showError(msg) {
  const el = document.getElementById('auth-error');
  el.textContent = '⚠️ ' + msg;
  el.classList.remove('hidden');
  document.getElementById('auth-success').classList.add('hidden');
}

function showSuccess(msg) {
  const el = document.getElementById('auth-success');
  el.textContent = '✅ ' + msg;
  el.classList.remove('hidden');
  document.getElementById('auth-error').classList.add('hidden');
}

function hideMessages() {
  document.getElementById('auth-error').classList.add('hidden');
  document.getElementById('auth-success').classList.add('hidden');
}

function setBtnLoading(btnId, textId, loaderId, loading) {
  document.getElementById(btnId).disabled = loading;
  document.getElementById(textId).classList.toggle('hidden', loading);
  document.getElementById(loaderId).classList.toggle('hidden', !loading);
}

// ── Handle Google token redirect ───────────────────────────────
const urlParams = new URLSearchParams(window.location.search);
const tokenFromGoogle = urlParams.get('token');
if (tokenFromGoogle) {
  localStorage.setItem('ss_token', tokenFromGoogle);
  window.location.href = '/';
}

// ── If already logged in, skip login page ─────────────────────
if (localStorage.getItem('ss_token') && !tokenFromGoogle) {
  window.location.href = '/';
}
