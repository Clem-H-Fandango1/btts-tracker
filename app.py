import datetime
import json
import os

import pytz
from flask import Flask, jsonify, render_template, request, session, redirect
# Application version string.  Incremented when new features are added.
APP_VERSION = "v2.3.1-bbc-debug"
import requests
from typing import Dict, List, Optional


app = Flask(__name__, static_folder="static", template_folder="templates")

# Secret key for session management (e.g. admin login).  In a production
# deployment, this should be set via an environment variable and kept
# secret.  A default is provided here for convenience.
app.secret_key = os.environ.get("SECRET_KEY", "bttssecretkey")

# Admin password for login.  This should also be set via an environment
# variable in production.  The default can be overridden by setting
# ADMIN_PASSWORD when running the container or application.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Password for accessing the BTTS odds page.  This is separate from the
# administrator password to allow sharing predictions without granting
# administrative privileges.  In production, override via the
# ODDS_PASSWORD environment variable.  A sensible default is provided
# for development and testing.
ODDS_PASSWORD = os.environ.get("ODDS_PASSWORD", "odds123")

# Location of the results file.  This JSON file stores completed match
# results across all configured leagues.  Each entry contains
# date, league, homeTeam, awayTeam, homeScore, awayScore and eventId.
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "results.json")

# Names of the participants used throughout the application.  The order
# determines how assignments are stored and displayed on the front-end.
FRIEND_NAMES: List[str] = [
    "Kenz",
    "Tartz",
    "Coypoo",
    "Ginger",
    "Kooks",
    "Doxy",
]

# Location of the assignments file.  This JSON file will store a
# dictionary mapping each friend name to an event ID (string) or null
# if no assignment has been made.  The file is created on demand.
ASSIGNMENTS_FILE = os.path.join(os.path.dirname(__file__), "assignments.json")

# Location of the group assignments file.  This JSON file will store a
# mapping of each friend to either "top" or "bottom" to determine
# whether they participate in the top bet or the bottom bet.  If the
# file does not exist, a default split (first half top, second half
# bottom) is applied.
GROUPS_FILE = os.path.join(os.path.dirname(__file__), "groups.json")

# Location of the site settings file.  This JSON file stores global
# settings such as the site title and the "any other business" message.
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

# Location of the manual matches file.  This JSON file stores matches that
# have been manually added (typically because they don't appear in API feeds).
# Each entry contains: eventId, homeTeam, awayTeam, league, kickoffTime.
MANUAL_MATCHES_FILE = os.path.join(os.path.dirname(__file__), "manual_matches.json")

# List of ESPN league codes for UK competitions.  These correspond to
# the top four tiers of English football and the top four Scottish
# divisions.  Additional codes can be added here as needed (e.g.
# domestic cups or other European leagues) but are intentionally
# limited to avoid cluttering the match list with too many fixtures.
LEAGUE_CODES: List[str] = [
    # English leagues
    "eng.1",  # Premier League
    "eng.2",  # Championship
    "eng.3",  # League One
    "eng.4",  # League Two
    "eng.5",  # National League
    "eng.6",  # National League North
    "eng.7",  # National League South
    # Scottish leagues
    "sco.1",  # Scottish Premiership
    "sco.2",  # Scottish Championship
    "sco.3",  # Scottish League One
    "sco.4",  # Scottish League Two
    # Welsh league
    "wal.1",  # Cymru Premier
    # Domestic cups
    "eng.fa",         # FA Cup
    "eng.faq",        # FA Cup Qualifying
    "eng.league_cup", # EFL Cup / Carabao Cup
    "eng.charity",    # FA Community Shield
    "eng.trophy",     # EFL Trophy
    "sco.tennents",   # Scottish Cup
    "sco.cis",        # Scottish League Cup
    "sco.challenge",  # Scottish Challenge Cup
    # European competitions
    "uefa.champions",        # UEFA Champions League
    "uefa.champions_qual",   # Champions League Qualifying
    "uefa.europa",           # UEFA Europa League
    "uefa.europa_qual",      # Europa League Qualifying
    "uefa.europa.conf",      # UEFA Conference League
    "uefa.europa.conf_qual", # Conference League Qualifying
    "uefa.super_cup",        # UEFA Super Cup
]

# -----------------------------
# Settings Loading and Saving
# -----------------------------

def load_settings() -> Dict[str, str]:
    """Load global settings from disk.

    In addition to the title and message shown on the main page,
    this function also loads Telegram notification settings.  Keys
    include:

        - title:  site title
        - message:  site-wide message banner
        - telegram_enabled: bool indicating whether Telegram alerts are sent
        - telegram_bot_token: API token for the Telegram bot
        - telegram_chat_id: chat/channel ID where notifications are sent
        - poll_seconds: interval between poll cycles in seconds

    If the settings file does not exist or is malformed, sensible
    defaults are returned.  These defaults come from DEFAULT_TELEGRAM
    and fall back to environment variables where appropriate.
    """
    defaults = {
        "title": "BTTS Match Tracker",
        "message": "",
        "telegram_enabled": DEFAULT_TELEGRAM.get("telegram_enabled", True),
        "telegram_bot_token": DEFAULT_TELEGRAM.get("telegram_bot_token", ""),
        "telegram_chat_id": DEFAULT_TELEGRAM.get("telegram_chat_id", ""),
        "poll_seconds": DEFAULT_TELEGRAM.get("poll_seconds", 30),
    }
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    merged = defaults.copy()
    for key, value in data.items():
        if value not in (None, ""):
            merged[key] = value
    return merged


# -----------------------------
# Results Database
# -----------------------------

def load_results() -> List[dict]:
    """Load historical match results from disk.

    Returns a list of dictionaries, each representing a finished match.
    The file is created on demand if it does not exist or is invalid.
    """
    try:
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_results(results: List[dict]) -> None:
    """Persist the list of match results to disk."""
    try:
        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f)
    except Exception:
        # Log failures silently; the caller can handle errors
        pass


def update_results(days_back: int = 7) -> None:
    """Update the results database with completed matches from recent days.

    This function iterates backwards in time for ``days_back`` days and
    fetches scoreboards for each configured league.  For each event
    that has finished (state != "pre"), the final scores are recorded
    into the results database.  Events already present in the database
    (matched by event ID) are skipped to avoid duplicate entries.

    Args:
        days_back: How many days in the past to check.  Defaults to 7.
    """
    results = load_results()
    existing_ids = {str(item.get("eventId")) for item in results if item.get("eventId")}
    tz = pytz.timezone("Europe/London")
    today = datetime.datetime.now(tz)
    # Iterate over each day in the past
    for delta in range(1, days_back + 1):
        date = today - datetime.timedelta(days=delta)
        date_str = date.strftime("%Y%m%d")
        for league in LEAGUE_CODES:
            scoreboard = fetch_scoreboard(league, date_str)
            if not scoreboard:
                continue
            for event in scoreboard.get("events", []):
                event_id = str(event.get("id"))
                # Skip if we've already stored this event
                if event_id in existing_ids:
                    continue
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                if len(competitors) != 2:
                    continue
                home_comp = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away_comp = next((c for c in competitors if c.get("homeAway") == "away"), None)
                if not home_comp or not away_comp:
                    home_comp, away_comp = competitors[0], competitors[1]
                home_score = int(home_comp.get("score", 0)) if home_comp.get("score") else 0
                away_score = int(away_comp.get("score", 0)) if away_comp.get("score") else 0
                # Determine if the match has been played.  Skip scheduled/pre matches.
                state = event.get("status", {}).get("type", {}).get("state", "")
                if state == "pre":
                    continue
                results.append({
                    "eventId": event_id,
                    "date": date_str,
                    "league": league,
                    "homeTeam": home_comp.get("team", {}).get("displayName", ""),
                    "awayTeam": away_comp.get("team", {}).get("displayName", ""),
                    "homeScore": home_score,
                    "awayScore": away_score,
                })
                existing_ids.add(event_id)
    save_results(results)


def compute_btts_predictions(results: List[dict], upcoming_events: List[dict]) -> List[dict]:
    """Compute predicted probabilities for both teams to score for upcoming matches.

    The probability for a match is estimated by multiplying the home team's
    proportion of home games in which they have scored by the away team's
    proportion of away games in which they have scored.  If no historical
    data exists for a team (e.g. new team or no matching records), a
    default probability of 0.5 is used for that team.

    Args:
        results: List of historical match results.
        upcoming_events: List of upcoming events as returned by
            :func:`parse_events_from_scoreboard`.

    Returns:
        A list of dictionaries with keys: eventId, league, homeTeam,
        awayTeam and probability, sorted descending by probability.
    """
    # Build per-team statistics for scoring at home/away
    team_stats: Dict[str, Dict[str, int]] = {}
    for r in results:
        home = r.get("homeTeam") or ""
        away = r.get("awayTeam") or ""
        # Initialise stats entries
        team_stats.setdefault(home, {"home_games": 0, "home_scored": 0, "away_games": 0, "away_scored": 0})
        team_stats.setdefault(away, {"home_games": 0, "home_scored": 0, "away_games": 0, "away_scored": 0})
        # Update home team stats
        team_stats[home]["home_games"] += 1
        if r.get("homeScore", 0) and int(r["homeScore"]) > 0:
            team_stats[home]["home_scored"] += 1
        # Update away team stats
        team_stats[away]["away_games"] += 1
        if r.get("awayScore", 0) and int(r["awayScore"]) > 0:
            team_stats[away]["away_scored"] += 1
    predictions: List[dict] = []
    for event in upcoming_events:
        home = event.get("homeTeam", "")
        away = event.get("awayTeam", "")
        # Home scoring probability
        h_stats = team_stats.get(home)
        if h_stats and h_stats["home_games"] > 0:
            p_home = h_stats["home_scored"] / float(h_stats["home_games"])
        else:
            p_home = 0.5
        # Away scoring probability
        a_stats = team_stats.get(away)
        if a_stats and a_stats["away_games"] > 0:
            p_away = a_stats["away_scored"] / float(a_stats["away_games"])
        else:
            p_away = 0.5
        prob = p_home * p_away
        predictions.append({
            "eventId": event.get("eventId"),
            "league": event.get("league"),
            "homeTeam": home,
            "awayTeam": away,
            "probability": prob,
        })
    # Sort descending by probability
    predictions.sort(key=lambda x: x.get("probability", 0), reverse=True)
    return predictions


def save_settings(settings: Dict[str, str]) -> None:
    """Persist global settings to disk.

    In addition to the title and message, this function persists
    Telegram configuration.  Only recognised keys are saved; other
    keys are ignored to avoid storing unexpected data.  Missing keys
    will revert to defaults on the next load.
    """
    allowed_keys = {
        "title",
        "message",
        "telegram_enabled",
        "telegram_bot_token",
        "telegram_chat_id",
        "poll_seconds",
    }
    to_save: Dict[str, str] = {}
    for key in allowed_keys:
        val = settings.get(key)
        if val not in (None, ""):
            to_save[key] = val
    with open(SETTINGS_FILE, "w") as f:
        json.dump(to_save, f)


def load_manual_matches() -> List[dict]:
    """Load manually added matches from disk.
    
    Returns a list of match dictionaries with keys: eventId, homeTeam,
    awayTeam, league, kickoffTime, title, status.
    """
    try:
        with open(MANUAL_MATCHES_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_manual_matches(matches: List[dict]) -> None:
    """Persist manually added matches to disk."""
    try:
        with open(MANUAL_MATCHES_FILE, "w") as f:
            json.dump(matches, f, indent=2)
    except Exception as e:
        print(f"Error saving manual matches: {e}")


def add_manual_match(home_team: str, away_team: str, league: str, kickoff_time: str) -> str:
    """Add a new manual match and return its generated event ID.
    
    Args:
        home_team: Home team name
        away_team: Away team name  
        league: League code (e.g. "sco.4")
        kickoff_time: Kickoff time string (e.g. "Sat, November 22 at 3:00 PM UK")
        
    Returns:
        The generated event ID for this match
    """
    matches = load_manual_matches()
    
    # Generate a unique manual event ID
    import time
    event_id = f"manual_{int(time.time())}"
    
    new_match = {
        "eventId": event_id,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "league": league,
        "kickoffTime": kickoff_time,
        "title": f"{home_team} vs {away_team}",
        "status": kickoff_time,
        "source": "manual"
    }
    
    matches.append(new_match)
    save_manual_matches(matches)
    
    # Add to event league map
    event_league_map[event_id] = league
    
    return event_id


def remove_manual_match(event_id: str) -> bool:
    """Remove a manual match by its event ID.
    
    Returns True if match was found and removed, False otherwise.
    """
    matches = load_manual_matches()
    original_len = len(matches)
    matches = [m for m in matches if m.get("eventId") != event_id]
    
    if len(matches) < original_len:
        save_manual_matches(matches)
        return True
    return False


# In-memory cache mapping event IDs to their corresponding league code.
# This allows the API to look up the correct league when retrieving
# detailed information for a specific match.
event_league_map: Dict[str, str] = {}


def get_today_date_str(timezone: str = "Europe/London") -> str:
    """Return today's date in the given timezone formatted as YYYYMMDD.

    The ESPN API uses dates without dashes (YYYYMMDD).  A timezone is
    supplied because the API expects the date relative to local time in
    the user's locale (Europe/London for this project).
    """
    tz = pytz.timezone(timezone)
    now = datetime.datetime.now(tz)
    return now.strftime("%Y%m%d")


def load_assignments() -> Dict[str, Optional[str]]:
    """Load the current match assignments from the JSON file.

    Returns a dictionary mapping each friend name to an event ID (string)
    or None if no assignment has been made.  If the file does not exist
    or is invalid, a fresh mapping with all values set to None is
    returned.  Additional names not present in FRIEND_NAMES are ignored.
    """
    try:
        with open(ASSIGNMENTS_FILE, "r") as f:
            data = json.load(f)
        # Ensure that we only include the expected names
        assignments = {name: data.get(name) for name in FRIEND_NAMES}
    except Exception:
        assignments = {name: None for name in FRIEND_NAMES}
    return assignments


def save_assignments(assignments: Dict[str, Optional[str]]) -> None:
    """Persist the assignments to the JSON file.

    The function writes the provided mapping to disk.  Only keys
    corresponding to FRIEND_NAMES are stored.  Other keys are ignored.
    """
    data = {name: assignments.get(name) for name in FRIEND_NAMES}
    with open(ASSIGNMENTS_FILE, "w") as f:
        json.dump(data, f)


def load_groups() -> Dict[str, str]:
    """Load the current group assignments from the JSON file.

    Returns a dictionary mapping each friend name to either "top" or
    "bottom".  If the file does not exist or is invalid, a default
    assignment is generated where the first half of FRIEND_NAMES are
    "top" and the remainder are "bottom".
    """
    try:
        with open(GROUPS_FILE, "r") as f:
            data = json.load(f)
        # Only include expected names and valid values
        groups: Dict[str, str] = {}
        half = len(FRIEND_NAMES) // 2
        for idx, name in enumerate(FRIEND_NAMES):
            val = None
            if isinstance(data, dict):
                val = data.get(name)
            # Accept "sixer" in addition to "top" and "bottom".  If the value
            # from the file is not one of these, fall back to the default top/bottom
            # split based on position.
            if val in {"top", "bottom", "sixer"}:
                groups[name] = val
            else:
                groups[name] = "top" if idx < half else "bottom"
    except Exception:
        # Default assignment: split friends evenly into top and bottom
        groups = {}
        half = len(FRIEND_NAMES) // 2
        for idx, name in enumerate(FRIEND_NAMES):
            groups[name] = "top" if idx < half else "bottom"
    return groups


def save_groups(groups: Dict[str, str]) -> None:
    """Persist the group assignments to the JSON file.

    Only keys corresponding to FRIEND_NAMES are stored.  Unexpected
    values are ignored.  The stored values are "top" or "bottom".
    """
    data: Dict[str, str] = {}
    for name in FRIEND_NAMES:
        val = groups.get(name)
        # Accept "sixer" in addition to "top" and "bottom" when persisting
        # group assignments.  Any other values are ignored.
        if val in {"top", "bottom", "sixer"}:
            data[name] = val
    with open(GROUPS_FILE, "w") as f:
        json.dump(data, f)


def fetch_scoreboard(league: str, date: str) -> Optional[dict]:
    """Fetch the scoreboard for a specific league and date from ESPN.

    Returns a dictionary containing the parsed JSON on success, or
    None if the request fails.  ESPN's API sometimes returns a 400
    message when there are no events for the requested date, so the
    caller should handle a None return value accordingly.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
    params = {"dates": date}
    try:
        resp = requests.get(url, params=params, timeout=10)
        # ESPN returns a 400 with a JSON body when no events are found
        # or when the parameters are invalid.  Attempt to parse the
        # response regardless of status code so that we can detect
        # whether events are present.
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, dict) or "events" not in data:
        return None
    return data


def parse_events_from_scoreboard(data: dict, league: str) -> List[dict]:
    """Parse the events from a scoreboard response into a simplified list.

    Each event dictionary in the returned list contains:
        - eventId: a string representing the event's unique ID
        - league: the league code (e.g. "eng.1")
        - homeTeam: display name of the home team
        - awayTeam: display name of the away team
        - title: a human-friendly match title (e.g. "Arsenal vs Chelsea")
        - status: short description of the match status (e.g. "FT")
    """
    events = []
    for event in data.get("events", []):
        event_id = str(event.get("id"))
        # Each event has a "competitions" list with details about the match
        competitions = event.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]
        # The competitors array includes two teams with a "homeAway" property
        competitors = comp.get("competitors", [])
        if len(competitors) != 2:
            continue
        home_comp = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away_comp = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home_comp or not away_comp:
            # If home/away isn't set, assume first is home
            home_comp, away_comp = competitors[0], competitors[1]
        home_team = home_comp.get("team", {}).get("displayName", "")
        away_team = away_comp.get("team", {}).get("displayName", "")
        status_type = event.get("status", {}).get("type", {})
        # Convert scheduled times into UK local time.  ESPN provides the
        # match start time in the event "date" field as an ISO 8601 UTC
        # timestamp (e.g., "2025-08-08T19:00Z").  When the match is
        # scheduled (state == "pre"), we convert this to Europe/London
        # and format it without the US time zone suffix.  For other
        # states (in‑progress, halftime, final), we retain the detail
        # provided by ESPN (e.g., "FT", "Half Time", etc.).
        status_description = status_type.get("detail", "")
        if status_type.get("state") == "pre":
            # Only convert times for scheduled matches
            event_date_str = event.get("date")
            try:
                # Parse the ISO 8601 date string, which is in UTC
                dt_utc = datetime.datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                # Convert to Europe/London timezone
                tz_london = pytz.timezone("Europe/London")
                dt_local = dt_utc.astimezone(tz_london)
                # Format: Fri, August 8 at 8:00 PM UK (no leading zeros on hour/day)
                day_name = dt_local.strftime("%a")
                month_name = dt_local.strftime("%B")
                day = dt_local.day
                hour_min = dt_local.strftime("%I:%M %p").lstrip("0")
                status_description = f"{day_name}, {month_name} {day} at {hour_min} UK"
            except Exception:
                # Fallback to the original detail on parsing errors
                status_description = status_type.get("detail", "")
        title = f"{home_team} vs {away_team}"
        events.append({
            "eventId": event_id,
            "league": league,
            "homeTeam": home_team,
            "awayTeam": away_team,
            "title": title,
            "status": status_description,
        })
        # Update the event->league mapping so summary calls know where to look
        event_league_map[event_id] = league
    return events


@app.route("/")
def index() -> str:
    """Serve the main page for the BTTS tracking app."""
    return render_template("index.html")


@app.route("/api/matches")
def api_matches():
    """Return a JSON list of matches available on the given date.

    Optional query parameters:
        date (str): Override the date used when querying APIs in YYYYMMDD format.

    This endpoint uses multiple APIs (ESPN, TheSportsDB, Football-Data.org) to
    aggregate matches from all configured league codes. Matches are deduplicated
    and sorted alphabetically by match title for ease of selection on the frontend.
    """
    date_str = request.args.get("date")
    if date_str is None:
        date_str = get_today_date_str()
    
    all_events: List[dict] = []
    
    # Try to import the multi-API aggregator
    try:
        from api_aggregator import fetch_all_matches, convert_to_app_format
        use_aggregator = True
    except ImportError:
        use_aggregator = False
    
    for league in LEAGUE_CODES:
        if use_aggregator:
            try:
                # Use multi-API aggregator (ESPN + TheSportsDB + Football-Data)
                matches = fetch_all_matches(league, date_str)
                converted = convert_to_app_format(matches)
                all_events.extend(converted)
            except Exception:
                # Fallback to ESPN-only if aggregator fails
                scoreboard = fetch_scoreboard(league, date_str)
                if scoreboard:
                    events = parse_events_from_scoreboard(scoreboard, league)
                    all_events.extend(events)
        else:
            # ESPN-only (original behavior)
            scoreboard = fetch_scoreboard(league, date_str)
            if scoreboard:
                events = parse_events_from_scoreboard(scoreboard, league)
                all_events.extend(events)
    
    # Add manually entered matches
    manual_matches = load_manual_matches()
    all_events.extend(manual_matches)
    
    # Sort events by title for better user experience
    all_events.sort(key=lambda e: e["title"])
    return jsonify(all_events)



def _count_red_cards_from_summary(data: dict, home_team_id: str, away_team_id: str):
    """
    Best-effort counter for red cards per team from an ESPN soccer summary payload.
    Returns (home_reds, away_reds). If not found, both are 0.
    """
    import re as _re
    try:
        home_reds = 0
        away_reds = 0

        def inc(team_id, n=1):
            nonlocal home_reds, away_reds
            if not team_id:
                return
            if str(team_id) == str(home_team_id):
                home_reds += n
            elif str(team_id) == str(away_team_id):
                away_reds += n

        box = (data or {}).get("boxscore", {})
        teams = box.get("teams", []) if isinstance(box.get("teams", []), list) else []
        if len(teams) >= 2:
            for t in teams:
                tid = str(t.get("team", {}).get("id", ""))
                stats_lists = []
                if isinstance(t.get("statistics"), list):
                    stats_lists.append(t["statistics"])
                if isinstance(t.get("teamStats"), list):
                    stats_lists.append(t["teamStats"])
                for stats in stats_lists:
                    for s in stats:
                        values = [
                            s.get("name",""), s.get("displayName",""), s.get("shortDisplayName",""),
                            s.get("abbreviation",""), s.get("label","")
                        ]
                        joined = " ".join([str(v) for v in values]).lower()
                        if "red card" in joined:
                            v = s.get("value")
                            if v is None:
                                dv = s.get("displayValue")
                                try:
                                    v = int(_re.findall(r"\d+", str(dv))[0]) if dv is not None else 0
                                except Exception:
                                    v = 0
                            try:
                                v = int(v)
                            except Exception:
                                v = 0
                            if str(tid) == str(home_team_id):
                                home_reds += v
                            elif str(tid) == str(away_team_id):
                                away_reds += v

        comm = (data or {}).get("commentary", {})
        possible = []
        if isinstance(comm, dict):
            if isinstance(comm.get("plays"), list): possible.append(comm["plays"])
            if isinstance(comm.get("comments"), list): possible.append(comm["comments"])
        if isinstance((data or {}).get("plays"), list):
            possible.append((data or {}).get("plays"))
        for arr in possible:
            for ev in arr:
                joined = " ".join([str(ev.get(k,"")) for k in ("type","card","text","detail","playType","headline")]).lower()
                if "red card" in joined or "straight red" in joined or "second yellow" in joined:
                    tid = ev.get("teamId") or ev.get("team", {}).get("id") or ev.get("homeAway")
                    if tid in ("home","away"):
                        inc(home_team_id if tid=="home" else away_team_id, 1)
                    else:
                        inc(tid, 1)

        hdr = (data or {}).get("header", {})
        if isinstance(hdr.get("incidents"), list):
            for incd in hdr.get("incidents"):
                desc = " ".join([str(incd.get("text","")), str(incd.get("type",""))]).lower()
                if "red card" in desc:
                    inc(incd.get("team", {}).get("id"))

        home_reds = max(0, int(home_reds))
        away_reds = max(0, int(away_reds))
        return home_reds, away_reds
    except Exception:
        return 0, 0

def fetch_match_summary(event_id: str, league: str) -> Optional[dict]:
    """Retrieve a match summary from ESPN given an event ID and league.

    The function returns the parsed JSON data on success or None on
    failure.  A failure can occur if ESPN returns an error (e.g., the
    event hasn't started yet) or the event belongs to a different
    league.  The caller may try other leagues if this returns None.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary"
    params = {"event": event_id}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
    except Exception:
        return None
    # A valid response will include a 'header' key
    if not isinstance(data, dict) or "header" not in data:
        return None
    return data


@app.route("/api/match/<event_id>")
def api_match(event_id: str):
    """Return detailed information about a specific match.

    The endpoint attempts to locate the league associated with the
    provided event ID using the in-memory event_league_map.  If the
    mapping isn't present (for instance, when the server has just
    started), it iterates through all configured leagues until it
    retrieves a successful summary.  This may incur additional
    requests on first call but ensures resilience.
    """
    # Determine which league to query
    league = event_league_map.get(event_id)
    data = None
    leagues_to_try = [league] if league else LEAGUE_CODES
    for lg in leagues_to_try:
        if lg is None:
            continue
        summary = fetch_match_summary(event_id, lg)
        if summary:
            data = summary
            league = lg
            # Update mapping for faster lookups next time
            event_league_map[event_id] = lg
            break
    if not data:
        return jsonify({"error": "Match not found"}), 404
    header = data.get("header", {})
    competitions = header.get("competitions", [])
    if not competitions:
        return jsonify({"error": "Match data unavailable"}), 500
    comp = competitions[0]
    competitors = comp.get("competitors", [])
    # Determine home and away and their scores
    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home_comp or not away_comp:
        home_comp, away_comp = competitors[0], competitors[1]
    home_team = home_comp.get("team", {}).get("displayName", "")
    away_team = away_comp.get("team", {}).get("displayName", "")
    home_score = int(home_comp.get("score", 0)) if home_comp.get("score") else 0
    away_score = int(away_comp.get("score", 0)) if away_comp.get("score") else 0
    # Status information
    comp_status = header.get("competitions", [{}])[0].get("status", {})
    status_type = comp_status.get("type", {})
    state = status_type.get("state", "")
    status_detail = status_type.get("detail", "")
    # Convert the ESPN event date (UTC) to UK local time and compute kickoff details.
    # For scheduled matches (state == "pre"), we display the day of the week and 24‑hour
    # time (e.g. "Saturday 15:00").  For in‑progress or finished matches, kickoff_time is
    # still provided but the status from ESPN is used for minutes/HT/FT.  We avoid
    # including the full date because the matches we track are within a few days.
    event_date_str = header.get("competitions", [{}])[0].get("date")
    kickoff_time = ""
    try:
        dt_utc = datetime.datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        tz_london = pytz.timezone("Europe/London")
        dt_local = dt_utc.astimezone(tz_london)
        # Default kickoff time: 24‑hour HH:MM for non‑scheduled contexts
        kickoff_time = dt_local.strftime("%H:%M")
        if state == "pre":
            # For scheduled games, include the day of week and 24‑hour time (e.g. Saturday 15:00)
            kickoff_time = dt_local.strftime("%A %H:%M")
            # Ensure status_detail is simply "Scheduled" or whatever ESPN provides; we leave
            # the status_detail unchanged here because the front‑end uses kickoff_time.
    except Exception:
        kickoff_time = ""
    # Determine if both teams have scored (BTTS)
    btts = home_score > 0 and away_score > 0
    try:
        home_id = str(home_comp.get('team', {}).get('id', ''))
        away_id = str(away_comp.get('team', {}).get('id', ''))
    except Exception:
        home_id = ''
        away_id = ''
    home_red, away_red = _count_red_cards_from_summary(data, home_id, away_id)
    return jsonify({
        "eventId": event_id,
        "league": league,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeScore": home_score,
        "awayScore": away_score,
        "homeRedCards": int(home_red), "awayRedCards": int(away_red),
        "status": status_detail,
        "kickoffTime": kickoff_time,
        "state": state,
        "btts": btts,
    })


# -----------------------------
# Authentication and Admin API
# -----------------------------

@app.route("/api/login", methods=["POST"])
def api_login():
    """Authenticate the admin user using a password.

    Expects JSON with a "password" field.  If the password matches
    ADMIN_PASSWORD, a session flag is set and a success response is
    returned.  Otherwise, a 401 Unauthorized response is sent.
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password")
    if password and password == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid password"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Log out the current admin session."""
    session.pop("admin", None)
    return jsonify({"success": True})


@app.route("/api/assignments", methods=["GET", "POST"])
def api_assignments():
    """Get or update match assignments for each friend.

    GET: returns a JSON object mapping friend names to event IDs or
    null if not assigned.

    POST: expects JSON with friend names as keys and event IDs as
    values (or null to clear).  Requires an admin session; if not
    authenticated, returns 401.  The assignments are saved to disk.
    """
    if request.method == "GET":
        return jsonify(load_assignments())
    # POST requires admin session
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    assignments = load_assignments()
    for name in FRIEND_NAMES:
        # Accept empty string or None to clear the assignment
        value = data.get(name)
        assignments[name] = value if value else None
    save_assignments(assignments)
    return jsonify({"success": True})


@app.route("/api/groups", methods=["GET", "POST"])
def api_groups():
    """Get or update the friend group assignments (top/bottom).

    GET: returns a JSON object mapping friend names to either "top" or
    "bottom".

    POST: expects JSON with friend names as keys and values of
    "top" or "bottom".  Requires an admin session.  Invalid values
    are ignored.  After saving, returns a success flag.
    """
    if request.method == "GET":
        return jsonify(load_groups())
    # POST requires admin session
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    groups = load_groups()
    updated: Dict[str, str] = {}
    for name in FRIEND_NAMES:
        val = data.get(name)
        # Accept "sixer" in addition to "top" and "bottom"
        if val in {"top", "bottom", "sixer"}:
            updated[name] = val
        else:
            # Preserve existing assignment if not provided
            updated[name] = groups.get(name, "top")
    save_groups(updated)
    return jsonify({"success": True})


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """Get or update global site settings.

    GET: returns the current settings dictionary with keys 'title' and 'message'.
    POST: expects JSON with optional 'title' and 'message' fields.  Requires
    an admin session.  Missing values are treated as empty strings (or
    default for title).  On success, a success flag is returned.
    """
    if request.method == "GET":
        return jsonify(load_settings())
    # POST requires admin session
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    title = data.get("title") or "BTTS Match Tracker"
    message = data.get("message") or ""
    save_settings({"title": title, "message": message})
    return jsonify({"success": True})


@app.route("/api/search_matches")
def api_search_matches():
    """Search for matches across leagues in a given date range.

    Query parameters:
        start (str): start date in YYYYMMDD or YYYY-MM-DD format.  Defaults to today.
        end   (str): end date in YYYYMMDD or YYYY-MM-DD format.  Defaults to start.

    The endpoint iterates through all configured league codes and
    aggregates matches within the range.  Results are sorted
    alphabetically by match title.  Scheduled times are converted to
    UK local time.
    """
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    if not start_str:
        start_str = get_today_date_str()
    if not end_str:
        end_str = start_str
    # Remove any hyphens to match ESPN date formatting
    start_clean = start_str.replace("-", "")
    end_clean = end_str.replace("-", "")
    # Compose the dates parameter.  ESPN supports ranges like
    # yyyyMMdd-yyyyMMdd for multiple days【812553852205208†L331-L343】.
    dates_param = start_clean if start_clean == end_clean else f"{start_clean}-{end_clean}"
    all_events: List[dict] = []
    for league in LEAGUE_CODES:
        scoreboard = fetch_scoreboard(league, dates_param)
        if scoreboard:
            events = parse_events_from_scoreboard(scoreboard, league)
            all_events.extend(events)
    # Remove duplicates (rare but possible when a match appears in multiple leagues) by eventId
    unique_events: Dict[str, dict] = {}
    for event in all_events:
        unique_events[event["eventId"]] = event
    # Convert to list and sort by title
    sorted_events = sorted(unique_events.values(), key=lambda e: e["title"])
    return jsonify(sorted_events)


@app.route("/api/manual_matches", methods=["GET"])
def get_manual_matches():
    """Return list of all manually added matches."""
    matches = load_manual_matches()
    return jsonify(matches)


@app.route("/api/manual_matches", methods=["POST"])
def create_manual_match():
    """Add a new manual match.
    
    Expected JSON body:
    {
        "homeTeam": "Stirling Albion",
        "awayTeam": "Elgin City",
        "league": "sco.4",
        "kickoffTime": "Sat, November 22 at 3:00 PM UK"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    home_team = data.get("homeTeam", "").strip()
    away_team = data.get("awayTeam", "").strip()
    league = data.get("league", "sco.4").strip()
    kickoff_time = data.get("kickoffTime", "TBD").strip()
    
    if not home_team or not away_team:
        return jsonify({"success": False, "message": "Home and away teams are required"}), 400
    
    event_id = add_manual_match(home_team, away_team, league, kickoff_time)
    
    return jsonify({
        "success": True,
        "message": "Manual match added successfully",
        "eventId": event_id
    })


@app.route("/api/manual_matches/<event_id>", methods=["DELETE"])
def delete_manual_match(event_id):
    """Delete a manual match by its event ID."""
    success = remove_manual_match(event_id)
    
    if success:
        return jsonify({"success": True, "message": "Match deleted"})
    else:
        return jsonify({"success": False, "message": "Match not found"}), 404


@app.route("/debug/bbc")
def debug_bbc():
    """Debug endpoint to see BBC's HTML structure"""
    try:
        from bbc_scraper import BBC_SCOTTISH_LEAGUES
        import requests
        from bs4 import BeautifulSoup
        
        league = request.args.get("league", "sco.4")
        
        if league not in BBC_SCOTTISH_LEAGUES:
            return jsonify({"error": "Invalid league"}), 400
        
        url = BBC_SCOTTISH_LEAGUES[league]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all possible match containers
        debug_info = {
            "url": url,
            "status_code": resp.status_code,
            "title": soup.title.string if soup.title else None,
            "total_elements": len(soup.find_all()),
            "potential_matches": {}
        }
        
        # Try to find elements that might contain matches
        patterns = [
            'fixture', 'match', 'event', 'game',
            'qa-fixture', 'sp-c-fixture',
            'gel-layout', 'gs-c'
        ]
        
        for pattern in patterns:
            elements = soup.find_all(class_=lambda x: x and pattern in x.lower())
            if elements:
                debug_info["potential_matches"][pattern] = {
                    "count": len(elements),
                    "first_element_classes": elements[0].get('class') if elements else None,
                    "first_element_html": str(elements[0])[:500] if elements else None
                }
        
        # Look for any "vs" text
        vs_texts = soup.find_all(string=lambda text: text and 'v' in text.lower())
        debug_info["vs_count"] = len([t for t in vs_texts if len(t.strip()) > 5])
        
        # Sample of the HTML
        debug_info["html_sample"] = str(soup)[:2000]
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/admin")
def admin_page():
    return render_template("admin.html", app_version=APP_VERSION)


@app.route("/api/admin_status")
def api_admin_status():
    """Return whether the current session is authenticated as admin."""
    return jsonify({"admin": bool(session.get("admin"))})


@app.route("/api/upcoming_matches")
def api_upcoming_matches():
    """Return matches scheduled within the next four days.

    The endpoint looks ahead four days (inclusive) starting from today in
    Europe/London time, across all configured leagues.  Results are
    aggregated and sorted alphabetically by match title.  Scheduled
    times are converted to UK local time in the returned objects via
    parse_events_from_scoreboard.
    """
    # Compute today's date and the date three days ahead in Europe/London
    tz = pytz.timezone("Europe/London")
    now = datetime.datetime.now(tz).date()
    end_date = now + datetime.timedelta(days=3)
    start_str = now.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    date_range_param = f"{start_str}-{end_str}"
    all_events: List[dict] = []
    for league in LEAGUE_CODES:
        scoreboard = fetch_scoreboard(league, date_range_param)
        if scoreboard:
            events = parse_events_from_scoreboard(scoreboard, league)
            all_events.extend(events)
    # Deduplicate by eventId and sort by title
    unique_events: Dict[str, dict] = {}
    for event in all_events:
        unique_events[event["eventId"]] = event
    sorted_events = sorted(unique_events.values(), key=lambda e: e["title"])
    return jsonify(sorted_events)


# -----------------------------
# Odds Page and Predictions API
# -----------------------------

@app.route("/api/odds_login", methods=["POST"])
def api_odds_login():
    """Authenticate a user for access to the odds page.

    Expects a JSON payload with a 'password' field.  If the password
    matches the configured ODDS_PASSWORD, a session flag is set and a
    success response is returned.  Otherwise, a 401 Unauthorized
    response is sent.
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password")
    if password and password == ODDS_PASSWORD:
        session["odds"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid password"}), 401


@app.route("/api/odds_logout", methods=["POST"])
def api_odds_logout():
    """Log out the current odds session."""
    session.pop("odds", None)
    return jsonify({"success": True})


@app.route("/api/update_results", methods=["POST"])
def api_update_results():
    """Trigger an update of the historical results database.

    Requires a valid odds or admin session.  Accepts an optional
    'days' field in the JSON payload specifying how many days back
    to fetch results.  Defaults to 7 days.  Returns a success flag
    when the update completes.
    """
    if not session.get("odds") and not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    try:
        days = int(data.get("days", 7))
    except Exception:
        days = 7
    # Limit the number of days to prevent excessive requests
    days = max(1, min(days, 31))
    update_results(days_back=days)
    return jsonify({"success": True})


@app.route("/api/btts_predictions")
def api_btts_predictions():
    """Return the top BTTS predictions for upcoming matches.

    Requires an odds or admin session.  Accepts an optional 'limit'
    query parameter specifying how many predictions to return.
    The function looks ahead four days (inclusive) from today, loads
    historical results and computes probabilities for upcoming
    fixtures.  Results are sorted by probability in descending
    order and truncated to the requested limit.
    """
    if not session.get("odds") and not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        limit = int(request.args.get("limit", 5))
    except Exception:
        limit = 5
    limit = max(1, min(limit, 20))
    # Retrieve upcoming matches using existing helper
    tz = pytz.timezone("Europe/London")
    now_date = datetime.datetime.now(tz).date()
    end_date = now_date + datetime.timedelta(days=3)
    start_str = now_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    date_range_param = f"{start_str}-{end_str}"
    upcoming: List[dict] = []
    for lg in LEAGUE_CODES:
        scoreboard = fetch_scoreboard(lg, date_range_param)
        if scoreboard:
            events = parse_events_from_scoreboard(scoreboard, lg)
            upcoming.extend(events)
    # Remove duplicates by eventId
    unique_upcoming: Dict[str, dict] = {}
    for ev in upcoming:
        unique_upcoming[ev["eventId"]] = ev
    upcoming_events = list(unique_upcoming.values())
    # Load historical results
    results = load_results()
    predictions = compute_btts_predictions(results, upcoming_events)
    # Select top predictions by probability
    top = predictions[:limit]
    # Round probability to two decimal places for display
    for item in top:
        item["probability"] = round(item["probability"], 2)
    return jsonify(top)


@app.route("/odds")
def odds_page():
    """Serve the odds page, which requires a password."""
    return render_template("odds.html", app_version=APP_VERSION)



# -----------------------------
# Telegram Notifications
# -----------------------------
import threading
import time

DEFAULT_TELEGRAM = {
    "telegram_enabled": True,
    "telegram_bot_token": "8223356225:AAEXDceBKCRYH3LJz7RnAD_O7gjLEtOM8nc",
    "telegram_chat_id": "1419645400",
    "poll_seconds": 30
}

NOTIFY_STATE_FILE = os.path.join(os.path.dirname(__file__), "notify_state.json")
_notifier_started = False

def tg_settings():
    s = load_settings()
    cfg = DEFAULT_TELEGRAM.copy()
    for k in ("telegram_enabled","telegram_bot_token","telegram_chat_id","poll_seconds"):
        if k in s and s[k] not in (None, ""):
            cfg[k] = s[k]
    return cfg

def tg_send_message(text: str) -> bool:
    cfg = tg_settings()
    if not cfg.get("telegram_enabled"): 
        return False
    token = cfg.get("telegram_bot_token")
    chat_id = cfg.get("telegram_chat_id")
    if not token or not chat_id:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
        return resp.ok
    except Exception:
        return False

def load_notify_state():
    try:
        with open(NOTIFY_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_notify_state(state):
    try:
        with open(NOTIFY_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass

def get_match_info_for_event(event_id: str):
    # Check if this is a BBC or manual match
    if event_id.startswith("bbc_") or event_id.startswith("manual_"):
        return get_match_info_from_bbc(event_id)
    
    league = event_league_map.get(event_id)
    data = None
    leagues_to_try = [league] if league else LEAGUE_CODES
    for lg in leagues_to_try:
        if lg is None: continue
        summary = fetch_match_summary(event_id, lg)
        if summary:
            data = summary
            league = lg
            event_league_map[event_id] = lg
            break
    if not data:
        for lg in LEAGUE_CODES:
            summary = fetch_match_summary(event_id, lg)
            if summary:
                data = summary; event_league_map[event_id] = lg; league = lg; break
    if not data: return None

    header = data.get("header", {})
    competitions = header.get("competitions", [{}])
    comp = competitions[0] if competitions else {}
    status = comp.get("status", {}).get("type", {}) or {}
    state = status.get("state", "" )
    status_detail = comp.get("status", {}).get("type", {}).get("shortDetail") or comp.get("status", {}).get("type", {}).get("detail") or ""
    competitors = comp.get("competitors", [])
    home_team = away_team = ""
    home_score = away_score = 0
    for c in competitors:
        if c.get("homeAway") == "home":
            home_team = c.get("team", {}).get("name", "")
            try: home_score = int(c.get("score", 0))
            except: home_score = 0
        elif c.get("homeAway") == "away":
            away_team = c.get("team", {}).get("name", "")
            try: away_score = int(c.get("score", 0))
            except: away_score = 0
    event_date_str = comp.get("date") or header.get("competitions", [{}])[0].get("date")
    kickoff_time = ""
    try:
        dt_utc = datetime.datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        tz_london = pytz.timezone("Europe/London")
        dt_local = dt_utc.astimezone(tz_london)
        kickoff_time = dt_local.strftime("%H:%M")
        if state == "pre":
            kickoff_time = dt_local.strftime("%A %H:%M")
    except Exception:
        kickoff_time = ""
    btts = home_score > 0 and away_score > 0
    try:
        home_id = str(home_comp.get("team", {}).get("id", ""))
        away_id = str(away_comp.get("team", {}).get("id", ""))
    except Exception:
        home_id = ""
        away_id = ""
    home_red, away_red = _count_red_cards_from_summary(data, home_id, away_id)
    return {
        "eventId": event_id,
        "league": league,
        "homeTeam": home_team, "awayTeam": away_team,
        "homeScore": home_score, "awayScore": away_score,
        "homeRedCards": int(home_red), "awayRedCards": int(away_red),
        "status": status_detail, "state": state,
        "kickoffTime": kickoff_time, "btts": btts
    }


def get_match_info_from_bbc(event_id: str):
    """Get live match info from BBC scraper for manual/BBC matches."""
    try:
        from bbc_scraper import get_bbc_live_score
        
        # Get match details from manual matches or parse from event_id
        manual_matches = load_manual_matches()
        match_info = None
        
        # Find the match in manual matches
        for match in manual_matches:
            if match.get("eventId") == event_id:
                match_info = match
                break
        
        if not match_info and event_id.startswith("bbc_"):
            # Parse event ID: bbc_sco.4_Stirling_Albion_Elgin_City
            parts = event_id.split("_")
            if len(parts) >= 3:
                league = parts[1]
                # Reconstruct team names
                home_team = " ".join(parts[2:-1])  # Everything between league and last part
                away_team = parts[-1].replace("_", " ")
                match_info = {
                    "homeTeam": home_team,
                    "awayTeam": away_team,
                    "league": league
                }
        
        if not match_info:
            return None
        
        # Scrape BBC for live score
        bbc_data = get_bbc_live_score(
            match_info.get("homeTeam", ""),
            match_info.get("awayTeam", ""),
            match_info.get("league", "")
        )
        
        if not bbc_data:
            # Return match info without scores
            return {
                "eventId": event_id,
                "league": match_info.get("league", ""),
                "homeTeam": match_info.get("homeTeam", ""),
                "awayTeam": match_info.get("awayTeam", ""),
                "homeScore": 0,
                "awayScore": 0,
                "homeRedCards": 0,
                "awayRedCards": 0,
                "status": match_info.get("status", "Scheduled"),
                "state": "pre",
                "kickoffTime": match_info.get("kickoffTime", ""),
                "btts": False
            }
        
        # Map BBC status to ESPN-style state
        status = bbc_data.get("status", "Scheduled")
        if status == "FT":
            state = "post"
        elif status in ["HT", "In Progress"] or any(c.isdigit() for c in status):
            state = "in"
        else:
            state = "pre"
        
        home_score = bbc_data.get("homeScore", 0)
        away_score = bbc_data.get("awayScore", 0)
        btts = home_score > 0 and away_score > 0
        
        return {
            "eventId": event_id,
            "league": bbc_data.get("league", ""),
            "homeTeam": bbc_data.get("homeTeam", ""),
            "awayTeam": bbc_data.get("awayTeam", ""),
            "homeScore": home_score,
            "awayScore": away_score,
            "homeRedCards": 0,  # BBC doesn't show red cards easily
            "awayRedCards": 0,
            "status": status,
            "state": state,
            "kickoffTime": "",
            "btts": btts
        }
        
    except Exception as e:
        print(f"BBC scraper error for {event_id}: {e}")
        return None

def format_minute(status_detail: str):
    if not status_detail: return ""
    return status_detail

def notifier_loop():
    state = load_notify_state()
    while True:
        try:
            cfg = tg_settings()
            if not cfg.get("telegram_enabled"):
                time.sleep(cfg.get("poll_seconds",30)); 
                continue
            assignments = load_assignments()
            for friend, event_id in assignments.items():
                if not event_id: continue
                info = get_match_info_for_event(event_id)
                if not info: continue
                key = event_id
                prev = state.get(key, {"state": "", "homeScore": 0, "awayScore": 0, "kickoffSent": False, "bttsSent": False, "ftSent": False})
                cur_state = info["state"]
                hs, as_ = info["homeScore"], info["awayScore"]
                minute = format_minute(info.get("status",""))
                if cur_state == "in" and not prev.get("kickoffSent"):
                    tg_send_message(f"Kickoff {friend}: {info['homeTeam']} vs {info['awayTeam']} ({info['kickoffTime']})")
                    prev["kickoffSent"] = True
                if (hs != prev.get("homeScore") or as_ != prev.get("awayScore")) and cur_state == "in":
                    tg_send_message(f"Goal for {friend}: {info['homeTeam']} {hs} {info['awayTeam']} {as_} - {minute}")
                if info["btts"] and not prev.get("bttsSent"):
                    tg_send_message(f"BTTS {friend}: Both teams have scored - {info['homeTeam']} {hs} {info['awayTeam']} {as_} ({minute})")
                    prev["bttsSent"] = True
                if cur_state == "post" and not prev.get("ftSent"):
                    tg_send_message(f"FT {friend}: {info['homeTeam']} {hs} {info['awayTeam']} {as_}")
                    prev["ftSent"] = True
                prev["state"] = cur_state
                prev["homeScore"] = hs
                prev["awayScore"] = as_
                state[key] = prev
            save_notify_state(state)
        except Exception:
            pass
        time.sleep(cfg.get("poll_seconds", 30))

def start_notifier_once():
    global _notifier_started
    if _notifier_started: return
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        t = threading.Thread(target=notifier_loop, daemon=True)
        t.start()
        _notifier_started = True

start_notifier_once()
if __name__ == "__main__":
    # When running directly, enable debug mode for easier development.
    # Listen on port 8094 instead of the previous default of 8000.
    app.run(host="0.0.0.0", port=8094, debug=True)

@app.route("/notify")
def notify_page():
    return render_template("notify.html", app_version=APP_VERSION)

@app.route("/update_telegram", methods=["POST"])
def update_telegram():
    data = request.get_json(silent=True) or {}
    # Accept both "token" and "telegram_bot_token" keys for backwards compatibility
    token = (data.get("token") or data.get("telegram_bot_token") or "").strip()
    chat_id = (data.get("chat_id") or data.get("telegram_chat_id") or "").strip()
    if not token or not chat_id:
        return jsonify({"success": False, "message": "Missing token or chat ID."}), 400
    try:
        # Load existing settings to preserve other keys
        settings = load_settings()
        settings["telegram_enabled"] = True
        settings["telegram_bot_token"] = token
        settings["telegram_chat_id"] = chat_id
        # Ensure poll_seconds has a sensible default
        if not settings.get("poll_seconds"):
            settings["poll_seconds"] = DEFAULT_TELEGRAM.get("poll_seconds", 30)
        save_settings(settings)
    except Exception as ex:
        return jsonify({"success": False, "message": f"Error saving settings: {ex}"}), 500
    return jsonify({"success": True, "message": "Telegram settings saved successfully."})


@app.route("/test_telegram", methods=["POST"])
def test_telegram():
    try:
        # Try to read runtime or saved Telegram credentials
        settings = tg_settings() if 'tg_settings' in globals() else {}
        token = (settings.get("telegram_bot_token") or settings.get("token") or "").strip()
        chat_id = (settings.get("telegram_chat_id") or settings.get("chat_id") or "").strip()
        # Fallback to saved settings if missing
        if not token or not chat_id:
            t2, c2 = _load_saved_telegram()
            token = token or t2
            chat_id = chat_id or c2
        if not token or not chat_id:
            return jsonify({"success": False, "message": "Missing token or chat_id. Save them first on the Notify page."}), 400
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "BTTS Test Notification ✅").strip()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        r = requests.post(url, json=payload, timeout=10)
        ok = False
        msg = f"HTTP {r.status_code}"
        try:
            j = r.json()
            ok = bool(j.get("ok"))
            if not ok and "description" in j:
                msg += f" — {j['description']}"
        except Exception:
            pass
        if ok:
            return jsonify({"success": True, "message": "Test message sent."})
        return jsonify({"success": False, "message": f"Failed to send. {msg}"}), 502
    except Exception as ex:
        return jsonify({"success": False, "message": f"Error: {ex}"}), 500
        return jsonify({"success": False, "message": f"Failed to send. {msg}"}), 502
    except Exception as ex:
        return jsonify({"success": False, "message": f"Error: {ex}"}), 500


def _load_saved_telegram():
    """Read the Telegram bot token and chat ID from the settings file.

    Returns a tuple of (token, chat_id).  This function is used as a
    fallback by endpoints such as test_telegram and telegram_status.
    It reads the consolidated settings file (SETTINGS_FILE) rather than a
    separate settings.json.  Supported keys are 'telegram_bot_token'
    and 'telegram_chat_id'.  For legacy compatibility the function
    will also return values stored under the older keys 'telegram_token'
    and 'telegram_chat_id' if present.
    """
    try:
        with open(SETTINGS_FILE, "r") as f:
            s = json.load(f)
        if not isinstance(s, dict):
            return ("", "")
        token = s.get("telegram_bot_token") or s.get("telegram_token") or ""
        chat_id = s.get("telegram_chat_id") or s.get("chat_id") or ""
        return (str(token).strip(), str(chat_id).strip())
    except Exception:
        return ("", "")


@app.route("/telegram_status", methods=["GET"])
def telegram_status():
    try:
        settings = tg_settings() if 'tg_settings' in globals() else {"token":"", "chat_id":""}
        token = (settings.get("token") or "").strip()
        chat_id = (settings.get("chat_id") or "").strip()
        t2, c2 = _load_saved_telegram()
        token_eff = token or t2
        chat_eff = chat_id or c2
        def mask(t): 
            if not t: return ""
            if len(t) <= 6: return "*"*len(t)
            return t[:6] + "..." + t[-4:]
        return jsonify({
            "env_or_runtime_token_present": bool(token),
            "env_or_runtime_chat_present": bool(chat_id),
            "saved_token_present": bool(t2),
            "saved_chat_present": bool(c2),
            "effective_token_masked": mask(token_eff),
            "effective_chat_id": chat_eff
        })
    except Exception as ex:
        return jsonify({"success": False, "message": f"Error: {ex}"}), 500
