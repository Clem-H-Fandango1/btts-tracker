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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            print(f"BBC scrape failed for {league_code}: HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Debug: Save a snippet of the HTML to see structure
        print(f"BBC page title: {soup.title.string if soup.title else 'No title'}")
        print(f"BBC page has {len(soup.find_all())} total HTML elements")
        
        # BBC uses multiple possible structures - try all of them
        match_elements = []
        
        # Try method 1: Look for MatchProgressContainer (what the debug found!)
        match_elements = soup.find_all(class_=lambda x: x and 'MatchProgressContainer' in str(x))
        print(f"Method 1 (MatchProgressContainer): Found {len(match_elements)} elements")
        
        if not match_elements:
            # Try method 2: Look for elements containing match/fixture/event
            match_elements = soup.find_all(class_=lambda x: x and any(word in str(x).lower() for word in ['match', 'fixture', 'event']))
            print(f"Method 2 (generic match/fixture): Found {len(match_elements)} elements")
        
        if not match_elements:
            # Try method 3: article tags
            match_elements = soup.find_all('article')
            print(f"Method 3 (article tags): Found {len(match_elements)} elements")
        
        if not match_elements:
            # Try method 4: div with data-testid
            match_elements = soup.find_all(attrs={'data-testid': lambda x: x and 'match' in str(x).lower()})
            print(f"Method 4 (data-testid): Found {len(match_elements)} elements")
        
        if not match_elements:
            # Try method 5: Look for any element containing "vs" or "v" between text
            all_divs = soup.find_all(['div', 'li', 'article'])
            for div in all_divs:
                text = div.get_text(separator=' ', strip=True)
                if re.search(r'\w+\s+v\s+\w+', text, re.I):
                    match_elements.append(div)
            print(f"Method 5 (text pattern matching): Found {len(match_elements)} elements")
        
        print(f"BBC scraper found {len(match_elements)} potential match elements for {league_code}")
        
        for match_elem in match_elements:
            try:
                match_data = parse_bbc_match_element(match_elem, league_code)
                if match_data:
                    matches.append(match_data)
            except Exception as e:
                print(f"Error parsing match element: {e}")
                continue
        
        print(f"BBC scraper successfully parsed {len(matches)} matches for {league_code}")
        
    except Exception as e:
        print(f"BBC scrape error for {league_code}: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
    
    return matches


def parse_bbc_match_element(elem, league_code: str) -> Optional[Dict]:
    """Parse a single BBC match element into match data."""
    try:
        # BBC's current structure uses different approaches
        # Try multiple methods to extract team names
        
        home_team = None
        away_team = None
        home_score = 0
        away_score = 0
        status = "Scheduled"
        
        # Method 1: Look for team name spans/divs with specific classes
        team_elements = elem.find_all('span', class_=lambda x: x and 'team' in str(x).lower())
        if not team_elements:
            team_elements = elem.find_all('div', class_=lambda x: x and 'team' in str(x).lower())
        
        # Method 2: Look for abbr tags (BBC often uses these for team names)
        if not team_elements or len(team_elements) < 2:
            team_elements = elem.find_all('abbr', title=True)
        
        # Method 3: Look for elements with aria-label containing team names
        if not team_elements or len(team_elements) < 2:
            team_elements = elem.find_all(attrs={'aria-label': lambda x: x and 'v' in str(x).lower()})
        
        # Method 4: Just get all text and look for "X vs Y" pattern
        if not team_elements or len(team_elements) < 2:
            text = elem.get_text(separator=' | ', strip=True)
            import re
            vs_match = re.search(r'([A-Za-z\s]+)\s+v\s+([A-Za-z\s]+)', text, re.I)
            if vs_match:
                home_team = vs_match.group(1).strip()
                away_team = vs_match.group(2).strip()
        
        # Extract team names if we found team elements
        if not home_team and team_elements and len(team_elements) >= 2:
            home_team = team_elements[0].get('title') or team_elements[0].get_text(strip=True)
            away_team = team_elements[1].get('title') or team_elements[1].get_text(strip=True)
        
        if not home_team or not away_team:
            return None
        
        # Extract scores - look for score elements
        score_elements = elem.find_all(class_=lambda x: x and 'score' in str(x).lower())
        if score_elements and len(score_elements) >= 2:
            try:
                home_score = int(score_elements[0].get_text(strip=True))
                away_score = int(score_elements[1].get_text(strip=True))
                status = "In Progress"
            except:
                pass
        
        # Check for match status/time
        time_elem = elem.find(class_=lambda x: x and ('time' in str(x).lower() or 'period' in str(x).lower()))
        if time_elem:
            time_text = time_elem.get_text(strip=True)
            if time_text:
                status = time_text
                if "'" in time_text or 'min' in time_text.lower():
                    status = time_text  # Live minute
                elif 'ft' in time_text.lower() or 'full' in time_text.lower():
                    status = "FT"
                elif 'ht' in time_text.lower() or 'half' in time_text.lower():
                    status = "HT"
        
        # Check for postponed/cancelled
        if any(word in elem.get_text().lower() for word in ['postponed', 'cancelled', 'abandoned']):
            status = "Postponed"
        
        # Generate event ID
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
