# Firebase Setup — ScamShield AI

Your Firebase project is already created: **safe-fire-ai1**

## Step 1: Enable Firebase Services (5 minutes)

Go to https://console.firebase.google.com → Select **safe-fire-ai1**

### Enable Authentication
1. Left menu → **Authentication** → **Get started**
2. **Sign-in method** tab → Enable:
   - **Google** → Enable → Add your email as support email → Save
   - **Phone** → Enable → Save

### Enable Firestore Database
1. Left menu → **Firestore Database** → **Create database**
2. Choose **Start in production mode** → Select region: **asia-south1 (Mumbai)** → Enable
3. Go to **Rules** tab → Replace with:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    match /scans/{scanId} {
      allow read: if request.auth != null && resource.data.user_id == request.auth.uid;
      allow create: if request.auth != null;
    }
    match /scam_reports/{reportId} {
      allow read: if true;
      allow create: if request.auth != null;
      allow update: if request.auth != null;
    }
    match /known_entities/{entityId} {
      allow read: if true;
      allow write: if false; // Only backend can write
    }
    match /newsletter/{email} {
      allow write: if true;
    }
    match /contacts/{id} {
      allow create: if true;
    }
    match /bookmarks/{id} {
      allow read, write: if request.auth != null && resource.data.user_id == request.auth.uid;
    }
    match /user_preferences/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```
4. Click **Publish**

## Step 2: Get Service Account Key (for backend)

1. Firebase Console → **Project Settings** (gear icon) → **Service accounts** tab
2. Click **Generate new private key** → **Generate key**
3. A JSON file downloads — open it
4. Copy the ENTIRE JSON content
5. Open `scamshield/.env` and paste it as the value of `FIREBASE_SERVICE_ACCOUNT`:
```
FIREBASE_SERVICE_ACCOUNT={"type":"service_account","project_id":"safe-fire-ai1",...}
```
(paste the entire JSON on one line)

OR save the file as `scamshield/backend/serviceAccountKey.json`

## Step 3: Enable Phone Auth for India

1. Firebase Console → Authentication → **Settings** tab
2. **Phone numbers for testing** → Add test numbers if needed
3. For production: Phone auth works automatically — Firebase handles SMS via their network

## Step 4: Add Authorized Domains

1. Firebase Console → Authentication → **Settings** → **Authorized domains**
2. Add your domains:
   - `localhost` (already there)
   - `your-app.onrender.com` (after deployment)
   - `yourdomain.com` (if custom domain)

## Step 5: Run Locally with Firebase

```bash
# Add your service account key to .env, then:
cd scamshield/backend
python -m uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/auth — sign in with Google or phone OTP

## Step 6: Deploy to Render with Firebase

In Render dashboard → Environment Variables, add:
- `FIREBASE_PROJECT_ID` = `safe-fire-ai1`
- `FIREBASE_SERVICE_ACCOUNT` = (paste the entire service account JSON)
- `ENVIRONMENT` = `production`
- `FRONTEND_URL` = `https://your-app.onrender.com`
- `ALLOWED_ORIGINS` = `https://your-app.onrender.com`

## What Firebase Gives You

- **Firestore** = Real-time NoSQL database (free: 1GB storage, 50K reads/day, 20K writes/day)
- **Authentication** = Google Sign-In + Phone OTP (free: unlimited users)
- **No server needed for auth** = Firebase JS SDK handles everything on frontend
- **Real-time updates** = Firestore listeners for live feed (future feature)
- **Automatic scaling** = Handles millions of users
