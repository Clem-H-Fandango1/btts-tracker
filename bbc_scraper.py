"""
BBC Sport scraper for Scottish football fixtures.
Enhanced version with comprehensive debugging capabilities.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime


# Map ESPN league codes to BBC URLs
BBC_SCOTTISH_LEAGUES = {
    'sco.4': 'https://www.bbc.com/sport/football/scottish-league-two/scores-fixtures',
    'sco.3': 'https://www.bbc.com/sport/football/scottish-league-one/scores-fixtures',
    'sco.2': 'https://www.bbc.com/sport/football/scottish-championship/scores-fixtures',
    'sco.1': 'https://www.bbc.com/sport/football/scottish-premiership/scores-fixtures'
}


def scrape_bbc_fixtures_debug(league_code):
    """
    Debug version that returns detailed information about what was found.
    Returns dict with 'fixtures' and 'debug' information.
    """
    url = BBC_SCOTTISH_LEAGUES.get(league_code)
    if not url:
        return {"error": "Invalid league code", "fixtures": [], "debug": {}}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug info
        debug_info = {
            "url": url,
            "status_code": response.status_code,
            "total_links": 0,
            "links_with_v": [],
            "links_with_vs": [],
            "fixtures_found": [],
            "sample_link_texts": []
        }
        
        all_links = soup.find_all('a', href=True)
        debug_info["total_links"] = len(all_links)
        
        fixtures = []
        seen_fixtures = set()
        
        # Collect sample link texts for debugging
        sample_count = 0
        for link in all_links:
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            
            if sample_count < 30 and link_text:  # First 30 non-empty links
                debug_info["sample_link_texts"].append({
                    "text": link_text,
                    "href": href[:100]  # First 100 chars of href
                })
                sample_count += 1
            
            # Check for " v " pattern
            if ' v ' in link_text:
                debug_info["links_with_v"].append({
                    "text": link_text,
                    "href": href[:100]
                })
            
            # Check for "vs" pattern
            if 'vs' in link_text.lower():
                debug_info["links_with_vs"].append({
                    "text": link_text,
                    "href": href[:100]
                })
            
            # Try to extract fixtures with " v "
            if ' v ' in link_text and '/football/' in href:
                try:
                    teams = link_text.split(' v ')
                    if len(teams) == 2:
                        home_team = teams[0].strip()
                        away_team = teams[1].strip()
                        
                        if len(home_team) >= 3 and len(away_team) >= 3:
                            if not any(char.isdigit() for char in home_team) and not any(char.isdigit() for char in away_team):
                                fixture_key = f"{home_team}|{away_team}"
                                if fixture_key not in seen_fixtures:
                                    seen_fixtures.add(fixture_key)
                                    
                                    kickoff_time = "TBD"
                                    parent = link.parent
                                    for _ in range(3):
                                        if parent:
                                            time_elem = parent.find('time')
                                            if time_elem:
                                                kickoff_time = time_elem.get_text(strip=True)
                                                break
                                            parent = parent.parent
                                    
                                    fixture = {
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'kickoff_time': kickoff_time,
                                        'league_code': league_code
                                    }
                                    fixtures.append(fixture)
                                    debug_info["fixtures_found"].append(fixture)
                except Exception as e:
                    continue
        
        debug_info["total_fixtures_extracted"] = len(fixtures)
        
        return {
            "fixtures": fixtures,
            "debug": debug_info
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "fixtures": [],
            "debug": {}
        }


def scrape_bbc_fixtures(league_code):
    """
    Main scraper function - returns just fixtures list.
    Uses robust text pattern matching to find fixtures on BBC Sport pages.
    
    Args:
        league_code: ESPN league code (e.g., 'sco.4' for Scottish League Two)
    
    Returns:
        List of fixture dictionaries with home_team, away_team, kickoff_time
    """
    result = scrape_bbc_fixtures_debug(league_code)
    fixtures = result.get("fixtures", [])
    
    print(f"BBC Scraper: Found {len(fixtures)} fixtures for {league_code}")
    if result.get("error"):
        print(f"BBC Scraper Error: {result['error']}")
    
    return fixtures


if __name__ == "__main__":
    print("Testing BBC Scraper for Scottish League Two...")
    result = scrape_bbc_fixtures_debug('sco.4')
    
    print(f"\nDebug Info:")
    print(f"Total links found: {result['debug'].get('total_links', 0)}")
    print(f"Links with ' v ': {len(result['debug'].get('links_with_v', []))}")
    print(f"Links with 'vs': {len(result['debug'].get('links_with_vs', []))}")
    print(f"Fixtures extracted: {result['debug'].get('total_fixtures_extracted', 0)}")
    
    if result['fixtures']:
        print("\nFixtures Found:")
        for f in result['fixtures']:
            print(f"  {f['home_team']} v {f['away_team']} - {f['kickoff_time']}")
    else:
        print("\nNo fixtures found!")
        if result.get('error'):
            print(f"Error: {result['error']}")
        else:
            print("\nSample links from page:")
            for sample in result['debug'].get('sample_link_texts', [])[:10]:
                print(f"  '{sample['text']}'")

