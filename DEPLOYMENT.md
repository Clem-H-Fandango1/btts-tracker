# Railway Deployment Guide

## Step-by-Step Instructions

### 1. Prepare Your Code for GitHub

First, you need to get this code onto GitHub:

**Option A: Using GitHub Website (Easiest)**
1. Go to https://github.com and sign in (or create account)
2. Click the "+" icon → "New repository"
3. Name it `btts-tracker` (or whatever you like)
4. Make it **Private** if you want
5. Don't initialize with README (we already have files)
6. Click "Create repository"
7. Follow the instructions to upload files:
   - Download the prepared files I've created
   - Use the "uploading an existing file" option
   - Upload all files from the btts_tracker folder

**Option B: Using Git Command Line**
```bash
cd /path/to/btts_tracker
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/btts-tracker.git
git push -u origin main
```

### 2. Deploy to Railway

1. Go to https://railway.app
2. Sign up using your GitHub account (easiest)
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Authorize Railway to access your repositories
6. Select your `btts-tracker` repository
7. Railway will automatically detect the Dockerfile

### 3. Configure Environment Variables

Once deployment starts:

1. Click on your project
2. Go to the **Variables** tab
3. Add these variables:

```
ADMIN_PASSWORD=your_secure_password_here
ODDS_PASSWORD=your_odds_password_here
SECRET_KEY=some_random_long_string_here
```

**Optional Telegram variables (can configure later via web UI):**
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Get Your Public URL

1. Go to **Settings** tab
2. Click **"Generate Domain"**
3. Railway will give you a URL like: `btts-tracker-production.up.railway.app`
4. Your app will be live at this URL!

### 5. Initial Setup

Once deployed:

1. Visit `https://your-app.railway.app/admin`
2. Log in with your `ADMIN_PASSWORD`
3. Assign matches to your friends
4. Visit `https://your-app.railway.app/notify` to configure Telegram (if desired)
5. Share `https://your-app.railway.app/` with your mates to view!

## Telegram Bot Setup (Optional)

If you want notifications:

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Save the **bot token** you receive
4. Add your bot to your group chat
5. Get your chat ID:
   - Add [@userinfobot](https://t.me/userinfobot) to your group
   - It will show the group's chat ID
   - Remove it after
6. Enter these in the `/notify` page or as Railway environment variables

## Troubleshooting

**App won't start?**
- Check the logs in Railway's **Deployments** tab
- Make sure all environment variables are set

**Port issues?**
- Railway automatically sets the PORT variable
- The Dockerfile handles this

**Data not persisting?**
- Railway's free tier has ephemeral storage
- Data resets on redeployment
- For persistence, upgrade to Railway Pro with volumes

**Need to update the app?**
- Just push changes to GitHub
- Railway auto-deploys on every push to main branch

## Free Tier Limits

Railway free tier includes:
- $5 credit per month
- Should be plenty for this app
- Sleeps after inactivity (wakes on first request)
- No credit card required initially

## Support

If you run into issues, check:
- Railway logs in the Deployments tab
- GitHub repository is correctly connected
- Environment variables are set correctly
