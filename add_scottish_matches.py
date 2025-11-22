#!/usr/bin/env python3
"""
Quick script to add Scottish League matches manually
Run this on match day to add missing fixtures
"""

import requests
import sys

# Your Railway app URL
APP_URL = "https://your-app.railway.app"  # CHANGE THIS!

# Today's Scottish League Two matches (22 Nov 2025)
MATCHES = [
    {
        "homeTeam": "Stirling Albion",
        "awayTeam": "Elgin City",
        "league": "sco.4",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    },
    {
        "homeTeam": "The Spartans",
        "awayTeam": "Stranraer",
        "league": "sco.4",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    },
    {
        "homeTeam": "Dumbarton",
        "awayTeam": "Forfar Athletic",
        "league": "sco.4",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    },
    {
        "homeTeam": "Clyde",
        "awayTeam": "Annan Athletic",
        "league": "sco.4",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    },
    {
        "homeTeam": "East Kilbride",
        "awayTeam": "Edinburgh City",
        "league": "sco.4",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    },
]

# Scottish League One matches
MATCHES.extend([
    {
        "homeTeam": "Montrose",
        "awayTeam": "East Fife",
        "league": "sco.3",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    },
])

def add_matches():
    """Add all matches to the app"""
    if "your-app" in APP_URL:
        print("ERROR: Please edit this script and set your Railway app URL!")
        print(f"Change APP_URL = '{APP_URL}' to your actual Railway URL")
        sys.exit(1)
    
    print(f"Adding {len(MATCHES)} matches to {APP_URL}...")
    
    for match in MATCHES:
        try:
            resp = requests.post(
                f"{APP_URL}/api/manual_matches",
                json=match,
                timeout=10
            )
            
            if resp.status_code == 200:
                print(f"✅ Added: {match['homeTeam']} vs {match['awayTeam']}")
            else:
                print(f"❌ Failed: {match['homeTeam']} vs {match['awayTeam']} - {resp.status_code}")
                print(f"   Response: {resp.text}")
        except Exception as e:
            print(f"❌ Error adding {match['homeTeam']} vs {match['awayTeam']}: {e}")
    
    print("\nDone! Refresh your admin page to see the matches.")

if __name__ == "__main__":
    add_matches()
