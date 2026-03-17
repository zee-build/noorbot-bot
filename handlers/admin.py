"""
Admin bot commands — only accessible by the configured ADMIN_CHAT_ID.
"""
import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest

from config import ADMIN_CHAT_ID
from utils.database import (
    get_total_users, get_all_users_admin, get_user,
    set_user_active, pool
)

logger = logging.getLogger(__name__)


def _e(text) -> str:
    """Escape HTML special characters in user-supplied strings."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _is_admin(user_id: int) -> bool:
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID is not set — all admin commands will be denied.")
        return False
    return user_id == ADMIN_CHAT_ID


async def _check_admin(update: Update) -> bool:
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        logger.warning(f"Admin check failed: user_id={user_id}, ADMIN_CHAT_ID={ADMIN_CHAT_ID}")
        await update.message.reply_text("❌ Admin only.")
        return False
    return True


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel help."""
    if not await _check_admin(update):
        return
    text = (
        "🔐 <b>Admin Panel</b>\n\n"
        "Available commands:\n"
        "/stats_admin — Bot statistics\n"
        "/top10 — Top 10 users all time\n"
        "/broadcast — Send message to all users\n"
        "/users — List all active users\n"
        "/inactive — List blocked/inactive users\n"
        "/user &lt;id&gt; — Get user info\n"
        "/pause_user &lt;id&gt; — Pause user\n"
        "/resume_user &lt;id&gt; — Resume user\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def stats_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Overall bot stats."""
    if not await _check_admin(update):
        return

    total = await get_total_users()
    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=7)).isoformat()

    active_today = await pool.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM deed_logs WHERE log_date=$1", today
    ) or 0
    active_week = await pool.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM deed_logs WHERE log_date>=$1", week_start
    ) or 0
    total_logs = await pool.fetchval("SELECT COUNT(*) FROM deed_logs") or 0
    new_today = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE joined_at=$1", today
    ) or 0

    text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total users: <b>{total}</b>\n"
        f"🆕 Joined today: <b>{new_today}</b>\n"
        f"✅ Active today: <b>{active_today}</b>\n"
        f"📅 Active this week: <b>{active_week}</b>\n"
        f"📝 Total deed logs: <b>{total_logs:,}</b>\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def top10_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top 10 users all time."""
    if not await _check_admin(update):
        return

    rows = await pool.fetch("""
        SELECT u.user_id, u.first_name, u.username, u.level,
               COALESCE(SUM(dl.points),0) as pts
        FROM users u
        LEFT JOIN deed_logs dl ON dl.user_id=u.user_id
        GROUP BY u.user_id, u.first_name, u.username, u.level
        ORDER BY pts DESC LIMIT 10
    """)

    medals = ["🥇","🥈","🥉"] + ["🏅"] * 7
    lines = ["🏆 <b>Top 10 All-Time</b>\n"]
    for i, r in enumerate(rows):
        name = _e(r["first_name"] or "Anonymous")
        uname = f" (@{_e(r['username'])})" if r["username"] else ""
        lines.append(f"{medals[i]} <b>{name}</b>{uname} — Lvl {r['level']} — {r['pts']} pts")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message to all active users.
    Usage: /broadcast Your message here"""
    if not await _check_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast Your message here\n\n"
            "Prefixed with [NoorBot Announcement] automatically."
        )
        return

    message = " ".join(context.args)
    full_text = f"📢 *NoorBot Announcement*\n\n{message}"

    users = await get_all_users_admin()
    sent = 0
    failed = 0
    blocked = 0

    await update.message.reply_text(f"📡 Broadcasting to {len(users)} users...")

    for user in users:
        if not user.get("active", 1):
            continue
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=full_text,
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Forbidden:
            # User blocked the bot — deactivate them
            await set_user_active(user["user_id"], False)
            blocked += 1
            failed += 1
            logger.info(f"Broadcast: user {user['user_id']} blocked bot — deactivated")
        except BadRequest as e:
            failed += 1
            logger.warning(f"Broadcast: BadRequest for {user['user_id']}: {e}")
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast: failed for {user['user_id']}: {e}")

    blocked_note = f"\n🚫 Blocked & deactivated: {blocked}" if blocked else ""
    await update.message.reply_text(
        f"✅ Broadcast complete!\n📤 Sent: {sent}\n❌ Failed: {failed}{blocked_note}"
    )


async def user_info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get info about a specific user. Usage: /user <user_id>"""
    if not await _check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /user <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    user = await get_user(target_id)
    if not user:
        await update.message.reply_text(f"User {target_id} not found.")
        return

    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=7)).isoformat()
    logs_today = await pool.fetchval(
        "SELECT COUNT(*) FROM deed_logs WHERE user_id=$1 AND log_date=$2", target_id, today
    ) or 0
    logs_week = await pool.fetchval(
        "SELECT COUNT(*) FROM deed_logs WHERE user_id=$1 AND log_date>=$2", target_id, week_start
    ) or 0
    total_pts = await pool.fetchval(
        "SELECT COALESCE(SUM(points),0) FROM deed_logs WHERE user_id=$1", target_id
    ) or 0

    status = "✅ Active" if user.get("active", 1) else "🚫 Paused"
    text = (
        f"👤 <b>User Info</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Name: <b>{_e(user['first_name'])}</b>\n"
        f"Username: @{_e(user['username'] or 'N/A')}\n"
        f"Status: {status}\n"
        f"Level: <b>{user['level']}</b> | XP: <b>{user['total_xp']:,}</b>\n"
        f"City: {_e(user['city'])}\n"
        f"Joined: {user['joined_at']}\n\n"
        f"📝 Logs today: <b>{logs_today}</b>\n"
        f"📅 Logs this week: <b>{logs_week}</b>\n"
        f"🏆 Total pts: <b>{total_pts:,}</b>\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def active_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active users. Usage: /users"""
    if not await _check_admin(update):
        return

    rows = await pool.fetch(
        "SELECT user_id, first_name, username, city, level, total_xp, joined_at FROM users WHERE active=1 ORDER BY joined_at DESC"
    )
    if not rows:
        await update.message.reply_text("No active users found.")
        return

    lines = [f"✅ <b>Active Users ({len(rows)})</b>\n"]
    for r in rows:
        uname = f"@{_e(r['username'])}" if r["username"] else "no username"
        lines.append(f"• <code>{r['user_id']}</code> — <b>{_e(r['first_name'])}</b> ({uname}) — Lvl {r['level']} — {_e(r['city'])} — joined {r['joined_at']}")

    # Telegram message limit is 4096 chars — split if needed
    text = "\n".join(lines)
    if len(text) <= 4096:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        chunk, chunks = [], []
        for line in lines:
            if sum(len(l) + 1 for l in chunk) + len(line) > 4000:
                chunks.append("\n".join(chunk))
                chunk = []
            chunk.append(line)
        if chunk:
            chunks.append("\n".join(chunk))
        for part in chunks:
            await update.message.reply_text(part, parse_mode=ParseMode.HTML)


async def inactive_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all inactive/blocked users. Usage: /inactive"""
    if not await _check_admin(update):
        return

    rows = await pool.fetch(
        "SELECT user_id, first_name, username, joined_at FROM users WHERE active=0 ORDER BY joined_at DESC"
    )
    if not rows:
        await update.message.reply_text("✅ No inactive users.")
        return

    lines = [f"🚫 <b>Inactive Users ({len(rows)})</b>\n"]
    for r in rows:
        uname = f"@{_e(r['username'])}" if r["username"] else "no username"
        lines.append(f"• <code>{r['user_id']}</code> — <b>{_e(r['first_name'])}</b> ({uname}) — joined {r['joined_at']}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def pause_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause a user (disable their reminders & exclude from stats). Usage: /pause_user <id>"""
    if not await _check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /pause_user <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    await set_user_active(target_id, False)
    await update.message.reply_text(f"🚫 User {target_id} has been paused.")


async def resume_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume a paused user. Usage: /resume_user <id>"""
    if not await _check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /resume_user <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    await set_user_active(target_id, True)
    await update.message.reply_text(f"✅ User {target_id} has been resumed.")


async def notify_admin_new_user(bot, user_id: int, first_name: str, username: str):
    """Send a notification to the admin when a new user joins."""
    if not ADMIN_CHAT_ID:
        return
    total = await get_total_users()
    uname = f"@{username}" if username else "no username"
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🆕 <b>New User Joined!</b>\n\n"
                f"👤 {_e(first_name)} ({_e(uname)})\n"
                f"🆔 <code>{user_id}</code>\n\n"
                f"👥 Total users: <b>{total}</b>"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Failed to notify admin of new user: {e}")
