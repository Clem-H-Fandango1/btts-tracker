"""
Multi-API Aggregator for Football Match Data
Combines data from ESPN, TheSportsDB, and Football-Data.org
"""
import requests
from typing import List, Dict, Optional
import datetime
import os


# API Configuration
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")  # RapidAPI key


# League mappings between different APIs
LEAGUE_MAPPINGS = {
    # ESPN code -> (Football-Data code, TheSportsDB ID, API-Football ID)
    "sco.1": ("SC0", "4328", "179"),  # Scottish Premiership
    "sco.2": ("SC1", "4329", "180"),  # Scottish Championship  
    "sco.3": ("SC2", "4330", "181"),  # Scottish League One
    "sco.4": ("SC3", "4670", "182"),  # Scottish League Two
    "eng.1": ("PL", "4328", "39"),   # Premier League
    "eng.2": ("ELC", "4329", "40"),  # Championship
    "eng.3": ("EL1", "4396", "41"),  # League One
    "eng.4": ("EL2", "4397", "42"),  # League Two
}


def normalize_team_name(name: str) -> str:
    """Normalize team names for deduplication (lowercase, remove FC/AFC)"""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" fc", " afc", " united", " city", " town"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name


def fetch_from_espn(league_code: str, date_str: str) -> List[Dict]:
    """Fetch matches from ESPN API"""
    matches = []
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
    params = {"dates": date_str}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if not isinstance(data, dict) or "events" not in data:
            return matches
            
        for event in data.get("events", []):
            event_id = str(event.get("id"))
            competitions = event.get("competitions", [])
            if not competitions:
                continue
                
            comp = competitions[0]
            competitors = comp.get("competitors", [])
            if len(competitors) != 2:
                continue
                
            home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            
            home_team = home_comp.get("team", {}).get("displayName", "")
            away_team = away_comp.get("team", {}).get("displayName", "")
            status = event.get("status", {}).get("type", {}).get("detail", "Scheduled")
            
            matches.append({
                "eventId": f"espn_{event_id}",
                "source": "ESPN",
                "league": league_code,
                "homeTeam": home_team,
                "awayTeam": away_team,
                "homeTeamNorm": normalize_team_name(home_team),
                "awayTeamNorm": normalize_team_name(away_team),
                "status": status,
                "date": date_str
            })
    except Exception as e:
        print(f"ESPN API error for {league_code}: {e}")
        
    return matches


def fetch_from_thesportsdb(league_code: str, date_str: str) -> List[Dict]:
    """Fetch matches from TheSportsDB API (free tier)"""
    matches = []
    
    # Get TheSportsDB league ID from mapping
    if league_code not in LEAGUE_MAPPINGS:
        return matches
    
    _, thesportsdb_id, _ = LEAGUE_MAPPINGS[league_code]
    
    # TheSportsDB free API for events by date (limited)
    # Format date as YYYY-MM-DD
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    try:
        # Using the event search endpoint
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={formatted_date}&l={thesportsdb_id}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data and "events" in data and data["events"]:
            for event in data["events"]:
                if not event:  # Skip null events
                    continue
                    
                home_team = event.get("strHomeTeam", "")
                away_team = event.get("strAwayTeam", "")
                status = event.get("strStatus", "")
                
                matches.append({
                    "eventId": f"thesportsdb_{event.get('idEvent')}",
                    "source": "TheSportsDB",
                    "league": league_code,
                    "homeTeam": home_team,
                    "awayTeam": away_team,
                    "homeTeamNorm": normalize_team_name(home_team),
                    "awayTeamNorm": normalize_team_name(away_team),
                    "status": status,
                    "date": date_str
                })
    except Exception as e:
        print(f"TheSportsDB API error for {league_code}: {e}")
        
    return matches


def fetch_from_footballdata(league_code: str, date_str: str) -> List[Dict]:
    """Fetch matches from Football-Data.org API"""
    matches = []
    
    if not FOOTBALL_DATA_API_KEY:
        return matches  # Skip if no API key
        
    # Get Football-Data code from mapping
    if league_code not in LEAGUE_MAPPINGS:
        return matches
    
    fd_code, _, _ = LEAGUE_MAPPINGS[league_code]
    
    # Format date as YYYY-MM-DD
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    try:
        url = f"https://api.football-data.org/v4/competitions/{fd_code}/matches"
        headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
        params = {"dateFrom": formatted_date, "dateTo": formatted_date}
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        if resp.status_code != 200:
            return matches
            
        data = resp.json()
        
        if "matches" in data:
            for match in data["matches"]:
                home_team = match.get("homeTeam", {}).get("name", "")
                away_team = match.get("awayTeam", {}).get("name", "")
                status = match.get("status", "SCHEDULED")
                
                matches.append({
                    "eventId": f"footballdata_{match.get('id')}",
                    "source": "Football-Data",
                    "league": league_code,
                    "homeTeam": home_team,
                    "awayTeam": away_team,
                    "homeTeamNorm": normalize_team_name(home_team),
                    "awayTeamNorm": normalize_team_name(away_team),
                    "status": status,
                    "date": date_str
                })
    except Exception as e:
        print(f"Football-Data API error for {league_code}: {e}")
        
    return matches


def deduplicate_matches(matches: List[Dict]) -> List[Dict]:
    """
    Remove duplicate matches based on normalized team names and date.
    Prioritize sources in order: ESPN > Football-Data > TheSportsDB
    """
    seen = {}
    unique_matches = []
    
    # Sort by source priority
    source_priority = {"ESPN": 0, "Football-Data": 1, "TheSportsDB": 2}
    matches_sorted = sorted(matches, key=lambda x: source_priority.get(x["source"], 99))
    
    for match in matches_sorted:
        # Create unique key from normalized team names and date
        key = f"{match['homeTeamNorm']}_{match['awayTeamNorm']}_{match['date']}"
        
        if key not in seen:
            seen[key] = match
            unique_matches.append(match)
    
    return unique_matches


def fetch_all_matches(league_code: str, date_str: str) -> List[Dict]:
    """
    Aggregate matches from all available APIs for a given league and date.
    Returns deduplicated list of matches.
    """
    all_matches = []
    
    # Fetch from all sources
    all_matches.extend(fetch_from_espn(league_code, date_str))
    all_matches.extend(fetch_from_thesportsdb(league_code, date_str))
    all_matches.extend(fetch_from_footballdata(league_code, date_str))
    
    # Deduplicate
    unique_matches = deduplicate_matches(all_matches)
    
    return unique_matches


def convert_to_app_format(matches: List[Dict]) -> List[Dict]:
    """
    Convert aggregated match format to the app's expected format.
    """
    converted = []
    
    for match in matches:
        converted.append({
            "eventId": match["eventId"],
            "league": match["league"],
            "homeTeam": match["homeTeam"],
            "awayTeam": match["awayTeam"],
            "title": f"{match['homeTeam']} vs {match['awayTeam']}",
            "status": match["status"],
            "source": match.get("source", "Unknown")  # Keep track of source
        })
    
    return converted
