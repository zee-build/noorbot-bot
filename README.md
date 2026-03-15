# NoorBot 🌙

**Islamic Productivity Telegram Bot**

Tracks Fardh & Sunnah deeds, sends prayer reminders, scores daily
performance, and reports weekly/monthly trends.

---

## Features

- 🕌 **Prayer reminders** — 15 min before every salah (Fajr → Isha)
- ✅ **One-tap check-in** — Prayed at home or with Jama'ah?
- 🏆 **Scoring** — Points per deed, bonus for congregation
- 🎯 **Goal setting** — Add any Sunnah deed (tahajjud, fasting, dhikr...)
- 📊 **Daily report** — Full breakdown at 10:30 PM
- 📅 **Weekly report** — Every Friday after Jumu'ah
- 📆 **Monthly report** — Trend vs previous month
- 🔥 **Streaks** — Track consecutive days per deed

---

## Quick Start (10 minutes)

### 1. Create your bot on Telegram
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the **API token**

### 2. Clone & install

```bash
git clone <your-repo>
cd noorbot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and paste your BOT_TOKEN
```

### 4. Run

```bash
python bot.py
```

That's it. Open Telegram, find your bot, and send `/start`.

---

## Free Hosting on Oracle Cloud (Recommended)

Oracle Cloud Always Free tier gives you a VM that runs 24/7 forever for free.

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com) (free, needs credit card for verification only)
2. Create a **VM.Standard.E2.1.Micro** instance (Always Free)
3. SSH into it and run the Quick Start steps above
4. Run with `nohup python bot.py &` to keep it alive after you disconnect

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Set up account, see today's prayer times |
| `/report` | Today's performance |
| `/weekly` | This week's summary |
| `/monthly` | Monthly trend |
| `/goals` | View & manage your goals |
| `/stats` | Prayer streaks |
| `/settings` | Location, reminders |
| `/help` | All commands |

---

## Scoring System

| Deed | Points |
|------|--------|
| Fardh prayer (on time) | 3 pts |
| Jama'ah bonus | +1 pt |
| Sunnah rawatib | 2 pts |
| Quran (1 page) | 2 pts |
| Dhikr after salah | 1 pt |
| Tahajjud | 4 pts |
| Fasting (Mon/Thu) | 4 pts |
| Sadaqah | 2 pts |
| Hadith | 1 pt |

**Max daily score (default goals): ~22 pts**

---

## Project Structure

```
noorbot/
├── bot.py              # Entry point, scheduler setup
├── config.py           # All settings (token, scoring, timezone)
├── requirements.txt
├── .env.example
├── handlers/
│   ├── commands.py     # /start, /report, /goals, etc.
│   ├── checkin.py      # All inline button callbacks
│   ├── reminders.py    # Prayer reminder engine
│   └── reports.py      # Daily/weekly/monthly report builders
└── utils/
    ├── database.py     # SQLite via aiosqlite
    ├── prayer_times.py # Aladhan API integration
    └── keyboards.py    # All inline keyboard builders
```

---

## Customization

Edit `config.py` to:
- Change `REMINDER_MINUTES_BEFORE` (default: 15 min)
- Adjust `POINTS` for each deed
- Change `TIMEZONE` (default: Asia/Dubai)
- Change `PRAYER_METHOD` (8 = Gulf Region)

---

## License

MIT — use it, sell it, modify it. May Allah bless your work. 🤲
