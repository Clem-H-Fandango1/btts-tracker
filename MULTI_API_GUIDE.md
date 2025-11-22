# Multi-API Integration Guide

## Overview
This upgrade allows your BTTS app to fetch matches from multiple sources:
- ESPN (primary, no API key needed)
- TheSportsDB (free, no API key for basic features)
- Football-Data.org (free tier, requires API key)

This ensures Scottish League One and Two matches appear even when ESPN doesn't have them.

## Setup Steps

### 1. Get API Keys (Optional but Recommended)

**Football-Data.org (Recommended):**
1. Go to https://www.football-data.org/client/register
2. Sign up for free account
3. Get your API key from your profile
4. Add to Railway environment variables: `FOOTBALL_DATA_API_KEY=your_key_here`

**API-Football (Optional - for future expansion):**
1. Go to https://rapidapi.com/api-sports/api/api-football
2. Subscribe to free tier (100 requests/day)
3. Get your RapidAPI key
4. Add to Railway: `API_FOOTBALL_KEY=your_key_here`

### 2. Update app.py

Replace the `api_matches` endpoint (around line 523) with this:

```python
@app.route("/api/matches")
def api_matches():
    """Return a JSON list of matches from multiple APIs"""
    from api_aggregator import fetch_all_matches, convert_to_app_format
    
    date_str = request.args.get("date")
    if date_str is None:
        date_str = get_today_date_str()
    
    all_events: List[dict] = []
    
    # Fetch from all configured leagues using multi-API aggregator
    for league in LEAGUE_CODES:
        try:
            # Use aggregator to fetch from multiple sources
            matches = fetch_all_matches(league, date_str)
            converted = convert_to_app_format(matches)
            all_events.extend(converted)
        except Exception as e:
            # Fallback to ESPN only if aggregator fails
            scoreboard = fetch_scoreboard(league, date_str)
            if scoreboard:
                events = parse_events_from_scoreboard(scoreboard, league)
                all_events.extend(events)
    
    # Sort events by title
    all_events.sort(key=lambda e: e["title"])
    return jsonify(all_events)
```

### 3. Update requirements.txt

No changes needed! All APIs use the `requests` library which is already installed.

### 4. Deploy to Railway

1. Upload both files to your GitHub repo:
   - `app.py` (with the modified endpoint)
   - `api_aggregator.py` (new file)

2. In Railway, add environment variable (if you got the key):
   ```
   FOOTBALL_DATA_API_KEY=your_key_here
   ```

3. Railway will auto-deploy

4. Test by visiting `/api/matches` - you should now see Scottish League matches!

## How It Works

### Match Fetching Flow:
1. App requests matches for a specific date
2. For each league:
   - Try ESPN API first (fastest, no auth)
   - Try TheSportsDB (good for Scottish leagues)
   - Try Football-Data.org (if API key available)
3. Deduplicate matches (same match from multiple sources)
4. Return combined list

### Deduplication:
Matches are considered duplicates if they have:
- Same home team (normalized: "Stirling Albion FC" → "stirling albion")
- Same away team (normalized)
- Same date

Priority: ESPN > Football-Data > TheSportsDB

### Source Tracking:
Each match includes a "source" field so you can see which API provided it.

## Testing

Test that it works:

```bash
# Test locally
python3 -c "
from api_aggregator import fetch_all_matches, convert_to_app_format
matches = fetch_all_matches('sco.4', '20251122')
print(f'Found {len(matches)} matches')
for m in matches:
    print(f'{m[\"homeTeam\"]} vs {m[\"awayTeam\"]} (Source: {m[\"source\"]})')
"
```

## Troubleshooting

**Problem: Still not seeing Scottish matches**
- Check Railway logs for API errors
- Verify FOOTBALL_DATA_API_KEY is set correctly
- TheSportsDB is rate-limited (30 requests/min on free tier)

**Problem: Duplicate matches appearing**
- This shouldn't happen due to deduplication
- Check the logs - might be slight team name variations
- Can adjust `normalize_team_name()` function

**Problem: Slow loading**
- Multiple API calls take longer than single ESPN
- Consider caching results for 1-2 minutes
- Or only call backup APIs if ESPN returns no results

## Future Enhancements

1. **Smart fallback:** Only call backup APIs if ESPN returns 0 results
2. **Caching:** Cache API results for 2-5 minutes to reduce calls
3. **Live scores:** Add API-Football integration for real-time score updates
4. **Admin panel:** Show which API provided each match

## API Limits Summary

| API | Free Tier Limit | Need API Key? | Scottish Coverage |
|-----|----------------|---------------|-------------------|
| ESPN | Unlimited | No | ❌ Poor |
| TheSportsDB | 30/min | No | ✅ Good |
| Football-Data | 10/min | Yes (free) | ✅ Excellent |
| API-Football | 100/day | Yes (free) | ✅ Excellent |

For your use case (checking matches ~3 times per day):
- **Without any API keys:** ESPN + TheSportsDB = Good coverage
- **With Football-Data key:** Excellent coverage, very reliable
- **With API-Football key:** Best coverage, includes live scores
