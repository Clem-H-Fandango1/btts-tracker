"""
BBC Sport Scraper for Scottish Football Matches
Scrapes live scores and fixtures from BBC Sport
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from datetime import datetime


# BBC Sport Scottish football URLs
BBC_SCOTTISH_LEAGUES = {
    "sco.1": "https://www.bbc.com/sport/football/scottish-premiership/scores-fixtures",
    "sco.2": "https://www.bbc.com/sport/football/scottish-championship/scores-fixtures", 
    "sco.3": "https://www.bbc.com/sport/football/scottish-league-one/scores-fixtures",
    "sco.4": "https://www.bbc.com/sport/football/scottish-league-two/scores-fixtures",
}


def scrape_bbc_matches(league_code: str, date_str: str = None) -> List[Dict]:
    """
    Scrape matches from BBC Sport for a given league.
    
    Args:
        league_code: League code (e.g. "sco.4" for Scottish League Two)
        date_str: Date string in YYYYMMDD format (not used currently as BBC shows all upcoming)
    
    Returns:
        List of match dictionaries with: eventId, homeTeam, awayTeam, 
        homeScore, awayScore, status, league
    """
    if league_code not in BBC_SCOTTISH_LEAGUES:
        return []
    
    url = BBC_SCOTTISH_LEAGUES[league_code]
    matches = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            print(f"BBC scrape failed for {league_code}: HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all match containers
        # BBC uses different structures, try multiple selectors
        match_elements = soup.find_all('article', class_=re.compile('sp-c-fixture'))
        
        if not match_elements:
            # Try alternative structure
            match_elements = soup.find_all('div', class_=re.compile('fixture'))
        
        for match_elem in match_elements:
            try:
                match_data = parse_bbc_match_element(match_elem, league_code)
                if match_data:
                    matches.append(match_data)
            except Exception as e:
                print(f"Error parsing match element: {e}")
                continue
        
        print(f"BBC scraper found {len(matches)} matches for {league_code}")
        
    except Exception as e:
        print(f"BBC scrape error for {league_code}: {e}")
    
    return matches


def parse_bbc_match_element(elem, league_code: str) -> Optional[Dict]:
    """Parse a single BBC match element into match data."""
    try:
        # Extract team names
        home_team_elem = elem.find('span', class_=re.compile('team-home'))
        away_team_elem = elem.find('span', class_=re.compile('team-away'))
        
        if not home_team_elem or not away_team_elem:
            # Try alternative selectors
            teams = elem.find_all('span', class_=re.compile('team'))
            if len(teams) >= 2:
                home_team_elem = teams[0]
                away_team_elem = teams[1]
            else:
                return None
        
        home_team = home_team_elem.get_text(strip=True)
        away_team = away_team_elem.get_text(strip=True)
        
        # Extract scores
        score_elem = elem.find('span', class_=re.compile('score'))
        home_score = 0
        away_score = 0
        status = "Scheduled"
        
        if score_elem:
            score_text = score_elem.get_text(strip=True)
            # Format could be "2-1" or "2 - 1"
            score_match = re.search(r'(\d+)\s*-\s*(\d+)', score_text)
            if score_match:
                home_score = int(score_match.group(1))
                away_score = int(score_match.group(2))
                status = "In Progress"
        
        # Check if match is finished
        status_elem = elem.find('span', class_=re.compile('status'))
        if status_elem:
            status_text = status_elem.get_text(strip=True).lower()
            if 'ft' in status_text or 'full time' in status_text:
                status = "FT"
            elif 'ht' in status_text or 'half time' in status_text:
                status = "HT"
            elif any(word in status_text for word in ['live', 'min', "'"]):
                status = status_text  # Show the minute
        
        # Check for kickoff time
        time_elem = elem.find('span', class_=re.compile('time'))
        if time_elem and status == "Scheduled":
            kickoff = time_elem.get_text(strip=True)
            status = kickoff
        
        # Generate a pseudo event ID based on team names
        event_id = f"bbc_{league_code}_{home_team.replace(' ', '_')}_{away_team.replace(' ', '_')}"
        
        return {
            "eventId": event_id,
            "source": "BBC",
            "league": league_code,
            "homeTeam": home_team,
            "awayTeam": away_team,
            "homeScore": home_score,
            "awayScore": away_score,
            "status": status,
            "title": f"{home_team} vs {away_team}",
        }
        
    except Exception as e:
        print(f"Error parsing BBC match: {e}")
        return None


def get_bbc_live_score(home_team: str, away_team: str, league_code: str) -> Optional[Dict]:
    """
    Get live score for a specific match by team names.
    
    Args:
        home_team: Home team name
        away_team: Away team name
        league_code: League code
    
    Returns:
        Match data dict or None if not found
    """
    matches = scrape_bbc_matches(league_code)
    
    # Normalize team names for matching
    home_norm = home_team.lower().strip()
    away_norm = away_team.lower().strip()
    
    for match in matches:
        match_home = match["homeTeam"].lower().strip()
        match_away = match["awayTeam"].lower().strip()
        
        if home_norm in match_home and away_norm in match_away:
            return match
    
    return None


def scrape_all_scottish_matches() -> List[Dict]:
    """Scrape all Scottish league matches from BBC Sport."""
    all_matches = []
    
    for league_code in BBC_SCOTTISH_LEAGUES.keys():
        matches = scrape_bbc_matches(league_code)
        all_matches.extend(matches)
    
    return all_matches


# Test function
if __name__ == "__main__":
    print("Testing BBC Sport scraper...")
    print("\nScottish League Two matches:")
    matches = scrape_bbc_matches("sco.4")
    for match in matches:
        print(f"  {match['homeTeam']} vs {match['awayTeam']}")
        print(f"    Score: {match['homeScore']}-{match['awayScore']}")
        print(f"    Status: {match['status']}")
        print()
