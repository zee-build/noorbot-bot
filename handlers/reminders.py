"""
Reminders v2 — prayer reminders, missed prayer follow-ups,
morning dua/hadith, weekly challenge drops.
"""
import logging
from datetime import date, datetime
from telegram import Bot
from telegram.constants import ParseMode

from utils.database import (
    get_all_active_users, mark_reminder_sent, mark_missed_followup_sent,
    get_today_logs, get_user_goals, is_period_mode,
    get_uninformed_female_users, mark_period_notified,
)
from utils.prayer_times import (
    get_prayer_times, minutes_until_prayer, minutes_since_prayer,
    PRAYER_KEYS, PRAYER_EMOJIS, PRAYER_NAMES
)
from utils.keyboards import prayer_checkin_kb, missed_followup_kb
from config import REMINDER_MINUTES, MORNING_CONTENT, WEEKLY_CHALLENGES
import pytz

logger = logging.getLogger(__name__)

PRAYER_HADITHS = {
    "fajr":    "The Prophet ﷺ said: 'Whoever prays Fajr is under the protection of Allah.' — Muslim",
    "dhuhr":   "The Prophet ﷺ said: 'The gates of heaven open at midday.' — Tirmidhi",
    "asr":     "Allah says: 'Guard the prayers, and the middle prayer.' — Quran 2:238",
    "maghrib": "The Prophet ﷺ said: 'Do not delay three things: prayer when its time comes...' — Tirmidhi",
    "isha":    "The Prophet ﷺ said: 'If people knew the reward for Isha in congregation, they would come crawling.' — Bukhari",
}


async def _notify_period_mode_feature(bot: Bot):
    """One-time notification to female users about the period tracking feature."""
    users = await get_uninformed_female_users()
    for user in users:
        try:
            await mark_period_notified(user["user_id"])  # mark first to avoid double-send on error
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    "🌸 *A feature made for you*\n\n"
                    "During your period, you can't pray or fast — and that's perfectly fine. "
                    "But we don't want that to break your streaks or affect your progress.\n\n"
                    "That's why NoorBot has *Period Mode* 💚\n\n"
                    "While it's on:\n"
                    "• Your streaks are protected — no gaps\n"
                    "• Prayer reminders are paused\n"
                    "• Your progress picks up right where you left off\n\n"
                    "To activate it, just go to:\n"
                    "📱 *Dashboard → Settings → Period Tracking*\n"
                    "or tap /settings here in the chat.\n\n"
                    "_May Allah make it easy for you._ 🤲"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Period notification error {user['user_id']}: {e}")


async def check_and_send_reminders(bot: Bot):
    """Called every minute — sends pre-prayer reminders & missed follow-ups."""
    await _notify_period_mode_feature(bot)

    users = await get_all_active_users()
    today = date.today().isoformat()

    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            # Skip all prayer reminders during period mode
            if await is_period_mode(user["user_id"]):
                continue

            times = await get_prayer_times(user["latitude"], user["longitude"])
            if not times:
                continue
            tz = user.get("timezone", "Asia/Dubai")

            for key in PRAYER_KEYS:
                mins_until = minutes_until_prayer(times[key], tz)

                # ── Pre-prayer reminder (15 min before) ──
                if REMINDER_MINUTES <= mins_until <= REMINDER_MINUTES + 1:
                    sent = await mark_reminder_sent(user["user_id"], key, today)
                    if sent:
                        await _send_reminder(bot, user["user_id"], key, times[key], user["city"])

                # ── Missed follow-up (45 min after prayer time, not yet logged) ──
                mins_since = minutes_since_prayer(times[key], tz)
                if 44 <= mins_since <= 46:
                    logs = await get_today_logs(user["user_id"])
                    logged = {l["deed_key"] for l in logs}
                    if key not in logged:
                        sent = await mark_missed_followup_sent(user["user_id"], key, today)
                        if sent:
                            await _send_missed_followup(bot, user["user_id"], key)

        except Exception as e:
            logger.error(f"Reminder error user {user['user_id']}: {e}")


async def _send_reminder(bot: Bot, chat_id: int, key: str, prayer_time: str, city: str):
    emoji   = PRAYER_EMOJIS[key]
    name    = PRAYER_NAMES[key]
    hadith  = PRAYER_HADITHS.get(key, "")

    text = (
        f"{emoji} *{name} in {REMINDER_MINUTES} minutes*\n\n"
        f"🕐 *{prayer_time}* in {city}\n\n"
        f"_{hadith}_\n\n"
        f"🕌 Head to the masjid or prepare for salah now."
    )
    await bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=prayer_checkin_kb(key)
    )


async def _send_missed_followup(bot: Bot, chat_id: int, key: str):
    name  = PRAYER_NAMES[key]
    emoji = PRAYER_EMOJIS[key]
    text = (
        f"{emoji} *Did you pray {name}?*\n\n"
        "It looks like it may have slipped by. "
        "You can still pray it as Qada — Allah is Most Merciful. 🤲"
    )
    await bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=missed_followup_kb(key)
    )


async def send_morning_content(bot: Bot):
    """Sends morning adhkar prompt + dua/hadith after Fajr."""
    from handlers.adhkar import send_morning_adhkar_prompt
    from utils.prayer_times import is_ramadan
    users = await get_all_active_users()
    today = date.today()
    content = MORNING_CONTENT[today.toordinal() % len(MORNING_CONTENT)]

    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            ramadan = await is_ramadan(user.get("latitude", 25.2048), user.get("longitude", 55.2708))
            ramadan_txt = "\n\n🌙 *Ramadan Mubarak!* May Allah accept your fast today." if ramadan else ""
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌅 *{today.strftime('%A, %d %B')}*{ramadan_txt}\n\n"
                    f"*Hadith of the Day:*\n_{content['hadith']}_\n"
                    f"📚 _{content['source']}_"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            await send_morning_adhkar_prompt(bot, user["user_id"])
        except Exception as e:
            logger.error(f"Morning content error {user['user_id']}: {e}")


async def send_evening_adhkar_reminder(bot: Bot):
    """Sends evening adhkar prompt around Maghrib time."""
    from handlers.adhkar import send_evening_adhkar_prompt
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            await send_evening_adhkar_prompt(bot, user["user_id"])
        except Exception as e:
            logger.error(f"Evening adhkar error {user['user_id']}: {e}")


async def send_sleep_adhkar_reminder(bot: Bot):
    """Sends sleep adhkar prompt at 10 PM."""
    from handlers.adhkar import send_sleep_adhkar_prompt
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            await send_sleep_adhkar_prompt(bot, user["user_id"])
        except Exception as e:
            logger.error(f"Sleep adhkar error {user['user_id']}: {e}")


async def send_ramadan_suhoor(bot: Bot):
    """Suhoor reminder — sent before Fajr (around 3:30 AM UAE)."""
    from utils.prayer_times import is_ramadan
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            ramadan = await is_ramadan(user.get("latitude", 25.2048), user.get("longitude", 55.2708))
            if not ramadan:
                continue
            times = await get_prayer_times(user["latitude"], user["longitude"])
            fajr_time = times.get("fajr", "05:00") if times else "05:00"
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌙 *Suhoor Time!*\n\n"
                    f"Fajr is at *{fajr_time}* — eat & drink before then.\n\n"
                    "_The Prophet ﷺ said: 'Have suhoor, for in suhoor there is blessing.'_ — Bukhari\n\n"
                    "May Allah accept your fast! 🤲"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Suhoor reminder error {user['user_id']}: {e}")


async def send_ramadan_iftar(bot: Bot):
    """Iftar reminder — sent before Maghrib (around Maghrib time)."""
    from utils.prayer_times import is_ramadan
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            ramadan = await is_ramadan(user.get("latitude", 25.2048), user.get("longitude", 55.2708))
            if not ramadan:
                continue
            times = await get_prayer_times(user["latitude"], user["longitude"])
            maghrib_time = times.get("maghrib", "18:30") if times else "18:30"
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌅 *Iftar soon — Maghrib at {maghrib_time}!*\n\n"
                    "Prepare your iftar. Don't forget the dua:\n\n"
                    "_اللَّهُمَّ لَكَ صُمْتُ وَعَلَى رِزْقِكَ أَفْطَرْتُ_\n"
                    "_O Allah! For You I fasted and upon Your provision I break my fast._\n\n"
                    "May Allah accept your fast! 🤲"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Iftar reminder error {user['user_id']}: {e}")


async def send_ramadan_tarawih(bot: Bot):
    """Tarawih reminder — after Isha (around 9 PM UAE)."""
    from utils.prayer_times import is_ramadan
    from utils.keyboards import deed_kb
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            ramadan = await is_ramadan(user.get("latitude", 25.2048), user.get("longitude", 55.2708))
            if not ramadan:
                continue
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    "🌙 *Time for Tarawih!*\n\n"
                    "The Prophet ﷺ said: 'Whoever prays Tarawih with full faith and "
                    "hoping for Allah's reward, his past sins will be forgiven.' — Bukhari\n\n"
                    "Head to the masjid or pray at home. May Allah accept! 🤲"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Tarawih reminder error {user['user_id']}: {e}")


async def send_weekly_challenge(bot: Bot):
    """Sends a weekly challenge every Monday morning."""
    import random
    challenge = random.choice(WEEKLY_CHALLENGES)
    users = await get_all_active_users()

    from utils.keyboards import challenge_kb
    for user in users:
        try:
            text = (
                f"🎯 *Weekly Challenge!*\n\n"
                f"*{challenge['title']}*\n\n"
                f"_{challenge['description']}_\n\n"
                f"🏆 Reward: *+{challenge['xp_reward']} XP*\n\n"
                "Accept the challenge and make this week count! 💪"
            )
            await bot.send_message(
                chat_id=user["user_id"], text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=challenge_kb(challenge["id"])
            )
        except Exception as e:
            logger.error(f"Challenge send error {user['user_id']}: {e}")
