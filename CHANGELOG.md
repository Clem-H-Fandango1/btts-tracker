# Changelog

## v2.3.0-bbc-scraper (2025-11-22)
- Added BBC Sport web scraper for Scottish leagues
- Automatic live score updates from BBC (no API limits!)
- Works for all Scottish League matches (Premiership, Championship, One, Two)
- Combined with manual match entry for complete solution
- No API keys required, unlimited scraping

## v2.2.1-manual-matches (2025-11-22)
- Added manual match entry system via API endpoints
- Manual matches appear in dropdown alongside API matches
- Fixes ESPN missing fixtures issue (add manually, track live automatically)
- API endpoints: POST/GET/DELETE /api/manual_matches

## v2.2.0-multi-api (2025-11-22)
- Added multi-API aggregation system (ESPN + TheSportsDB + Football-Data.org)
- Fixes missing Scottish League One and Two fixtures
- Automatic deduplication of matches from multiple sources
- Fallback redundancy if one API is down
- Optional Football-Data.org API key for best coverage

## v2.1.2-dev-rc (2025-08-19)
- Added red card logic to API and UI (🟥 / 🟥 xN).
- No demo/preview UI changes in this build.
