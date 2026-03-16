"""
Callback handler v2 — prayer checkins, deeds, XP, level-up, city, groups, leaderboard.
"""
import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.database import (
    log_deed, get_user_goals, get_today_logs, add_goal,
    add_xp, get_user, update_user_location, update_user_reminders,
    create_group, join_group, get_user_groups, get_group_leaderboard,
    get_all_active_users, reset_progress,
    set_period_mode, deactivate_period_mode, is_period_mode
)
from utils.prayer_times import get_prayer_times, format_prayer_schedule, is_ramadan
from utils.keyboards import (
    deed_kb, add_goal_kb, main_menu_kb, settings_kb,
    report_nav_kb, prayer_checkin_kb, missed_followup_kb, reset_confirm_kb,
    prayer_log_kb, after_prayer_kb, FARDH_KEYS
)
from handlers.reports import build_daily_report, build_weekly_report, build_monthly_report
from config import POINTS, LEVEL_MILESTONES, xp_progress

logger = logging.getLogger(__name__)

PRAYER_LABELS = {"fajr":"Fajr","dhuhr":"Dhuhr","asr":"Asr","maghrib":"Maghrib","isha":"Isha"}

# Track pending inputs per user: {user_id: "awaiting_city" | "awaiting_group_name" | "awaiting_group_code"}
PENDING = {}


def _level_bar(xp_in: int, needed: int, width: int = 10) -> str:
    if needed == 0:
        return "█" * width + " MAX"
    filled = round(xp_in / needed * width)
    return "█" * filled + "░" * (width - filled)


async def _level_up_message(bot, chat_id: int, new_level: int, total_xp: int):
    milestone = LEVEL_MILESTONES.get(new_level, "")
    _, xp_in, xp_needed = xp_progress(total_xp)
    bar = _level_bar(xp_in, xp_needed)
    text = (
        f"🎉 *Level Up! You're now Level {new_level}!*\n\n"
        f"`{bar}` {xp_in}/{xp_needed} XP\n\n"
        + (f"_{milestone}_\n\n" if milestone else "")
        + "May Allah bless your consistency. 💚"
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    try:
        await _handle_callback_inner(query, data, user_id, chat_id, context)
    except Exception as e:
        logger.error(f"Callback error [{data}] for {user_id}: {e}", exc_info=True)
        try:
            await query.answer("Something went wrong. Please try again.", show_alert=True)
        except Exception:
            pass


async def _handle_callback_inner(query, data, user_id, chat_id, context):

    # ── Prayer checkin ────────────────────────────────────
    if data.startswith("pray:"):
        _, prayer_key, mode = data.split(":")
        label = PRAYER_LABELS.get(prayer_key, prayer_key.capitalize())
        pts   = POINTS.get(prayer_key, 3)
        jamaah = 1 if mode == "jamaah" else 0

        if mode == "missed":
            await query.edit_message_text(
                f"😔 *{label} — Missed*\n\n"
                "No worries, Allah is Most Forgiving. Make it up as Qada when you can.\n\n"
                "_'Verily, with hardship comes ease.'_ — Quran 94:5\n\n"
                "Catch the next prayer on time. 🤲",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=report_nav_kb()
            )
            return

        logged, xp = await log_deed(user_id, prayer_key, label, pts, jamaah)
        if not logged:
            await query.answer(f"✅ {label} already logged today!", show_alert=True)
            return

        new_level, leveled_up, total_xp = await add_xp(user_id, xp)
        total_pts = pts + (1 if jamaah else 0)
        jamaah_txt = "\n🕌 _BarakAllahu feek for praying with the congregation!_" if jamaah else ""

        _, xp_in, xp_needed = xp_progress(total_xp)
        bar = _level_bar(xp_in, xp_needed)

        logs        = await get_today_logs(user_id)
        logged_keys = {l["deed_key"] for l in logs}
        logged_prayers = {k for k in logged_keys if k in FARDH_KEYS}
        prayers_left   = 5 - len(logged_prayers)

        # Remaining non-prayer deeds
        goals = await get_user_goals(user_id)
        remaining_deeds = [g for g in goals if g["deed_key"] not in logged_keys and g["deed_key"] not in FARDH_KEYS]

        text = (
            f"✅ *{label} logged!*{jamaah_txt}\n"
            f"*+{total_pts} pts · +{xp} XP*\n\n"
            f"⭐ Level {new_level} `{bar}` {xp_in}/{xp_needed} XP\n\n"
        )
        if prayers_left == 0 and not remaining_deeds:
            text += "🌟 *All done today! MashaAllah!* 🎊"
        else:
            if prayers_left > 0:
                text += f"🕌 *{prayers_left} prayer{'s' if prayers_left > 1 else ''} left today*\n"
            if remaining_deeds:
                text += f"📿 *Deeds left:* {', '.join(g['deed_label'] for g in remaining_deeds[:3])}"

        ramadan = await is_ramadan()
        kb = after_prayer_kb(prayer_key, logged_prayers, ramadan)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

        if leveled_up:
            await _level_up_message(context.bot, chat_id, new_level, total_xp)

    # ── Deed checkin ──────────────────────────────────────
    elif data.startswith("deed:"):
        _, deed_key, pts_str = data.split(":")
        pts = int(pts_str)
        goals = await get_user_goals(user_id)
        goal  = next((g for g in goals if g["deed_key"] == deed_key), None)
        if not goal:
            await query.answer("Goal not found.", show_alert=True)
            return

        logged, xp = await log_deed(user_id, deed_key, goal["deed_label"], pts)
        if not logged:
            await query.answer(f"✅ Already logged today!", show_alert=True)
            return

        new_level, leveled_up, total_xp = await add_xp(user_id, xp)
        await query.answer(f"✅ +{pts} pts · +{xp} XP", show_alert=False)

        logs        = await get_today_logs(user_id)
        logged_keys = {l["deed_key"] for l in logs}
        await query.edit_message_reply_markup(deed_kb(goals, logged_keys))

        if leveled_up:
            await _level_up_message(context.bot, chat_id, new_level, total_xp)

    # ── Add goal ──────────────────────────────────────────
    elif data.startswith("addgoal:"):
        parts = data.split(":", 3)
        deed_key, pts, label = parts[1], int(parts[2]), parts[3]
        existing = await get_user_goals(user_id)
        if any(g["deed_key"] == deed_key for g in existing):
            await query.answer("Already in your goals! ✅", show_alert=True)
            return
        from utils.database import add_goal as _add
        await _add(user_id, deed_key, label, pts)
        await query.answer(f"✅ {label} added!", show_alert=False)
        updated_goals = await get_user_goals(user_id)
        existing_keys = {g["deed_key"] for g in updated_goals}
        await query.edit_message_text(
            f"✅ *{label}* added!\n\n+{pts} pts every day you complete it.\n\nAdd another?",
            parse_mode=ParseMode.MARKDOWN, reply_markup=add_goal_kb(existing_keys)
        )

    # ── Snooze ────────────────────────────────────────────
    elif data.startswith("snooze:"):
        _, prayer_key, mins_str = data.split(":")
        label = PRAYER_LABELS.get(prayer_key, prayer_key.capitalize())
        mins  = int(mins_str)
        if context.job_queue is None:
            await query.edit_message_text(
                "⚠️ Snooze unavailable — job queue not running.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        # Cancel any existing snooze for this user+prayer
        for job in context.job_queue.get_jobs_by_name(f"snooze_{user_id}_{prayer_key}"):
            job.schedule_removal()
        context.job_queue.run_once(
            _snooze_job,
            when=mins * 60,
            chat_id=chat_id,
            user_id=user_id,
            data={"prayer_key": prayer_key, "label": label},
            name=f"snooze_{user_id}_{prayer_key}"
        )
        await query.edit_message_text(
            f"⏰ *Snoozed!* I'll remind you about *{label}* in {mins} minutes. 🤲",
            parse_mode=ParseMode.MARKDOWN
        )

    # ── Manual prayer selection (from prayer_log_kb) ──────
    elif data.startswith("praymenu:"):
        prayer_key = data.split(":")[1]
        label = PRAYER_LABELS.get(prayer_key, prayer_key.capitalize())
        await query.edit_message_text(
            f"🕌 *{label}*\n\nHow did you pray?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=prayer_checkin_kb(prayer_key)
        )

    elif data == "noop":
        pass  # tapping an already-added goal — do nothing

    elif data.startswith("pray_done:"):
        prayer_key = data.split(":")[1]
        label = PRAYER_LABELS.get(prayer_key, prayer_key.capitalize())
        await query.answer(f"✅ {label} already logged today!", show_alert=True)

    # ── Dismiss ───────────────────────────────────────────
    elif data.startswith("dismiss:"):
        await query.edit_message_reply_markup(None)

    # ── View shortcuts ────────────────────────────────────
    elif data.startswith("view:"):
        view = data.split(":")[1]

        if view in ("menu", "home"):
            from handlers.commands import build_home_page
            text = await build_home_page(user_id)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                          reply_markup=main_menu_kb())
        elif view == "today":
            text = await build_daily_report(user_id)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())
        elif view == "weekly":
            text = await build_weekly_report(user_id)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())
        elif view == "monthly":
            text = await build_monthly_report(user_id)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())
        elif view == "profile":
            from handlers.commands import _send_profile
            await _send_profile(user_id, query.edit_message_text)
        elif view == "goals":
            goals = await get_user_goals(user_id)
            existing_keys = {g["deed_key"] for g in goals}
            non_prayer = [g for g in goals if g["deed_key"] not in FARDH_KEYS]
            lines = ["🎯 *Your Active Goals*\n"]
            lines += [f"• {g['deed_label']} — *{g['points']} pts*" for g in non_prayer]
            lines.append("\n*Add more:*")
            await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=add_goal_kb(existing_keys))
        elif view == "settings":
            db_user = await get_user(user_id)
            state = "🔔 On" if db_user["reminders_on"] else "🔕 Off"
            await query.edit_message_text(
                f"⚙️ *Settings*\n\n📍 City: *{db_user['city']}*\n🔔 Reminders: *{state}*\n\nWhat to change?",
                parse_mode=ParseMode.MARKDOWN, reply_markup=settings_kb(gender=db_user.get("gender", "unset"))
            )
        elif view == "prayers":
            logs = await get_today_logs(user_id)
            logged_prayers = {l["deed_key"] for l in logs if l["deed_key"] in FARDH_KEYS}
            done_count = len(logged_prayers)
            await query.edit_message_text(
                f"🕌 *Prayer Check-in*\n\n"
                f"_{done_count}/5 prayers logged today_\n\n"
                "Tap an unlogged prayer to check in:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=prayer_log_kb(logged_prayers)
            )
        elif view == "deeds":
            goals = await get_user_goals(user_id)
            logs  = await get_today_logs(user_id)
            logged_keys = {l["deed_key"] for l in logs}
            sunnah_goals = [g for g in goals if g["deed_key"] not in FARDH_KEYS]
            done_count = sum(1 for g in sunnah_goals if g["deed_key"] in logged_keys)
            await query.edit_message_text(
                f"📿 *Sunnah & Voluntary Deeds*\n\n"
                f"_{done_count}/{len(sunnah_goals)} completed today_\n\n"
                "Tap to log:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=deed_kb(goals, logged_keys)
            )
        elif view == "leaderboard":
            text = await _build_leaderboard_text(user_id)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=report_nav_kb())

    # ── Settings actions ──────────────────────────────────
    elif data.startswith("settings:"):
        action = data.split(":")[1]

        if action == "city":
            PENDING[user_id] = "awaiting_city"
            await query.edit_message_text(
                "📍 *Change City*\n\n"
                "Type your city name and I'll update your prayer times.\n\n"
                "_Example: Abu Dhabi, London, Karachi_",
                parse_mode=ParseMode.MARKDOWN
            )
        elif action == "addgoal":
            existing = await get_user_goals(user_id)
            existing_keys = {g["deed_key"] for g in existing}
            await query.edit_message_text(
                "➕ *Add a Sunnah Deed*\n\nChoose from the list:",
                parse_mode=ParseMode.MARKDOWN, reply_markup=add_goal_kb(existing_keys)
            )
        elif action == "pause":
            await update_user_reminders(user_id, False)
            await query.edit_message_text("🔕 *Reminders paused.*\n\nUse /settings to resume.", parse_mode=ParseMode.MARKDOWN)
        elif action == "resume":
            await update_user_reminders(user_id, True)
            await query.edit_message_text("🔔 *Reminders resumed!* You'll get notified before each prayer.", parse_mode=ParseMode.MARKDOWN)
        elif action == "creategroup":
            PENDING[user_id] = "awaiting_group_name"
            await query.edit_message_text(
                "👥 *Create a Group*\n\n"
                "Type a name for your group and I'll create it with an invite code.\n\n"
                "_Example: Masjid Al-Noor Friends_",
                parse_mode=ParseMode.MARKDOWN
            )
        elif action == "joingroup":
            PENDING[user_id] = "awaiting_group_code"
            await query.edit_message_text(
                "🔗 *Join a Group*\n\n"
                "Type the 6-character invite code your friend shared with you.",
                parse_mode=ParseMode.MARKDOWN
            )
        elif action == "reset":
            await query.edit_message_text(
                "⚠️ *Reset Progress*\n\n"
                "This will permanently delete:\n"
                "• All your deed logs\n"
                "• Your XP and level\n"
                "• Your daily scores\n\n"
                "Your city, reminders, and group memberships will be kept.\n\n"
                "_This cannot be undone._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reset_confirm_kb()
            )
        elif action == "periodmode":
            in_period = await is_period_mode(user_id)
            if in_period:
                await deactivate_period_mode(user_id)
                await query.edit_message_text(
                    "✅ *Tracking resumed.*\n\nWelcome back! Prayer reminders are active again.\n\n"
                    "May Allah accept your worship and grant you ease. 🤲",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_kb()
                )
            else:
                PENDING[user_id] = "awaiting_period_days"
                await query.edit_message_text(
                    "🌙 *Pause Tracking*\n\n"
                    "Prayer and Quran reminders will be paused and your streaks will be protected.\n\n"
                    "You can still earn points for adhkar, dhikr, sadaqah, and other deeds.\n\n"
                    "How many days would you like to pause for?\n"
                    "_Type a number between 1 and 10_",
                    parse_mode=ParseMode.MARKDOWN
                )

        elif action == "gender_male":
            from utils.database import set_user_gender
            await set_user_gender(user_id, "male")
            await query.edit_message_text("✅ Got it! Your profile has been updated.", parse_mode=ParseMode.MARKDOWN)

        elif action == "gender_female":
            from utils.database import set_user_gender
            await set_user_gender(user_id, "female")
            await query.edit_message_text("✅ Got it! Your profile has been updated.", parse_mode=ParseMode.MARKDOWN)

        elif action == "reset_confirm":
            await reset_progress(user_id)
            await query.edit_message_text(
                "✅ *Progress reset.*\n\n"
                "Your logs, XP, and level have been cleared. Fresh start! 🌱\n\n"
                "May Allah make it easy for you.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_kb()
            )
        elif action == "test_alerts":
            await query.edit_message_text(
                "🧪 *Sending all test alerts...*\n\nCheck the chat for each one.",
                parse_mode=ParseMode.MARKDOWN
            )
            from handlers.reminders import (
                _send_reminder, _send_missed_followup,
                send_morning_content, send_evening_adhkar_reminder, send_sleep_adhkar_reminder,
                send_weekly_challenge
            )
            from utils.prayer_times import get_prayer_times
            db_user = await get_user(user_id)
            times = await get_prayer_times(db_user["latitude"], db_user["longitude"])
            bot = context.bot

            # Prayer reminder (Fajr)
            if times:
                await _send_reminder(bot, chat_id, "fajr", times.get("fajr", "05:30"), db_user["city"])
            # Missed prayer follow-up (Asr)
            await _send_missed_followup(bot, chat_id, "asr")
            # Morning content
            await send_morning_content(bot)
            # Evening adhkar
            await send_evening_adhkar_reminder(bot)
            # Sleep adhkar
            await send_sleep_adhkar_reminder(bot)
            # Weekly challenge
            await send_weekly_challenge(bot)

    # ── Challenge actions ─────────────────────────────────
    elif data.startswith("challenge:"):
        _, action, challenge_id = data.split(":")
        if action == "accept":
            await query.edit_message_text(
                f"✅ *Challenge accepted!* In sha Allah, you've got this.\n\n"
                "I'll track your progress and let you know when you complete it. 💪",
                parse_mode=ParseMode.MARKDOWN
            )
        elif action == "skip":
            await query.edit_message_text("⏭ Challenge skipped. There's always next week! 🤲", parse_mode=ParseMode.MARKDOWN)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles a shared location message — auto-detects city & updates prayer times."""
    user_id = update.effective_user.id
    location = update.message.location
    lat = location.latitude
    lng = location.longitude

    await update.message.reply_text(
        "📍 *Detecting your location...*", parse_mode=ParseMode.MARKDOWN
    )

    import aiohttp
    try:
        headers = {"User-Agent": "NoorBot/2.0"}
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
                data = await r.json()
        address = data.get("address", {})
        city = (
            address.get("city") or address.get("town") or
            address.get("village") or address.get("county") or "Unknown"
        )
        country = address.get("country", "")
    except Exception as e:
        logger.error(f"Reverse geocode failed: {e}")
        city, country = "Unknown", ""

    await update_user_location(user_id, city, country, lat, lng)

    from utils.prayer_times import get_prayer_times, format_prayer_schedule
    times = await get_prayer_times(lat, lng)
    schedule = format_prayer_schedule(times, city) if times else ""

    PENDING.pop(user_id, None)
    await update.message.reply_text(
        f"✅ *Location set to {city}!*\n\n{schedule}\n\n"
        "_Prayer reminders will now use your exact location._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb()
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles free-text messages — city input, group name, group code."""
    user_id = update.effective_user.id
    text    = update.message.text.strip()

    pending = PENDING.get(user_id)

    if pending == "awaiting_city":
        await update.message.reply_text("🔍 Looking up prayer times for *" + text + "*...", parse_mode=ParseMode.MARKDOWN)
        from utils.prayer_times import get_city_coordinates
        result = await get_city_coordinates(text)
        if not result:
            await update.message.reply_text(
                f"❌ I couldn't find *{text}*.\n\n"
                "Try a different spelling, e.g. _Abu Dhabi_, _Dubai_, _London_, _Karachi_.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=settings_kb()
            )
            return
        await update_user_location(user_id, result["city"], result["country"], result["lat"], result["lng"])
        times = await get_prayer_times(result["lat"], result["lng"])
        schedule = format_prayer_schedule(times, result["city"]) if times else ""
        PENDING.pop(user_id, None)
        await update.message.reply_text(
            f"✅ *Location updated to {result['city']}!*\n\n{schedule}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )

    elif pending == "awaiting_group_name":
        group = await create_group(text, user_id)
        PENDING.pop(user_id, None)
        await update.message.reply_text(
            f"👥 *Group '{group['name']}' created!*\n\n"
            f"🔗 Invite code: `{group['invite_code']}`\n\n"
            "Share this code with friends — they can join with /settings → Join a group.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )

    elif pending == "awaiting_period_days":
        try:
            days = int(text.strip())
            if not 1 <= days <= 10:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "Please enter a number between 1 and 10.",
                reply_markup=settings_kb()
            )
            return
        await set_period_mode(user_id, days)
        PENDING.pop(user_id, None)
        until = (date.today() + timedelta(days=days)).strftime("%A, %d %B")
        await update.message.reply_text(
            f"🌙 *Tracking paused.*\n\n"
            f"Prayer and Quran reminders are paused until *{until}*.\n\n"
            f"Your streaks are protected during this time. "
            f"You can still earn points for adhkar and other deeds.\n\n"
            f"May Allah grant you ease and accept your worship. 🤲",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )

    elif pending == "awaiting_group_code":
        code = text.upper().strip()
        group = await join_group(code, user_id)
        PENDING.pop(user_id, None)
        if not group:
            await update.message.reply_text(
                f"❌ Code *{code}* not found.\n\nDouble-check the code and try again.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=settings_kb()
            )
        else:
            await update.message.reply_text(
                f"🎉 *You joined '{group['name']}'!*\n\n"
                "You'll now appear on the group leaderboard. May Allah bless your competition! 💚",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_kb()
            )
    else:
        # Unknown message — show menu
        await update.message.reply_text(
            "Use the menu below or type /help for commands.",
            reply_markup=main_menu_kb()
        )


# ── Leaderboard builder ───────────────────────────────────

async def _build_leaderboard_text(user_id: int) -> str:
    from utils.database import pool
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()

    # Global top 10
    rows = await pool.fetch("""
        SELECT u.user_id, u.first_name, u.level,
               COALESCE(SUM(dl.points),0) as pts
        FROM users u
        LEFT JOIN deed_logs dl ON dl.user_id=u.user_id AND dl.log_date>=$1
        WHERE u.active=1
        GROUP BY u.user_id, u.first_name, u.level ORDER BY pts DESC LIMIT 10
    """, week_start)
    rows = [dict(r) for r in rows]

    medals = ["🥇","🥈","🥉"] + ["🏅"] * 7
    lines  = ["🏆 *Global Leaderboard — This Week*\n"]
    user_in_list = False

    for i, r in enumerate(rows):
        me = " ← you" if r["user_id"] == user_id else ""
        if r["user_id"] == user_id:
            user_in_list = True
        name = r["first_name"] or "Anonymous"
        lines.append(f"{medals[i]} *{name}* — Lvl {r['level']} — {r['pts']} pts{me}")

    if not user_in_list:
        rank_val = await pool.fetchval("""
            SELECT COUNT(*)+1 FROM (
                SELECT u.user_id, COALESCE(SUM(dl.points),0) as pts
                FROM users u
                LEFT JOIN deed_logs dl ON dl.user_id=u.user_id AND dl.log_date>=$1
                WHERE u.active=1 GROUP BY u.user_id
            ) sub
            WHERE pts > (
                SELECT COALESCE(SUM(points),0) FROM deed_logs
                WHERE user_id=$2 AND log_date>=$3
            )
        """, week_start, user_id, week_start)
        lines.append(f"\n_You are ranked #{rank_val or '?'} this week._")

    # Group leaderboard
    groups = await get_user_groups(user_id)
    if groups:
        g = groups[0]
        members = await get_group_leaderboard(g["id"], week_start)
        lines.append(f"\n👥 *{g['name']} — Group This Week*\n")
        for i, m in enumerate(members[:5]):
            me = " ← you" if m["user_id"] == user_id else ""
            lines.append(f"{medals[i]} *{m['first_name'] or 'Anonymous'}* — {m['points']} pts{me}")

    return "\n".join(lines)


# ── Snooze job ────────────────────────────────────────────

async def _snooze_job(context):
    d = context.job.data
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔔 *{d['label']} reminder!*\n\nTime's up — have you prayed? 🤲",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=prayer_checkin_kb(d["prayer_key"])
    )
