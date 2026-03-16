from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from config import WEBAPP_URL

FARDH_KEYS = {"fajr", "dhuhr", "asr", "maghrib", "isha"}


def prayer_checkin_kb(prayer_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕌 Prayed with Jama'ah", callback_data=f"pray:{prayer_key}:jamaah")],
        [
            InlineKeyboardButton("🏠 Prayed at home",    callback_data=f"pray:{prayer_key}:home"),
            InlineKeyboardButton("⏰ Snooze 10 min",     callback_data=f"snooze:{prayer_key}:10"),
        ],
        [InlineKeyboardButton("😔 Missed it",            callback_data=f"pray:{prayer_key}:missed")],
    ])


def missed_followup_kb(prayer_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I made it up (Qada)", callback_data=f"pray:{prayer_key}:home")],
        [InlineKeyboardButton("🤲 I'll try next time",  callback_data=f"dismiss:missed:{prayer_key}")],
    ])


def prayer_log_kb(logged_prayers: set) -> InlineKeyboardMarkup:
    """Manual prayer check-in — shows status for each prayer, tap unlogged to log."""
    prayers = [
        ("fajr",    "🌅 Fajr"),
        ("dhuhr",   "🌤 Dhuhr"),
        ("asr",     "🌇 Asr"),
        ("maghrib", "🌆 Maghrib"),
        ("isha",    "🌙 Isha"),
    ]
    rows = []
    for key, label in prayers:
        if key in logged_prayers:
            rows.append([InlineKeyboardButton(f"✅ {label}", callback_data=f"pray_done:{key}")])
        else:
            rows.append([InlineKeyboardButton(f"🕌 {label} — tap to log", callback_data=f"praymenu:{key}")])
    rows.append([InlineKeyboardButton("📿 Sunnah deeds", callback_data="view:deeds")])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="view:home")])
    return InlineKeyboardMarkup(rows)


def deed_kb(goals: list, logged_keys: set) -> InlineKeyboardMarkup:
    """Sunnah/voluntary deeds only — fardh prayers handled separately."""
    rows = []
    for g in goals:
        if g["deed_key"] in FARDH_KEYS:
            continue  # prayers have their own flow
        done = g["deed_key"] in logged_keys
        label = f"✅ {g['deed_label']}" if done else f"◻️ {g['deed_label']} (+{g['points']} pts)"
        rows.append([InlineKeyboardButton(label, callback_data=f"deed:{g['deed_key']}:{g['points']}")])
    rows.append([
        InlineKeyboardButton("🕌 Prayers",   callback_data="view:prayers"),
        InlineKeyboardButton("📊 Today",     callback_data="view:today"),
    ])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="view:home")])
    return InlineKeyboardMarkup(rows)


def after_prayer_kb(prayer_key: str, logged_prayers: set, ramadan: bool = False) -> InlineKeyboardMarkup:
    """Shown after logging a prayer. Smart 'log more' based on what's left."""
    order = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    remaining = [p for p in order if p not in logged_prayers]

    rows = []

    if remaining:
        # Show next unlogged prayer as a quick-log button
        next_p = remaining[0]
        next_labels = {"fajr": "🌅 Fajr", "dhuhr": "🌤 Dhuhr", "asr": "🌇 Asr",
                       "maghrib": "🌆 Maghrib", "isha": "🌙 Isha"}
        rows.append([InlineKeyboardButton(
            f"➡️ Log {next_labels[next_p]}",
            callback_data=f"praymenu:{next_p}"
        )])

    # Ramadan: after Maghrib, offer to log the fast
    if ramadan and prayer_key == "maghrib" and "fast" not in logged_prayers:
        rows.append([InlineKeyboardButton(
            "🌙 Log today's fast (+4 pts)", callback_data="deed:fast:4"
        )])

    rows.append([
        InlineKeyboardButton("🕌 All prayers", callback_data="view:prayers"),
        InlineKeyboardButton("📊 Today",       callback_data="view:today"),
    ])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="view:home")])
    return InlineKeyboardMarkup(rows)


def add_goal_kb(existing_keys: set = None) -> InlineKeyboardMarkup:
    if existing_keys is None:
        existing_keys = set()
    opts = [
        ("tahajjud",  "Tahajjud prayer",      4),
        ("fast",      "Fasting Mon & Thu",     4),
        ("sadaqah",   "Sadaqah",               2),
        ("hadith",    "Read 1 hadith",         1),
        ("dhikr_am",  "Morning adhkar",        2),
        ("dhikr_pm",  "Evening adhkar",        2),
        ("istighfar", "100x Istighfar",        1),
    ]
    rows = []
    for key, label, pts in opts:
        if key in existing_keys:
            rows.append([InlineKeyboardButton(f"✅ {label} (added)", callback_data="noop")])
        else:
            rows.append([InlineKeyboardButton(
                f"➕ {label} (+{pts} pts)", callback_data=f"addgoal:{key}:{pts}:{label}"
            )])
    rows.append([InlineKeyboardButton("✅ Done", callback_data="view:goals")])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="view:home")])
    return InlineKeyboardMarkup(rows)


def main_menu_kb(has_webapp: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🕌 Prayers",    callback_data="view:prayers"),
            InlineKeyboardButton("📿 Deeds",      callback_data="view:deeds"),
        ],
        [
            InlineKeyboardButton("📊 Today",      callback_data="view:today"),
            InlineKeyboardButton("📅 Weekly",     callback_data="view:weekly"),
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="view:leaderboard"),
            InlineKeyboardButton("🎯 Goals",        callback_data="view:goals"),
        ],
        [
            InlineKeyboardButton("👤 Profile",  callback_data="view:profile"),
            InlineKeyboardButton("⚙️ Settings", callback_data="view:settings"),
        ],
    ]
    if has_webapp and WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            "🌐 Open Dashboard",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )])
    return InlineKeyboardMarkup(rows)


def settings_kb(gender: str = "unset") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📍 Change city",         callback_data="settings:city")],
        [InlineKeyboardButton("➕ Add Sunnah deed",     callback_data="settings:addgoal")],
        [InlineKeyboardButton("🔕 Pause reminders",    callback_data="settings:pause")],
        [InlineKeyboardButton("🔔 Resume reminders",   callback_data="settings:resume")],
        [InlineKeyboardButton("👥 Create a group",     callback_data="settings:creategroup")],
        [InlineKeyboardButton("🔗 Join a group",       callback_data="settings:joingroup")],
        [InlineKeyboardButton("🔄 Reset progress",     callback_data="settings:reset")],
        [InlineKeyboardButton("🧪 Test Alerts (temp)", callback_data="settings:test_alerts")],
        [InlineKeyboardButton("🏠 Home",               callback_data="view:home")],
    ]
    if gender == "female":
        rows.insert(7, [InlineKeyboardButton("🌙 Pause Tracking", callback_data="settings:periodmode")])
    return InlineKeyboardMarkup(rows)


def reset_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Yes, reset everything", callback_data="settings:reset_confirm")],
        [InlineKeyboardButton("❌ Cancel",                 callback_data="view:settings")],
    ])


def report_nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Weekly",   callback_data="view:weekly"),
            InlineKeyboardButton("📆 Monthly",  callback_data="view:monthly"),
        ],
        [
            InlineKeyboardButton("👤 Profile",   callback_data="view:profile"),
            InlineKeyboardButton("🏠 Home",      callback_data="view:home"),
        ],
    ])


def challenge_kb(challenge_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept challenge", callback_data=f"challenge:accept:{challenge_id}")],
        [InlineKeyboardButton("⏭ Skip this week",   callback_data=f"challenge:skip:{challenge_id}")],
    ])
