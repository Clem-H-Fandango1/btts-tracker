# Manual Match Entry - Quick Start Guide

## The Problem
ESPN's `/scoreboard` API doesn't return all Scottish League matches, even though they exist on ESPN's website.

## The Solution
Add matches manually through the API, then they'll appear in your dropdown and track live via ESPN!

## How to Add a Manual Match

### Option 1: Use curl (Command Line)

```bash
curl -X POST https://your-app.railway.app/api/manual_matches \
  -H "Content-Type: application/json" \
  -d '{
    "homeTeam": "Stirling Albion",
    "awayTeam": "Elgin City",
    "league": "sco.4",
    "kickoffTime": "Sat, November 22 at 3:00 PM UK"
  }'
```

### Option 2: Use Browser Console

1. Go to your admin page: `https://your-app.railway.app/admin`
2. Open browser console (F12)
3. Paste this code:

```javascript
fetch('/api/manual_matches', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    homeTeam: "Stirling Albion",
    awayTeam: "Elgin City",
    league: "sco.4",
    kickoffTime: "Sat, November 22 at 3:00 PM UK"
  })
})
.then(r => r.json())
.then(data => {
  console.log('Match added!', data);
  alert('Match added! Refresh the page.');
});
```

4. Press Enter
5. Refresh the admin page - the match will now appear in the dropdown!

### Option 3: Use Postman/Insomnia

1. POST to: `https://your-app.railway.app/api/manual_matches`
2. Body (JSON):
```json
{
  "homeTeam": "Stirling Albion",
  "awayTeam": "Elgin City",
  "league": "sco.4",
  "kickoffTime": "Sat, November 22 at 3:00 PM UK"
}
```

## Today's Missing Matches

Add these for today (November 22, 2025):

**Stirling Albion vs Elgin City:**
```json
{
  "homeTeam": "Stirling Albion",
  "awayTeam": "Elgin City",
  "league": "sco.4",
  "kickoffTime": "Sat, November 22 at 3:00 PM UK"
}
```

**Montrose vs East Fife:**
```json
{
  "homeTeam": "Montrose",
  "awayTeam": "East Fife",
  "league": "sco.3",
  "kickoffTime": "Sat, November 22 at 3:00 PM UK"
}
```

## View All Manual Matches

```bash
curl https://your-app.railway.app/api/manual_matches
```

Or visit in browser: `https://your-app.railway.app/api/manual_matches`

## Delete a Manual Match

```bash
curl -X DELETE https://your-app.railway.app/api/manual_matches/manual_1234567890
```

(Replace the event ID with the actual ID from the match list)

## League Codes

| League | Code |
|--------|------|
| Scottish Premiership | sco.1 |
| Scottish Championship | sco.2 |
| Scottish League One | sco.3 |
| Scottish League Two | sco.4 |
| Premier League | eng.1 |
| Championship | eng.2 |
| League One | eng.3 |
| League Two | eng.4 |

## Important Notes

1. **Manual matches persist** - they're stored in `manual_matches.json`
2. **They appear in the dropdown** alongside API matches
3. **Live scores still work** - ESPN's live score tracking works fine even if the match wasn't in the schedule
4. **Clean up old matches** - delete manual matches after match day

## Future Enhancement

We could add a proper UI form in the admin page to make this easier. For now, the browser console method works great!

## Troubleshooting

**Match not appearing?**
- Refresh the admin page
- Check the API response: visit `/api/matches` in your browser
- Verify the manual match was saved: visit `/api/manual_matches`

**Can't delete a match?**
- Get the event ID from `/api/manual_matches`
- Use the DELETE endpoint with the correct ID

**Live scores not updating?**
- Manual matches use the same live score system as API matches
- If ESPN has the match data, scores will update automatically
- Check the main page to see if scores are showing
