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
    weekly, monthly, settings_cmd, help_command, leaderboard_cmd
)
from handlers.checkin import handle_callback, handle_text, handle_location
from handlers.card import card_cmd
from handlers.admin import (
    admin_cmd, stats_admin, top10_cmd, broadcast_cmd,
    user_info_cmd, pause_user_cmd, resume_user_cmd
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

    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    scheduler.add_job(
        lambda: _run(send_daily_reports, application),
        CronTrigger(hour=22, minute=30, timezone=tz), id="daily_reports"
    )
    scheduler.add_job(
        lambda: _run(send_weekly_reports, application),
        CronTrigger(day_of_week="fri", hour=14, minute=30, timezone=tz), id="weekly_reports"
    )
    scheduler.add_job(
        lambda: _run(send_monthly_reports, application),
        CronTrigger(day=1, hour=9, minute=0, timezone=tz), id="monthly_reports"
    )
    scheduler.add_job(
        lambda: _run(check_reminders, application),
        CronTrigger(minute="*", timezone=tz), id="prayer_check"
    )
    # Morning dua/hadith + adhkar — 15 min after Fajr (~5:45 AM UAE)
    scheduler.add_job(
        lambda: _run(morning_content, application),
        CronTrigger(hour=5, minute=45, timezone=tz), id="morning_content"
    )
    # Evening adhkar — around Maghrib (6:00 PM UAE, adjust per season)
    scheduler.add_job(
        lambda: _run(evening_adhkar, application),
        CronTrigger(hour=18, minute=15, timezone=tz), id="evening_adhkar"
    )
    # Sleep adhkar — 10:00 PM
    scheduler.add_job(
        lambda: _run(sleep_adhkar, application),
        CronTrigger(hour=22, minute=0, timezone=tz), id="sleep_adhkar"
    )
    # Weekly challenge — every Monday 7 AM
    scheduler.add_job(
        lambda: _run(weekly_challenge, application),
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=tz), id="weekly_challenge"
    )
    # Ramadan suhoor reminder — 3:30 AM
    scheduler.add_job(
        lambda: _run(ramadan_suhoor, application),
        CronTrigger(hour=3, minute=30, timezone=tz), id="ramadan_suhoor"
    )
    # Ramadan iftar reminder — 6:10 PM (before typical Maghrib)
    scheduler.add_job(
        lambda: _run(ramadan_iftar, application),
        CronTrigger(hour=18, minute=10, timezone=tz), id="ramadan_iftar"
    )
    # Ramadan tarawih reminder — 9:00 PM
    scheduler.add_job(
        lambda: _run(ramadan_tarawih, application),
        CronTrigger(hour=21, minute=0, timezone=tz), id="ramadan_tarawih"
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

async def ramadan_tarawih(app):
    from handlers.reminders import send_ramadan_tarawih
    await send_ramadan_tarawih(app.bot)


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

    # Callbacks — adhkar prefix first (more specific), then general
    from handlers.adhkar import handle_adhkar_callback
    app.add_handler(CallbackQueryHandler(handle_adhkar_callback, pattern="^adhkar:"))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Location sharing — auto-detect city
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Free text (city input, group name, group code)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🌙 NoorBot v2 running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
