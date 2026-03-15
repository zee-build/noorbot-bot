"""
NoorBot v2 — Configuration
"""
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
DATABASE_URL     = os.getenv("DATABASE_URL", "noorbot.db")
TIMEZONE         = "Asia/Dubai"
PRAYER_METHOD    = 8
REMINDER_MINUTES = 15
WEBAPP_URL       = os.getenv("WEBAPP_URL", "")
ADMIN_CHAT_ID    = int(os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_PASSWORD   = os.getenv("ADMIN_PASSWORD", "")

# ── Scoring ───────────────────────────────────────────────
POINTS = {
    "fajr":            3,
    "dhuhr":           3,
    "asr":             3,
    "maghrib":         3,
    "isha":            3,
    "jamaah_bonus":    1,
    "sunnah_rawatib":  2,
    "quran":           2,
    "dhikr":           1,
    "tahajjud":        4,
    "fast":            4,
    "sadaqah":         2,
    "hadith":          1,
    "dhikr_am":        2,
    "dhikr_pm":        2,
    "istighfar":       1,
}

# ── XP per point earned ───────────────────────────────────
XP_PER_POINT = 10   # 1 deed point = 10 XP

# ── Level thresholds (XP needed to reach each level) ─────
# Level N requires N*200 XP total
def xp_for_level(level: int) -> int:
    return level * 200

def level_from_xp(xp: int) -> int:
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
    return min(level, 50)

def xp_progress(xp: int) -> tuple:
    """Returns (current_level, xp_into_level, xp_needed_for_next)"""
    level = level_from_xp(xp)
    if level >= 50:
        return 50, 0, 0
    xp_start = xp_for_level(level)
    xp_end   = xp_for_level(level + 1)
    return level, xp - xp_start, xp_end - xp_start

# ── Level milestone messages ──────────────────────────────
LEVEL_MILESTONES = {
    5:  "You've built a foundation. Keep going! 🌱",
    10: "10 levels in — your consistency is showing. 💪",
    15: "MashaAllah! You're forming real habits now. ⭐",
    20: "Level 20 — halfway to mastery. SubhanAllah! 🌟",
    25: "Your dedication is an inspiration. 🏅",
    30: "Level 30 — you're in rare company. Keep it up! 🔥",
    40: "Level 40 — true consistency. Allah sees your effort. 💚",
    50: "Level 50 — MashaAllah! You've reached the top. 🏆",
}

# ── Weekly challenge definitions ─────────────────────────
WEEKLY_CHALLENGES = [
    {
        "id": "all5_3days",
        "title": "Pray all 5 on time for 3 days",
        "description": "Complete all 5 Fardh prayers on time for any 3 days this week.",
        "xp_reward": 500,
        "check": "all5_streak",
        "target": 3,
    },
    {
        "id": "all5_7days",
        "title": "Perfect prayer week 🏆",
        "description": "Complete all 5 Fardh prayers every single day this week.",
        "xp_reward": 1500,
        "check": "all5_streak",
        "target": 7,
    },
    {
        "id": "quran_5days",
        "title": "Quran 5 days in a row",
        "description": "Read at least 1 page of Quran for 5 consecutive days.",
        "xp_reward": 600,
        "check": "deed_streak",
        "deed": "quran",
        "target": 5,
    },
    {
        "id": "jamaah_3",
        "title": "3x Jama'ah this week",
        "description": "Pray with the congregation at least 3 times this week.",
        "xp_reward": 400,
        "check": "jamaah_count",
        "target": 3,
    },
    {
        "id": "fast_monday",
        "title": "Fast on Monday",
        "description": "Complete a Sunnah fast on Monday this week.",
        "xp_reward": 500,
        "check": "deed_day",
        "deed": "fast",
        "day": 0,
    },
]

# ── Duas & Hadiths (rotated daily) ───────────────────────
MORNING_CONTENT = [
    {
        "dua": "اللَّهُمَّ بِكَ أَصْبَحْنَا وَبِكَ أَمْسَيْنَا",
        "dua_en": "O Allah, by You we enter the morning and by You we enter the evening.",
        "hadith": "The Prophet ﷺ said: 'The most beloved deeds to Allah are those done consistently, even if small.'",
        "source": "Bukhari & Muslim",
    },
    {
        "dua": "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ",
        "dua_en": "We have entered the morning and the entire dominion belongs to Allah.",
        "hadith": "The Prophet ﷺ said: 'Whoever prays Fajr is under the protection of Allah.'",
        "source": "Muslim",
    },
    {
        "dua": "اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا",
        "dua_en": "O Allah, I ask You for beneficial knowledge.",
        "hadith": "The Prophet ﷺ said: 'Two rak'ahs of Fajr are better than the world and all it contains.'",
        "source": "Muslim",
    },
    {
        "dua": "رَبِّ زِدْنِي عِلْمًا",
        "dua_en": "My Lord, increase me in knowledge.",
        "hadith": "The Prophet ﷺ said: 'The five daily prayers are an expiation for what comes between them.'",
        "source": "Muslim",
    },
    {
        "dua": "اللَّهُمَّ اهْدِنِي وَسَدِّدْنِي",
        "dua_en": "O Allah, guide me and keep me on the straight path.",
        "hadith": "The Prophet ﷺ said: 'Whoever reads Ayat al-Kursi after every prayer, nothing prevents him from entering Jannah.'",
        "source": "Nasa'i",
    },
    {
        "dua": "سُبْحَانَ اللهِ وَبِحَمْدِهِ",
        "dua_en": "Glory be to Allah and praise be to Him.",
        "hadith": "The Prophet ﷺ said: 'Whoever says SubhanAllah wa bihamdihi 100 times, his sins are forgiven even if they were like sea foam.'",
        "source": "Bukhari",
    },
    {
        "dua": "لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ",
        "dua_en": "There is no god but Allah, alone, without partner.",
        "hadith": "The Prophet ﷺ said: 'The prayer is the pillar of the religion.'",
        "source": "Bayhaqi",
    },
]

# ── Performance tier labels ───────────────────────────────
PERFORMANCE_TIERS = [
    (90, "🏆 Excellent — MashaAllah!"),
    (75, "💚 Good — Keep it up!"),
    (60, "📈 Improving — Stay consistent"),
    (40, "⚠️  Needs attention"),
    (0,  "🤲 Every day is a new start"),
]
