"""
Command handlers v2 — full onboarding, profile, menu, groups.
"""
import logging
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from datetime import date
from utils.database import (
    upsert_user, get_user, get_user_goals, add_default_goals,
    get_streak, get_user_groups, get_today_logs
)
from utils.prayer_times import get_prayer_times, format_prayer_schedule, is_ramadan
from utils.keyboards import main_menu_kb, settings_kb, report_nav_kb, add_goal_kb
from handlers.reports import build_daily_report, build_weekly_report, build_monthly_report
from config import xp_progress, PERFORMANCE_TIERS

FARDH_KEYS   = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
PRAYER_EMOJI = {"fajr": "🌅", "dhuhr": "🌤", "asr": "🌇", "maghrib": "🌆", "isha": "🌙"}

logger = logging.getLogger(__name__)


def _level_bar(current_xp_in_level: int, needed: int, width: int = 10) -> str:
    if needed == 0:
        return "█" * width + " MAX"
    filled = round(current_xp_in_level / needed * width)
    return "█" * filled + "░" * (width - filled)


async def build_home_page(user_id: int) -> str:
    db_user = await get_user(user_id)
    if not db_user:
        return "Send /start to set up your account."

    today     = date.today()
    goals     = await get_user_goals(user_id)
    logs      = await get_today_logs(user_id)
    logged    = {l["deed_key"] for l in logs}

    # XP / level
    level, xp_in, xp_needed = xp_progress(db_user["total_xp"])
    bar = _level_bar(xp_in, xp_needed)

    # Score
    earned  = sum(l["points"] for l in logs)
    max_pts = sum(g["points"] for g in goals)
    pct     = round(earned / max_pts * 100) if max_pts else 0

    # Prayer status row
    prayer_row = "  ".join(
        f"{'✅' if k in logged else '❌'} {PRAYER_EMOJI[k]}"
        for k in FARDH_KEYS
    )
    prayers_done = sum(1 for k in FARDH_KEYS if k in logged)

    # Streaks
    fajr_streak = await get_streak(user_id, "fajr")

    # Ramadan
    ramadan = await is_ramadan(db_user["latitude"], db_user["longitude"])
    ramadan_line = ""
    if ramadan:
        fast_logged = "fast" in logged
        ramadan_line = f"\n🌙 *Ramadan* — Fast: {'✅ logged' if fast_logged else '⬜ not logged yet'}"

    # Date header
    date_str = today.strftime("%A, %d %B %Y")

    lines = [
        f"☽ *As-Salamu Alaikum, {db_user['first_name']}!*",
        f"_{date_str}_",
        ramadan_line,
        "",
        f"⭐ *Level {level}* `{bar}` {xp_in}/{xp_needed} XP",
        "",
        f"*🕌 Prayers — {prayers_done}/5*",
        prayer_row,
        "",
        f"*📊 Today: {earned}/{max_pts} pts ({pct}%)*",
    ]

    # Score tier
    for threshold, label in PERFORMANCE_TIERS:
        if pct >= threshold:
            lines.append(label)
            break

    if fajr_streak > 0:
        lines.append(f"\n🔥 Fajr streak: *{fajr_streak} day{'s' if fajr_streak != 1 else ''}*")

    return "\n".join(l for l in lines if l is not None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    from utils.database import is_new_user
    newly_joined = await is_new_user(user.id)
    await upsert_user(user.id, user.username or "", user.first_name)
    db_user = await get_user(user.id)
    is_new  = not db_user or not db_user.get("onboarding")

    if newly_joined:
        from handlers.admin import notify_admin_new_user
        await notify_admin_new_user(context.bot, user.id, user.first_name, user.username or "")

    await add_default_goals(user.id)

    if is_new:
        # First-time welcome
        times    = await get_prayer_times(db_user["latitude"], db_user["longitude"])
        schedule = "\n\n" + format_prayer_schedule(times, db_user["city"]) if times else ""
        text = (
            f"☽ *As-Salamu Alaikum, {user.first_name}!*\n\n"
            "Welcome to *NoorBot v2* — your Islamic productivity companion.\n\n"
            "I'll remind you before every prayer, track your Fardh & Sunnah deeds, "
            "give you XP, levels, weekly reports, and help you grow — day by day.\n\n"
            "📌 *Tracked by default:*\n"
            "• 5 Fardh prayers\n• Sunnah rawatib\n• Quran (1 page/day)\n• Dhikr after salah\n\n"
            "Use ⚙️ Settings to set your city for accurate prayer times."
            f"{schedule}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=main_menu_kb())
    else:
        # Returning user — show home page
        text = await build_home_page(user.id)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=main_menu_kb())


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build_home_page(update.effective_user.id)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=main_menu_kb())


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_profile(update.effective_user.id, update.message.reply_text)


async def _send_profile(user_id: int, reply_fn):
    db_user = await get_user(user_id)
    if not db_user:
        await reply_fn("User not found. Send /start first.")
        return

    level, xp_in_level, xp_needed = xp_progress(db_user["total_xp"])
    bar = _level_bar(xp_in_level, xp_needed)

    # Streaks
    fajr_streak  = await get_streak(user_id, "fajr")
    quran_streak = await get_streak(user_id, "quran")

    # Groups
    groups = await get_user_groups(user_id)
    group_text = ", ".join(g["name"] for g in groups) if groups else "None — use /settings to join one"

    text = (
        f"👤 *{db_user['first_name']}'s Profile*\n\n"
        f"⭐ *Level {level}* / 50\n"
        f"`{bar}` {xp_in_level}/{xp_needed} XP\n"
        f"💎 Total XP: *{db_user['total_xp']:,}*\n\n"
        f"🔥 Fajr streak: *{fajr_streak} days*\n"
        f"📖 Quran streak: *{quran_streak} days*\n\n"
        f"📍 City: *{db_user['city']}*\n"
        f"👥 Groups: _{group_text}_\n\n"
        f"_Joined: {db_user['joined_at']}_"
    )
    await reply_fn(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())


async def goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_goals = await get_user_goals(user_id)
    total = sum(g["points"] for g in user_goals)
    lines = ["🎯 *Your Active Goals*\n"]
    for g in user_goals:
        lines.append(f"• {g['deed_label']} — *{g['points']} pts/day*")
    lines.append(f"\n📊 Max daily score: *{total} pts*")
    lines.append("\nTap below to add more Sunnah deeds:")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=add_goal_kb()
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await profile(update, context)


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build_daily_report(update.effective_user.id)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build_weekly_report(update.effective_user.id)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())


async def monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build_monthly_report(update.effective_user.id)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = await get_user(update.effective_user.id)
    reminder_state = "🔔 On" if db_user["reminders_on"] else "🔕 Off"
    text = (
        f"⚙️ *Settings*\n\n"
        f"📍 City: *{db_user['city']}*\n"
        f"🔔 Reminders: *{reminder_state}*\n\n"
        "What would you like to change?"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=settings_kb())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *NoorBot Commands*\n\n"
        "/start — Set up your account\n"
        "/menu — Main menu\n"
        "/profile — Your level, XP & streaks\n"
        "/report — Today's performance\n"
        "/weekly — This week's summary\n"
        "/monthly — Monthly trend\n"
        "/goals — Manage your goals\n"
        "/settings — City, reminders, groups\n"
        "/leaderboard — Top users this week\n"
        "/card — Share your progress card 🌙\n"
        "/help — This message\n\n"
        "Prayer reminders fire 15 min before each salah. ☽\n"
        "_Share your location to auto-detect city & prayer times._"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.checkin import _build_leaderboard_text
    text = await _build_leaderboard_text(update.effective_user.id)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())
