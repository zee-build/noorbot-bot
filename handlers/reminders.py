"""
Reminders v2 — prayer reminders, missed prayer follow-ups,
morning dua/hadith, weekly challenge drops.
"""
import logging
from datetime import date, datetime
from telegram import Bot
from telegram.constants import ParseMode

from utils.database import (
    get_all_active_users, mark_reminder_sent,
    get_today_logs, is_period_mode,
    get_uninformed_female_users, mark_period_notified,
    mark_broadcast_sent,
)
from utils.prayer_times import (
    get_prayer_times, minutes_until_prayer, minutes_since_prayer,
    PRAYER_KEYS, PRAYER_EMOJIS, PRAYER_NAMES, to_12h
)
from utils.keyboards import prayer_checkin_kb
from config import REMINDER_MINUTES, MORNING_CONTENT, WEEKLY_CHALLENGES, get_user_timezone
import pytz

logger = logging.getLogger(__name__)


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
    from utils.prayer_times import is_ramadan
    # Only run period-mode notification once per hour (on the hour)
    if datetime.now().minute == 0:
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

            times = await get_prayer_times(user["latitude"], user["longitude"], country=user.get("country", ""))
            if not times:
                continue
            tz = get_user_timezone(user.get("country", ""))

            for key in PRAYER_KEYS:
                mins_until = minutes_until_prayer(times[key], tz)

                # ── Pre-prayer reminder (15 min before) ──
                if REMINDER_MINUTES <= mins_until <= REMINDER_MINUTES + 1:
                    sent = await mark_reminder_sent(user["user_id"], key, today)
                    if sent:
                        await _send_reminder(bot, user["user_id"], key, times[key], user["city"])

        except Exception as e:
            logger.error(f"Reminder error user {user['user_id']}: {e}")


async def _send_reminder(bot: Bot, chat_id: int, key: str, prayer_time: str, city: str):
    emoji = PRAYER_EMOJIS[key]
    name  = PRAYER_NAMES[key]
    text = (
        f"{emoji} *{name} — {REMINDER_MINUTES} min*\n"
        f"🕐 {to_12h(prayer_time)} · {city}"
    )
    await bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=prayer_checkin_kb(key)
    )



async def send_morning_content(bot: Bot):
    """Sends morning adhkar prompt + dua/hadith after Fajr."""
    from handlers.adhkar import send_morning_adhkar_prompt
    from utils.prayer_times import is_ramadan
    today = date.today().isoformat()
    if not await mark_broadcast_sent("morning_content", today):
        return
    users = await get_all_active_users()
    today = date.today()
    content = MORNING_CONTENT[today.toordinal() % len(MORNING_CONTENT)]

    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌅 *{today.strftime('%A, %d %B')}*\n\n"
                    f"_{content['hadith']}_\n"
                    f"📚 {content['source']}"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            await send_morning_adhkar_prompt(bot, user["user_id"])
        except Exception as e:
            logger.error(f"Morning content error {user['user_id']}: {e}")


async def send_evening_adhkar_reminder(bot: Bot):
    """Sends evening adhkar prompt around Maghrib time."""
    from handlers.adhkar import send_evening_adhkar_prompt
    today = date.today().isoformat()
    if not await mark_broadcast_sent("evening_adhkar", today):
        return
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
    today = date.today().isoformat()
    if not await mark_broadcast_sent("sleep_adhkar", today):
        return
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
    today = date.today().isoformat()
    if not await mark_broadcast_sent("ramadan_suhoor", today):
        return
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            ramadan = await is_ramadan(user.get("latitude", 25.2048), user.get("longitude", 55.2708), country=user.get("country", ""))
            if not ramadan:
                continue
            times = await get_prayer_times(user["latitude"], user["longitude"], country=user.get("country", ""))
            fajr_time = times.get("fajr", "05:00") if times else "05:00"
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌙 *Suhoor Time!*\n\n"
                    f"Fajr is at *{to_12h(fajr_time)}* — eat & drink before then.\n\n"
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
    today = date.today().isoformat()
    if not await mark_broadcast_sent("ramadan_iftar", today):
        return
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            ramadan = await is_ramadan(user.get("latitude", 25.2048), user.get("longitude", 55.2708), country=user.get("country", ""))
            if not ramadan:
                continue
            times = await get_prayer_times(user["latitude"], user["longitude"], country=user.get("country", ""))
            maghrib_time = times.get("maghrib", "18:30") if times else "18:30"
            await bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌅 *Iftar soon — Maghrib at {to_12h(maghrib_time)}!*\n\n"
                    "Prepare your iftar. Don't forget the dua:\n\n"
                    "_اللَّهُمَّ لَكَ صُمْتُ وَعَلَى رِزْقِكَ أَفْطَرْتُ_\n"
                    "_O Allah! For You I fasted and upon Your provision I break my fast._\n\n"
                    "May Allah accept your fast! 🤲"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Iftar reminder error {user['user_id']}: {e}")


async def send_friday_morning(bot: Bot):
    """Friday morning reminder — sent at 7:00 AM."""
    today = date.today()
    if today.weekday() != 4:  # 4 = Friday
        return
    if not await mark_broadcast_sent("friday_morning", today.isoformat()):
        return
    users = await get_all_active_users()
    text = (
        "🌿 *Jumu'ah Mubarak!*\n\n"
        "• Perform ghusl · Read Surah Al-Kahf\n"
        "• Increase salawat upon the Prophet ﷺ\n"
        "• Make duʿa — today is a blessed day 🤍\n\n"
        "_'The best day on which the sun has risen is Friday.'_ — Muslim"
    )
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            await bot.send_message(chat_id=user["user_id"], text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Friday morning error {user['user_id']}: {e}")


async def send_friday_jumua(bot: Bot):
    """Friday Jumu'ah reminder — sent at 11:30 AM."""
    today = date.today()
    if today.weekday() != 4:
        return
    if not await mark_broadcast_sent("friday_jumua", today.isoformat()):
        return
    users = await get_all_active_users()
    text = (
        "🕌 *Jumu'ah is soon — go early!*\n\n"
        "_'Whoever goes early to Jumu'ah is like one who offered a camel for Allah's sake.'_ — Bukhari\n\n"
        "May Allah accept your Jumu'ah. 🤲"
    )
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            await bot.send_message(chat_id=user["user_id"], text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Friday Jumu'ah error {user['user_id']}: {e}")


async def send_friday_asr_dua(bot: Bot):
    """Friday post-Asr duʿa reminder — Sa'at al-Istijabah (4:30 PM)."""
    today = date.today()
    if today.weekday() != 4:
        return
    if not await mark_broadcast_sent("friday_asr_dua", today.isoformat()):
        return
    users = await get_all_active_users()
    text = (
        "🤲 *Sa'at al-Istijabah*\n\n"
        "After Asr until Maghrib — the hour of answered duʿa. Don't miss it.\n\n"
        "_'On Friday there is a time when, if a Muslim asks Allah for something good, He will give it.'_ — Bukhari\n\n"
        "May Allah accept your duʿa. 🌿"
    )
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            await bot.send_message(chat_id=user["user_id"], text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Friday Asr duʿa error {user['user_id']}: {e}")


# ── Single-user versions for test alerts ──────────────────

async def send_morning_adhkar_prompt_single(bot: Bot, chat_id: int):
    from handlers.adhkar import send_morning_adhkar_prompt
    await send_morning_adhkar_prompt(bot, chat_id)

async def send_evening_adhkar_prompt_single(bot: Bot, chat_id: int):
    from handlers.adhkar import send_evening_adhkar_prompt
    await send_evening_adhkar_prompt(bot, chat_id)

async def send_sleep_adhkar_prompt_single(bot: Bot, chat_id: int):
    from handlers.adhkar import send_sleep_adhkar_prompt
    await send_sleep_adhkar_prompt(bot, chat_id)

async def send_weekly_challenge_single(bot: Bot, chat_id: int):
    import random
    from config import WEEKLY_CHALLENGES
    from utils.keyboards import challenge_kb
    challenge = random.choice(WEEKLY_CHALLENGES)
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎯 *Weekly Challenge!*\n\n"
            f"*{challenge['title']}*\n\n"
            f"_{challenge['description']}_\n\n"
            f"🏆 Reward: *+{challenge['xp_reward']} XP*\n\n"
            "Accept the challenge and make this week count! 💪"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=challenge_kb(challenge["id"])
    )

async def send_friday_morning_single(bot: Bot, chat_id: int):
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🌿 *Jumu'ah Mubarak!*\n\n"
            "• Perform ghusl · Read Surah Al-Kahf\n"
            "• Increase salawat upon the Prophet ﷺ\n"
            "• Make duʿa — today is a blessed day 🤍\n\n"
            "_'The best day on which the sun has risen is Friday.'_ — Muslim"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

async def send_friday_jumua_single(bot: Bot, chat_id: int):
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🕌 *Jumu'ah is soon — go early!*\n\n"
            "_'Whoever goes early to Jumu'ah is like one who offered a camel for Allah's sake.'_ — Bukhari\n\n"
            "May Allah accept your Jumu'ah. 🤲"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

async def send_friday_asr_dua_single(bot: Bot, chat_id: int):
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🤲 *Sa'at al-Istijabah*\n\n"
            "After Asr until Maghrib — the hour of answered duʿa. Don't miss it.\n\n"
            "_'On Friday there is a time when, if a Muslim asks Allah for something good, He will give it.'_ — Bukhari\n\n"
            "May Allah accept your duʿa. 🌿"
        ),
        parse_mode=ParseMode.MARKDOWN
    )


async def send_eid_mubarak(bot: Bot):
    """One-time Eid al-Fitr broadcast — location-aware sunrise time."""
    today = date.today().isoformat()
    if not await mark_broadcast_sent("eid_alfitr_2026", today):
        return
    users = await get_all_active_users()
    for user in users:
        try:
            times = await get_prayer_times(user["latitude"], user["longitude"], country=user.get("country", ""))
            city = user.get("city", "")

            text = (
                "🌙✨ *Eid al-Fitr Mubarak!*\n\n"
                "_Taqabbal Allahu minnaa wa minkum —_\n"
                "_May Allah accept from us and from you._ 🤲"
            )
            await bot.send_message(
                chat_id=user["user_id"],
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Eid blast error {user['user_id']}: {e}")


async def send_weekly_challenge(bot: Bot):
    """Sends a weekly challenge every Monday morning."""
    import random
    today = date.today().isoformat()
    if not await mark_broadcast_sent("weekly_challenge", today):
        return
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


async def send_daily_prayer_times(bot: Bot):
    """Sends each user their prayer schedule at noon."""
    from utils.prayer_times import format_prayer_schedule
    today = date.today().isoformat()
    if not await mark_broadcast_sent("daily_prayer_times", today):
        return
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            times = await get_prayer_times(user["latitude"], user["longitude"], country=user.get("country", ""))
            if not times:
                continue
            await bot.send_message(
                chat_id=user["user_id"],
                text=format_prayer_schedule(times, user.get("city", "")),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error(f"Daily prayer times error {user['user_id']}: {e}")


async def send_daily_prayer_checkin(bot: Bot):
    """9 PM consolidated check-in — one message showing all prayers for the day."""
    from utils.keyboards import prayer_log_kb
    today = date.today().isoformat()
    if not await mark_broadcast_sent("daily_prayer_checkin", today):
        return
    users = await get_all_active_users()
    for user in users:
        if not user.get("reminders_on", 1):
            continue
        try:
            if await is_period_mode(user["user_id"]):
                continue
            logs = await get_today_logs(user["user_id"])
            logged = {l["deed_key"] for l in logs}
            prayers_done = sum(1 for k in ["fajr", "dhuhr", "asr", "maghrib", "isha"] if k in logged)
            if prayers_done == 5:
                continue  # All prayers logged — no need to send
            await bot.send_message(
                chat_id=user["user_id"],
                text=f"🌙 *End of day check-in — {prayers_done}/5 prayers logged*\n\nAny you haven't logged yet?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=prayer_log_kb(logged),
            )
        except Exception as e:
            logger.error(f"Daily checkin error {user['user_id']}: {e}")
