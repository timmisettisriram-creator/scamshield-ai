# ScamShield AI — Launch Guide

## Step 1: Real Database (Supabase — Free, 5 minutes)

1. Go to **https://supabase.com** → Sign up free
2. Click **New Project** → name it `scamshield`
3. Set a strong database password → **Save it**
4. Wait ~2 minutes for project to provision
5. Go to **Settings → Database → Connection string → URI**
6. Copy the URI — it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ```
7. Open `scamshield/.env` and set:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ENVIRONMENT=production
   ```

## Step 2: Google OAuth (Free, 10 minutes)

1. Go to **https://console.cloud.google.com**
2. Create a new project → name it `ScamShield`
3. Go to **APIs & Services → OAuth consent screen**
   - User type: External → Fill in app name, email
4. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: Web application
   - Authorized redirect URIs: `https://your-app.onrender.com/auth/google/callback`
5. Copy Client ID and Client Secret → add to `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/google/callback
   ```

## Step 3: SMS OTP — Twilio (Free trial, 5 minutes)

1. Go to **https://twilio.com** → Sign up free (₹0, gives $15 credit)
2. Get your Account SID, Auth Token, and a phone number
3. Add to `.env`:
   ```
   TWILIO_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=your-auth-token
   TWILIO_PHONE=+1234567890
   ```

## Step 4: Deploy to Render (Free, 10 minutes)

1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "ScamShield AI v4.0"
   git remote add origin https://github.com/YOUR_USERNAME/scamshield-ai.git
   git push -u origin main
   ```

2. Go to **https://render.com** → Sign up free
3. Click **New → Web Service** → Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory:** `scamshield`
5. Add Environment Variables (from your `.env` file):
   - `DATABASE_URL` → your Supabase URL
   - `SECRET_KEY` → run `python -c "import secrets; print(secrets.token_hex(32))"`
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
   - `TWILIO_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE`
   - `ENVIRONMENT` → `production`
   - `FRONTEND_URL` → `https://your-app.onrender.com`
   - `ALLOWED_ORIGINS` → `https://your-app.onrender.com`
6. Click **Deploy** → Wait ~3 minutes

## Step 5: Custom Domain (Optional, ₹500-1000/year)

1. Buy a domain at **GoDaddy**, **Namecheap**, or **Google Domains**
   - Suggested: `scamshield.in` or `scamshieldai.in`
2. In Render → Settings → Custom Domains → Add your domain
3. Update DNS records as shown by Render
4. Update `FRONTEND_URL` and `GOOGLE_REDIRECT_URI` to your domain

## Step 6: Error Tracking — Sentry (Free)

1. Go to **https://sentry.io** → Sign up free
2. Create a Python project → Copy the DSN
3. Add to `.env`: `SENTRY_DSN=https://xxx@sentry.io/xxx`

---

## Local Development

```bash
cd scamshield/backend
python -m uvicorn main:app --reload --port 8000
```

Open: http://localhost:8000

## Production Checklist

- [ ] Supabase database connected
- [ ] Google OAuth configured
- [ ] Twilio SMS configured  
- [ ] SECRET_KEY set (strong random value)
- [ ] ENVIRONMENT=production
- [ ] ALLOWED_ORIGINS set to your domain
- [ ] Sentry DSN configured
- [ ] Custom domain configured
- [ ] SSL certificate active (Render provides free SSL)
