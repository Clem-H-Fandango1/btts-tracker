# BTTS Match Tracker

A Flask-based web application for tracking Both Teams To Score (BTTS) football bets across multiple leagues with live updates and Telegram notifications.

## Features

- 🎯 Assign football matches to friends for BTTS betting
- ⚽ Live match tracking via ESPN API
- 📱 Telegram notifications for goals, BTTS, and full-time
- 📊 BTTS probability predictions based on historical data
- 🔴 Red card tracking
- 🏆 Support for 20+ football leagues and competitions

## Quick Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### Manual Railway Deployment

1. Fork this repository or upload to your GitHub
2. Create a new project on [Railway](https://railway.app)
3. Connect your GitHub repository
4. Railway will auto-detect the Dockerfile
5. Set the following environment variables:
   - `ADMIN_PASSWORD` - Password for admin panel (default: admin123)
   - `ODDS_PASSWORD` - Password for odds page (default: odds123)
   - `SECRET_KEY` - Random string for session security
   - `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (optional)
   - `TELEGRAM_CHAT_ID` - Your Telegram chat ID (optional)
6. Deploy!

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_PASSWORD` | Admin panel password | `admin123` |
| `ODDS_PASSWORD` | Odds page password | `odds123` |
| `SECRET_KEY` | Flask session secret | `bttssecretkey` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token | - |
| `TELEGRAM_CHAT_ID` | Telegram chat/channel ID | - |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Or with Docker
docker build -t btts-tracker .
docker run -p 8094:8094 btts-tracker
```

## Usage

1. **Admin Panel**: `/admin` - Assign matches to friends
2. **Main View**: `/` - View all assigned matches with live updates
3. **Odds Page**: `/odds` - View BTTS probability predictions
4. **Telegram Config**: `/notify` - Configure Telegram notifications

## Telegram Setup

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Add the bot to your group/channel
4. Get your chat ID (use [@userinfobot](https://t.me/userinfobot))
5. Configure in the `/notify` page or set environment variables

## Version

Current version: **v2.1.3-dev-rc**

## License

For personal use by friends group.
