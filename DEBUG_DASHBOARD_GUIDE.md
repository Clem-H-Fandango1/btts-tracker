# 🔍 BTTS App Debug Dashboard - Complete Guide

## What's New in v2.4.0

### Comprehensive `/debug` Dashboard

A beautiful, all-in-one debug page that shows you **everything** happening in your app:

- ✅ **ESPN API Status** - Is it working? How many matches found?
- ✅ **BBC Scraper Status** - Are Scottish matches being scraped?
- ✅ **Manual Matches** - What matches have been manually added?
- ✅ **Assignments** - Who has which matches assigned?
- ✅ **API Aggregator** - Combined view of all match sources
- ✅ **System Info** - Python version, environment variables, paths
- ✅ **Error Log** - All errors in one place with full stack traces

## How to Access

Simply visit:

```
https://your-app.railway.app/debug
```

**No password required!** The debug page is always accessible for troubleshooting.

## What You'll See

### 📊 Quick Overview Panel
- ESPN API status (✅/❌)
- BBC Scraper status (✅/❌/⚠️)
- Total matches available
- Manual matches count

### ⚽ ESPN API Section
- Connection status
- Test URL used
- HTTP status code
- Number of events found
- Any errors encountered

### 🏴󠁧󠁢󠁳󠁣󠁴󠁿 BBC Scraper Section
- Scraper status
- Test URL (Scottish League Two by default)
- Number of fixtures found
- Total links on the page
- Links containing " v " pattern
- Sample fixtures (first 5)
- Full error messages with stack traces

### 🔧 API Aggregator Section
- Status of the combined API system
- Total matches from all sources
- Breakdown by league
- Any aggregation errors

### 📝 Manual Matches Section
- File status (exists/not found)
- File path
- Total manual matches
- Full list of manual matches with details

### 👥 Assignments Section
- File status
- Total assignments made
- Full assignment mapping (friend → match)

### 💻 System Info Section
- Python version
- Platform (Linux/Windows/Mac)
- Current working directory
- Environment variables (passwords masked)

### 📄 Full Debug Data
- Complete JSON export of all debug info
- Copy/paste this to send for troubleshooting

## Why This Helps

### Problem: Stirling Albion not appearing?

Visit `/debug` and check:

1. **BBC Scraper section** → Are fixtures found? (should show 5+ fixtures)
2. **If 0 fixtures** → Look at "Links with ' v '" count
3. **API Aggregator** → Does it show matches for "sco.4"?
4. **Errors section** → Any red error boxes?

Send me a screenshot of the debug page and I can immediately see:
- Which component is failing
- What error is occurring
- What data is actually being found

### Problem: Matches not updating?

Check:
- ESPN API status (should be ✅)
- System Info → Environment variables set correctly?
- API Aggregator → How many matches total?

### Problem: Assignments not saving?

Check:
- Assignments section → File exists?
- View the actual assignments JSON
- Any file permission errors?

## Other Debug Endpoints

### `/debug/bbc/detailed`
Deep dive into BBC scraper specifically:
```
https://your-app.railway.app/debug/bbc/detailed?league=sco.4
```

Shows:
- Every link found on the BBC page
- Which links match the fixture pattern
- Sample HTML from the page
- Raw JSON output

### `/debug/bbc` (Original)
Basic BBC HTML structure check:
```
https://your-app.railway.app/debug/bbc?league=sco.4
```

## Troubleshooting Workflow

### Step 1: Visit `/debug`
See the overview - what's red? What's green?

### Step 2: Screenshot/Copy
- Take a screenshot of the full page
- Or copy the "Full Debug Data" JSON

### Step 3: Send for Analysis
Send the screenshot/JSON and describe the issue - I can pinpoint the problem immediately!

### Step 4: Targeted Fix
Based on the debug data, we can:
- Fix BBC scraper selectors
- Adjust API endpoints
- Fix file permissions
- Update environment variables

## Example Debug Scenarios

### Scenario 1: BBC Scraper Shows "0 fixtures found"

Debug page shows:
```
BBC Scraper Status: ⚠️ No fixtures found
Total Links: 821
Links with ' v ': 0
```

**Diagnosis:** BBC changed their fixture format!  
**Fix:** Update the scraper to look for new pattern (maybe "vs" instead of " v ")

### Scenario 2: ESPN API Shows "❌ Error 403"

Debug page shows:
```
ESPN API Status: ❌ Error 403
Status Code: 403
```

**Diagnosis:** ESPN blocked the request or rate limited  
**Fix:** Update user agent or add retry logic

### Scenario 3: Manual Matches Shows "File not found"

Debug page shows:
```
Manual Matches Status: ⚠️ File not found
File Path: /app/manual_matches.json
```

**Diagnosis:** File doesn't exist yet  
**Fix:** Add first manual match to create the file

## Security Note

The `/debug` endpoint does NOT expose:
- Actual passwords (shown as `***`)
- Telegram bot tokens (shown as `***`)
- Secret keys (shown as `***`)

It only shows:
- Whether these are set or not
- Public configuration data
- File paths (no sensitive content)

## Benefits

✅ **Instant diagnosis** - See all problems in one place  
✅ **No guessing** - Actual data and errors shown  
✅ **Easy sharing** - Screenshot and send  
✅ **Complete picture** - All components checked  
✅ **Beautiful UI** - Easy to read matrix-style theme  

## Tips

- **Bookmark the `/debug` URL** for quick access
- **Check it after every deploy** to verify everything works
- **Use it before asking for help** - you might solve it yourself!
- **Refresh the page** to see real-time status updates

---

**The debug dashboard makes troubleshooting 10x faster!**

No more guessing what's wrong - just visit `/debug` and see everything! 🚀
