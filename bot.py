"""
NoorBot v2 — Main entry point
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from handlers.commands import (
    start, menu, profile, goals, stats, report,
    weekly, monthly, settings_cmd, help_command, leaderboard_cmd, about_cmd
)
from handlers.checkin import handle_callback, handle_text, handle_location
from handlers.card import card_cmd
from handlers.admin import (
    admin_cmd, stats_admin, top10_cmd, broadcast_cmd,
    user_info_cmd, pause_user_cmd, resume_user_cmd,
    inactive_users_cmd, active_users_cmd
)
from utils.database import init_db
from config import BOT_TOKEN, TIMEZONE

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    global _loop
    _loop = asyncio.get_event_loop()

    await init_db()
    logger.info("✅ Database initialised")

    from config import ADMIN_CHAT_ID
    if ADMIN_CHAT_ID:
        logger.info(f"✅ Admin configured: {ADMIN_CHAT_ID}")
    else:
        logger.warning("⚠️  ADMIN_CHAT_ID is not set — admin commands will be disabled! Set it in Railway env vars.")

    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # misfire_grace_time=300: if the bot restarts and a job missed its window
    # by more than 5 minutes, drop it instead of firing all at once on startup.
    _grace = 300  # seconds

    scheduler.add_job(
        lambda: _run(send_daily_reports, application),
        CronTrigger(hour=22, minute=30, timezone=tz), id="daily_reports",
        misfire_grace_time=_grace, coalesce=True,
    )
    scheduler.add_job(
        lambda: _run(send_weekly_reports, application),
        CronTrigger(day_of_week="fri", hour=14, minute=30, timezone=tz), id="weekly_reports",
        misfire_grace_time=_grace, coalesce=True,
    )
    scheduler.add_job(
        lambda: _run(send_monthly_reports, application),
        CronTrigger(day=1, hour=9, minute=0, timezone=tz), id="monthly_reports",
        misfire_grace_time=_grace, coalesce=True,
    )
    scheduler.add_job(
        lambda: _run(check_reminders, application),
        CronTrigger(minute="*", timezone=tz), id="prayer_check",
        misfire_grace_time=90, coalesce=True,
    )
    # Morning dua/hadith + adhkar — 15 min after Fajr (~5:45 AM UAE)
    scheduler.add_job(
        lambda: _run(morning_content, application),
        CronTrigger(hour=5, minute=45, timezone=tz), id="morning_content",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Evening adhkar — around Maghrib (6:00 PM UAE, adjust per season)
    scheduler.add_job(
        lambda: _run(evening_adhkar, application),
        CronTrigger(hour=18, minute=15, timezone=tz), id="evening_adhkar",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Sleep adhkar — 10:00 PM
    scheduler.add_job(
        lambda: _run(sleep_adhkar, application),
        CronTrigger(hour=22, minute=0, timezone=tz), id="sleep_adhkar",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Weekly challenge — every Monday 7 AM
    scheduler.add_job(
        lambda: _run(weekly_challenge, application),
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=tz), id="weekly_challenge",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Ramadan suhoor reminder — 3:30 AM
    scheduler.add_job(
        lambda: _run(ramadan_suhoor, application),
        CronTrigger(hour=3, minute=30, timezone=tz), id="ramadan_suhoor",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Ramadan iftar reminder — 6:10 PM (before typical Maghrib)
    scheduler.add_job(
        lambda: _run(ramadan_iftar, application),
        CronTrigger(hour=18, minute=10, timezone=tz), id="ramadan_iftar",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Period mode expiration check — 12:01 AM daily
    scheduler.add_job(
        lambda: _run(check_period_expirations, application),
        CronTrigger(hour=0, minute=1, timezone=tz), id="period_check",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Friday morning reminder — 7:00 AM every Friday
    scheduler.add_job(
        lambda: _run(friday_morning, application),
        CronTrigger(day_of_week="fri", hour=7, minute=0, timezone=tz), id="friday_morning",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Friday Jumu'ah reminder — 11:30 AM every Friday
    scheduler.add_job(
        lambda: _run(friday_jumua, application),
        CronTrigger(day_of_week="fri", hour=11, minute=30, timezone=tz), id="friday_jumua",
        misfire_grace_time=_grace, coalesce=True,
    )
    # Friday post-Asr duʿa / Sa'at al-Istijabah — 4:30 PM every Friday
    scheduler.add_job(
        lambda: _run(friday_asr_dua, application),
        CronTrigger(day_of_week="fri", hour=16, minute=30, timezone=tz), id="friday_asr_dua",
        misfire_grace_time=_grace, coalesce=True,
    )

    scheduler.start()
    logger.info("✅ Scheduler started")


_loop = None

def _run(coro_fn, application):
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(coro_fn(application), _loop)
    else:
        logger.warning(f"_run: no event loop available for {coro_fn.__name__}")


async def send_daily_reports(app):
    from handlers.reports import send_all_daily_reports
    await send_all_daily_reports(app.bot)

async def send_weekly_reports(app):
    from handlers.reports import send_all_weekly_reports
    await send_all_weekly_reports(app.bot)

async def send_monthly_reports(app):
    from handlers.reports import send_all_monthly_reports
    await send_all_monthly_reports(app.bot)

async def check_reminders(app):
    from handlers.reminders import check_and_send_reminders
    await check_and_send_reminders(app.bot)

async def morning_content(app):
    from handlers.reminders import send_morning_content
    await send_morning_content(app.bot)

async def weekly_challenge(app):
    from handlers.reminders import send_weekly_challenge
    await send_weekly_challenge(app.bot)

async def evening_adhkar(app):
    from handlers.reminders import send_evening_adhkar_reminder
    await send_evening_adhkar_reminder(app.bot)

async def sleep_adhkar(app):
    from handlers.reminders import send_sleep_adhkar_reminder
    await send_sleep_adhkar_reminder(app.bot)

async def ramadan_suhoor(app):
    from handlers.reminders import send_ramadan_suhoor
    await send_ramadan_suhoor(app.bot)

async def ramadan_iftar(app):
    from handlers.reminders import send_ramadan_iftar
    await send_ramadan_iftar(app.bot)

async def friday_morning(app):
    from handlers.reminders import send_friday_morning
    await send_friday_morning(app.bot)

async def friday_jumua(app):
    from handlers.reminders import send_friday_jumua
    await send_friday_jumua(app.bot)

async def friday_asr_dua(app):
    from handlers.reminders import send_friday_asr_dua
    await send_friday_asr_dua(app.bot)

async def check_period_expirations(app):
    from utils.database import get_users_period_ending_today, deactivate_period_mode
    from telegram.constants import ParseMode
    users = await get_users_period_ending_today()
    for user in users:
        await deactivate_period_mode(user["user_id"])
        try:
            await app.bot.send_message(
                chat_id=user["user_id"],
                text=(
                    "🌸 *Welcome back!*\n\n"
                    "Your tracking pause has ended. Your streaks are protected — "
                    "Alhamdulillah! 💚\n\n"
                    "May Allah make it easy for you. 🤲"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Period expiry notify {user['user_id']}: {e}")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("menu",        menu))
    app.add_handler(CommandHandler("profile",     profile))
    app.add_handler(CommandHandler("goals",       goals))
    app.add_handler(CommandHandler("stats",       stats))
    app.add_handler(CommandHandler("report",      report))
    app.add_handler(CommandHandler("weekly",      weekly))
    app.add_handler(CommandHandler("monthly",     monthly))
    app.add_handler(CommandHandler("settings",    settings_cmd))
    app.add_handler(CommandHandler("help",        help_command))
    app.add_handler(CommandHandler("about",       about_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("card",        card_cmd))

    # Admin commands
    app.add_handler(CommandHandler("admin",       admin_cmd))
    app.add_handler(CommandHandler("stats_admin", stats_admin))
    app.add_handler(CommandHandler("top10",       top10_cmd))
    app.add_handler(CommandHandler("broadcast",   broadcast_cmd))
    app.add_handler(CommandHandler("user",        user_info_cmd))
    app.add_handler(CommandHandler("pause_user",  pause_user_cmd))
    app.add_handler(CommandHandler("resume_user", resume_user_cmd))
    app.add_handler(CommandHandler("inactive",    inactive_users_cmd))
    app.add_handler(CommandHandler("users",       active_users_cmd))

    # Adhkar command + callbacks
    from handlers.adhkar import handle_adhkar_callback, adhkar_menu_cmd
    app.add_handler(CommandHandler("adhkar", adhkar_menu_cmd))
    app.add_handler(CallbackQueryHandler(handle_adhkar_callback, pattern="^adhkar:"))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Location sharing — auto-detect city
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Free text (city input, group name, group code)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🌙 NoorBot v2 running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
