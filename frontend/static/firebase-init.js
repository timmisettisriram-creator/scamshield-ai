/**
 * Firebase JS SDK initialization — shared across all pages.
 * Uses your Firebase project: safe-fire-ai1
 */
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup,
         RecaptchaVerifier, signInWithPhoneNumber,
         onAuthStateChanged, signOut, getIdToken }
  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey:            "AIzaSyD0N0L34gKVtb2CZP7PgajTrd8VeuvROp0",
  authDomain:        "safe-fire-ai1.firebaseapp.com",
  projectId:         "safe-fire-ai1",
  storageBucket:     "safe-fire-ai1.firebasestorage.app",
  messagingSenderId: "311058590739",
  appId:             "1:311058590739:web:9dbfe613c6d1f962f623e6",
};

const firebaseApp  = initializeApp(firebaseConfig);
const firebaseAuth = getAuth(firebaseApp);
const firestoreDb  = getFirestore(firebaseApp);

// ── Get fresh ID token for API calls ──────────────────────────
async function getFirebaseToken() {
  const user = firebaseAuth.currentUser;
  if (!user) return null;
  return await getIdToken(user, /* forceRefresh */ false);
}

// ── Auth state listener ────────────────────────────────────────
function onAuthChange(callback) {
  return onAuthStateChanged(firebaseAuth, callback);
}

// ── Google Sign-In ─────────────────────────────────────────────
async function signInWithGoogle() {
  const provider = new GoogleAuthProvider();
  provider.addScope("email");
  provider.addScope("profile");
  const result = await signInWithPopup(firebaseAuth, provider);
  return result.user;
}

// ── Phone OTP ──────────────────────────────────────────────────
let _confirmationResult = null;

async function sendPhoneOTP(phoneNumber, recaptchaContainerId) {
  // phoneNumber must be in E.164 format: +919876543210
  const recaptchaVerifier = new RecaptchaVerifier(
    firebaseAuth,
    recaptchaContainerId,
    { size: "invisible" }
  );
  _confirmationResult = await signInWithPhoneNumber(
    firebaseAuth, phoneNumber, recaptchaVerifier
  );
  return _confirmationResult;
}

async function verifyPhoneOTP(otp) {
  if (!_confirmationResult) throw new Error("No OTP sent. Please request OTP first.");
  const result = await _confirmationResult.confirm(otp);
  return result.user;
}

// ── Sign out ───────────────────────────────────────────────────
async function firebaseSignOut() {
  await signOut(firebaseAuth);
  localStorage.removeItem("ss_token");
  localStorage.removeItem("ss_user");
}

export {
  firebaseApp, firebaseAuth, firestoreDb,
  getFirebaseToken, onAuthChange,
  signInWithGoogle, sendPhoneOTP, verifyPhoneOTP, firebaseSignOut,
};
