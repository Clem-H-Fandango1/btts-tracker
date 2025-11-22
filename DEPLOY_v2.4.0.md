# 🚀 BTTS App v2.4.0 - Deployment Guide

## What's in This Version

✅ **Comprehensive `/debug` Dashboard**
- See all app components at once
- ESPN API status
- BBC Scraper with fixture counts
- Manual matches loaded
- Assignments status
- System info and errors

✅ **Enhanced BBC Scraper**
- Debug function included
- Better error reporting
- Sample fixture output

✅ **Better Troubleshooting**
- All errors logged in one place
- Full stack traces when things go wrong
- Easy to screenshot and share

## Deploy in 2 Steps

### Step 1: Upload to GitHub

**Method A - GitHub Web:**
1. Go to your GitHub repo
2. Delete all old files
3. Upload all files from `btts_app` folder
4. Commit changes

**Method B - Command Line:**
```bash
# Navigate to extracted folder
cd btts_app

# Initialize git (if needed)
git init
git add .
git commit -m "Add comprehensive debug dashboard - v2.4.0"

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/btts-tracker.git
git push -u origin main --force
```

### Step 2: Railway Deploys Automatically

- Railway detects the changes
- Rebuilds your app (2-3 minutes)
- App is live with new debug dashboard!

## First Thing to Do After Deploy

### Visit the Debug Dashboard

```
https://your-app.railway.app/debug
```

This will show you:
- ✅ What's working
- ❌ What's broken
- ⚠️ What needs attention

Take a screenshot and you'll immediately see if:
- ESPN API is working
- BBC scraper is finding fixtures
- Manual matches are loaded
- Everything is configured correctly

## Check If Stirling Albion Appears

1. **Go to debug page first:** `https://your-app.railway.app/debug`
2. **Look at BBC Scraper section:**
   - Should show "✅ OK" or "⚠️ No fixtures found"
   - Should list sample fixtures found
   - Should show links with " v " count

3. **If fixtures are found** → Go to `/admin` and check dropdown
4. **If 0 fixtures found** → Screenshot debug page and send to me

## Troubleshooting

### Everything Shows ✅ Green

Perfect! Your app is working correctly.

### ESPN API Shows ❌ Red

- ESPN might be down or rate limiting
- Check the error message in debug page
- Usually temporary - wait and refresh

### BBC Scraper Shows ⚠️ Warning

- Scraper works but found 0 fixtures
- BBC might have changed their HTML
- Look at "Links with ' v '" count
- Send debug screenshot for fix

### Manual Matches Shows "File not found"

- Normal if you haven't added any yet
- Add one match and the file will be created

## Quick Manual Add (While Debugging)

If you need Stirling Albion NOW:

1. Go to `/admin`
2. Press F12
3. Paste:

```javascript
fetch('/api/manual_matches', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    homeTeam: "Stirling Albion",
    awayTeam: "Elgin City",
    league: "sco.4",
    kickoffTime: "Sat, Nov 23 at 3:00 PM"
  })
}).then(() => location.reload());
```

Done! Match added permanently.

## Files Included

This package contains your complete BTTS app:

- `app.py` - Main application with new `/debug` endpoint
- `bbc_scraper.py` - Enhanced scraper with debug function
- `api_aggregator.py` - Multi-source match aggregation
- `templates/` - All HTML templates
- `static/` - CSS and JavaScript
- `Dockerfile` - Railway deployment config
- `requirements.txt` - Dependencies
- All data files and configs

## Version Info

**Previous:** v2.3.3-bbc-aggressive  
**Current:** v2.4.0-debug-dashboard  

**Changes:**
- Added comprehensive `/debug` dashboard
- Enhanced BBC scraper debugging
- Better error logging and reporting
- System info display
- All components checked in one view

## Getting Help

1. **Deploy this version**
2. **Visit `/debug`** 
3. **Screenshot the page**
4. **Send it to me** with your question

I'll see exactly what's happening and can fix it immediately!

## What's Next

After deploying:
- ✅ Visit `/debug` to verify everything works
- ✅ Check `/admin` to see if Scottish matches appear
- ✅ If issues remain, send debug screenshot
- ✅ I'll analyze and provide targeted fix

---

**The debug dashboard makes troubleshooting instant and easy!**

Deploy → Debug → Fix → Done! 🎯
