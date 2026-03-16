"""
/card command — generate a shareable progress card image using Pillow.
Falls back to a text card if Pillow is unavailable.
"""
import io
import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.database import get_user, get_today_logs, get_user_goals, get_streak, pool
from config import xp_progress

logger = logging.getLogger(__name__)


def _draw_card(first_name: str, level: int, xp_in: int, xp_needed: int,
               total_xp: int, prayers_done: int, score_pct: int,
               fajr_streak: int, city: str) -> io.BytesIO:
    """Draw an image card using Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 800, 500
    BG      = (5, 14, 14)
    GOLD    = (201, 168, 76)
    GREEN   = (14, 42, 30)
    CREAM   = (240, 230, 210)
    MUTED   = (120, 140, 130)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Background panel ──────────────────────────────────────
    draw.rounded_rectangle([20, 20, W-20, H-20], radius=24, fill=GREEN,
                           outline=GOLD, width=2)

    # ── Header ───────────────────────────────────────────────
    draw.text((40, 40), "☽ NoorBot", fill=GOLD, font=None)
    draw.text((W-160, 40), date.today().strftime("%d %b %Y"), fill=MUTED, font=None)

    # ── Name ─────────────────────────────────────────────────
    draw.text((40, 100), first_name, fill=CREAM, font=None)
    draw.text((40, 130), f"Level {level}  •  {total_xp:,} XP", fill=GOLD, font=None)

    # ── XP bar ───────────────────────────────────────────────
    bar_x, bar_y, bar_w, bar_h = 40, 175, W-80, 18
    draw.rounded_rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h],
                           radius=9, fill=(20, 60, 40))
    if xp_needed > 0:
        filled = int((xp_in / xp_needed) * bar_w)
        draw.rounded_rectangle([bar_x, bar_y, bar_x+filled, bar_y+bar_h],
                               radius=9, fill=GOLD)
    draw.text((bar_x, bar_y+24), f"{xp_in}/{xp_needed} XP to next level", fill=MUTED, font=None)

    # ── Stats row ─────────────────────────────────────────────
    stats = [
        ("🕌 Prayers", f"{prayers_done}/5"),
        ("📊 Score",   f"{score_pct}%"),
        ("🔥 Fajr",    f"{fajr_streak} day streak"),
        ("📍 City",    city or "—"),
    ]
    sx = 40
    for label, val in stats:
        draw.text((sx, 240), label, fill=MUTED, font=None)
        draw.text((sx, 264), val,   fill=CREAM, font=None)
        sx += 190

    # ── Footer ────────────────────────────────────────────────
    draw.line([(40, 430), (W-40, 430)], fill=(*GOLD, 80), width=1)
    draw.text((40, 445), "Shared via NoorBot — track your ibadah daily",
              fill=MUTED, font=None)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def _get_card_data(user_id: int):
    """Shared data-fetching logic for both command and callback."""
    db_user = await get_user(user_id)
    if not db_user:
        return None, None, None, None, None, None, None, None

    logs  = await get_today_logs(user_id)
    goals = await get_user_goals(user_id)

    fardh_keys   = {"fajr", "dhuhr", "asr", "maghrib", "isha"}
    logged_keys  = {l["deed_key"] for l in logs}
    prayers_done = sum(1 for k in fardh_keys if k in logged_keys)
    score        = sum(l["points"] for l in logs)
    max_score    = sum(g["points"] for g in goals) or 1
    score_pct    = round(score / max_score * 100)
    level, xp_in, xp_needed = xp_progress(db_user["total_xp"])
    fajr_streak  = await get_streak(user_id, "fajr")

    return db_user, level, xp_in, xp_needed, prayers_done, score_pct, fajr_streak, logged_keys


async def card_from_callback(query, context):
    """Called from view:card inline button — sends photo as a new message."""
    user_id = query.from_user.id
    db_user, level, xp_in, xp_needed, prayers_done, score_pct, fajr_streak, _ = await _get_card_data(user_id)

    if not db_user:
        await query.answer("Send /start first.", show_alert=True)
        return

    today   = date.today()
    caption = (
        f"*{db_user['first_name']}'s NoorBot Progress Card*\n"
        f"_{today.strftime('%A, %d %B %Y')}_\n\n"
        "🌙 _May Allah accept our deeds and make us consistent._"
    )

    try:
        buf = _draw_card(
            first_name=db_user["first_name"], level=level,
            xp_in=xp_in, xp_needed=xp_needed, total_xp=db_user["total_xp"],
            prayers_done=prayers_done, score_pct=score_pct,
            fajr_streak=fajr_streak, city=db_user.get("city", ""),
        )
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=buf, caption=caption, parse_mode="Markdown",
        )
        await query.answer()
    except Exception as e:
        logger.warning(f"Card callback image failed: {e}")
        # Fall back to text card sent as new message
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_text_card(db_user, level, xp_in, xp_needed, prayers_done, score_pct, fajr_streak),
            parse_mode="Markdown",
        )
        await query.answer()


def _text_card(db_user, level, xp_in, xp_needed, prayers_done, score_pct, fajr_streak) -> str:
    today     = date.today().strftime("%A, %d %B %Y")
    bar_width = 10
    filled    = round(xp_in / xp_needed * bar_width) if xp_needed else bar_width
    bar       = "█" * filled + "░" * (bar_width - filled)
    return (
        f"┌──────────────────────────┐\n"
        f"│  ☽ *NoorBot Progress Card*\n"
        f"├──────────────────────────┤\n"
        f"│  👤 *{db_user['first_name']}*\n"
        f"│  _{today}_\n"
        f"│\n"
        f"│  ⭐ *Level {level}*\n"
        f"│  `{bar}` {xp_in}/{xp_needed} XP\n"
        f"│  💎 Total XP: *{db_user['total_xp']:,}*\n"
        f"│\n"
        f"│  🕌 Prayers: *{prayers_done}/5*\n"
        f"│  📊 Today: *{score_pct}%*\n"
        f"│  🔥 Fajr streak: *{fajr_streak} days*\n"
        f"│  📍 {db_user.get('city', '—')}\n"
        f"└──────────────────────────┘\n\n"
        "_Shared via NoorBot — track your ibadah daily_ 🌙"
    )


async def card_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a shareable progress card."""
    user_id = update.effective_user.id
    db_user, level, xp_in, xp_needed, prayers_done, score_pct, fajr_streak, _ = await _get_card_data(user_id)

    if not db_user:
        await update.message.reply_text("Send /start first to set up your account.")
        return

    today   = date.today()
    caption = (
        f"*{db_user['first_name']}'s NoorBot Progress Card*\n"
        f"_{today.strftime('%A, %d %B %Y')}_\n\n"
        "🌙 _May Allah accept our deeds and make us consistent._"
    )

    try:
        buf = _draw_card(
            first_name=db_user["first_name"], level=level,
            xp_in=xp_in, xp_needed=xp_needed, total_xp=db_user["total_xp"],
            prayers_done=prayers_done, score_pct=score_pct,
            fajr_streak=fajr_streak, city=db_user.get("city", ""),
        )
        await update.message.reply_photo(photo=buf, caption=caption, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning(f"Pillow card failed, sending text card: {e}")
        await update.message.reply_text(
            _text_card(db_user, level, xp_in, xp_needed, prayers_done, score_pct, fajr_streak),
            parse_mode=ParseMode.MARKDOWN
        )
