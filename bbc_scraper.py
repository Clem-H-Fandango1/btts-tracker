"""
BBC Sport scraper for Scottish football fixtures.
Uses robust text pattern matching to find fixtures on BBC Sport pages.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime


def scrape_bbc_fixtures(league_code):
    """
    Scrape BBC Sport fixtures for Scottish leagues using robust text pattern matching.
    
    Args:
        league_code: ESPN league code (e.g., 'sco.4' for Scottish League Two)
    
    Returns:
        List of fixture dictionaries with home_team, away_team, kickoff_time
    """
    # Map ESPN league codes to BBC URLs
    league_url_map = {
        'sco.4': 'https://www.bbc.com/sport/football/scottish-league-two/scores-fixtures',
        'sco.3': 'https://www.bbc.com/sport/football/scottish-league-one/scores-fixtures',
        'sco.2': 'https://www.bbc.com/sport/football/scottish-championship/scores-fixtures',
        'sco.1': 'https://www.bbc.com/sport/football/scottish-premiership/scores-fixtures'
    }
    
    url = league_url_map.get(league_code)
    if not url:
        return []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        fixtures = []
        seen_fixtures = set()
        
        # Strategy: Find all links that contain " v " (BBC's format for fixtures)
        # These are typically in <a> tags with fixture URLs
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            
            # BBC fixture links contain team names separated by " v "
            if ' v ' in link_text and '/football/' in href:
                try:
                    # Split on " v " to get team names
                    teams = link_text.split(' v ')
                    if len(teams) == 2:
                        home_team = teams[0].strip()
                        away_team = teams[1].strip()
                        
                        # Skip if team names are too short or look invalid
                        if len(home_team) < 3 or len(away_team) < 3:
                            continue
                        
                        # Skip if it contains numbers (likely a score, not a fixture)
                        if any(char.isdigit() for char in home_team) or any(char.isdigit() for char in away_team):
                            continue
                        
                        # Try to find kickoff time near this fixture
                        kickoff_time = "TBD"
                        
                        # Look for time element in parent or nearby elements
                        parent = link.parent
                        for _ in range(3):  # Check up to 3 levels up
                            if parent:
                                time_elem = parent.find('time')
                                if time_elem:
                                    time_text = time_elem.get_text(strip=True)
                                    if time_text:
                                        kickoff_time = time_text
                                        break
                                parent = parent.parent
                        
                        # Create unique key to avoid duplicates
                        fixture_key = f"{home_team}|{away_team}"
                        if fixture_key not in seen_fixtures:
                            seen_fixtures.add(fixture_key)
                            fixtures.append({
                                'home_team': home_team,
                                'away_team': away_team,
                                'kickoff_time': kickoff_time,
                                'league_code': league_code
                            })
                except Exception as e:
                    continue
        
        print(f"BBC Scraper: Found {len(fixtures)} fixtures for {league_code}")
        return fixtures
        
    except Exception as e:
        print(f"Error scraping BBC fixtures for {league_code}: {e}")
        return []


if __name__ == "__main__":
    # Test the scraper
    print("Testing BBC Scraper for Scottish League Two...")
    fixtures = scrape_bbc_fixtures('sco.4')
    
    if fixtures:
        print(f"\nFound {len(fixtures)} fixtures:")
        for i, fixture in enumerate(fixtures, 1):
            print(f"{i}. {fixture['home_team']} v {fixture['away_team']} - {fixture['kickoff_time']}")
    else:
        print("No fixtures found")
