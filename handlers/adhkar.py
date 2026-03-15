"""
Adhkar handler — paginated interactive recitation flow.
Sends adhkar one by one, user taps Done after each,
completes the set and logs the deed automatically.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from data.adhkar import ADHKAR_COLLECTIONS
from utils.database import log_deed, add_xp, get_user
from config import XP_PER_POINT, xp_progress, LEVEL_MILESTONES

logger = logging.getLogger(__name__)

# Active sessions: {user_id: {"collection": key, "index": int}}
ADHKAR_SESSIONS = {}


def _adhkar_card(dhikr: dict, index: int, total: int, collection_key: str) -> tuple[str, InlineKeyboardMarkup]:
    """Returns (text, keyboard) for a single dhikr card."""
    progress_bar = "●" * (index + 1) + "○" * (total - index - 1)
    count_txt = f"×{dhikr['count']}" if dhikr['count'] > 1 else ""

    text = (
        f"📿 *{dhikr['title']}* {count_txt}\n"
        f"_{progress_bar} {index + 1}/{total}_\n\n"
        f"*{dhikr['arabic']}*\n\n"
        f"_{dhikr['transliteration']}_\n\n"
        f"💬 _{dhikr['meaning']}_\n\n"
        f"📚 {dhikr['source']}\n"
        f"✨ _{dhikr['benefit']}_"
    )

    is_last = (index == total - 1)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Done — Next ›" if not is_last else "✅ Completed! Log it",
            callback_data=f"adhkar:next:{collection_key}:{index}"
        )],
        [
            InlineKeyboardButton("⏭ Skip this",   callback_data=f"adhkar:skip:{collection_key}:{index}"),
            InlineKeyboardButton("❌ Stop",        callback_data=f"adhkar:stop:{collection_key}"),
        ],
    ])
    return text, kb


def _completion_text(collection_key: str, xp_earned: int, new_level: int, total_xp: int) -> str:
    col = ADHKAR_COLLECTIONS[collection_key]
    _, xp_in, xp_needed = xp_progress(total_xp)
    bar = "█" * round(xp_in / max(xp_needed, 1) * 10) + "░" * (10 - round(xp_in / max(xp_needed, 1) * 10))
    return (
        f"🌟 *{col['label']} Complete!*\n\n"
        f"MashaAllah! You've completed all the adhkar.\n\n"
        f"*+{col['points']} pts · +{xp_earned} XP*\n"
        f"⭐ Level {new_level} `{bar}` {xp_in}/{xp_needed} XP\n\n"
        f"_May Allah accept from you and increase you in goodness._ 🤲"
    )


# ── Trigger functions (called from reminders) ─────────────

async def send_morning_adhkar_prompt(bot, chat_id: int):
    text = (
        "🌅 *Time for Morning Adhkar!*\n\n"
        "Start your day with the remembrance of Allah.\n"
        "It takes just a few minutes and protects you all day. 🤲\n\n"
        "_'Verily, in the remembrance of Allah do hearts find rest.'_ — Quran 13:28"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 Begin Morning Adhkar", callback_data="adhkar:start:dhikr_am:0")],
        [InlineKeyboardButton("⏰ Remind me in 30 min", callback_data="adhkar:snooze:dhikr_am:30")],
        [InlineKeyboardButton("✅ Already done",         callback_data="adhkar:already:dhikr_am")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def send_evening_adhkar_prompt(bot, chat_id: int):
    text = (
        "🌆 *Time for Evening Adhkar!*\n\n"
        "The day is ending — seal it with the remembrance of Allah.\n"
        "These adhkar protect you through the night. 🌙"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 Begin Evening Adhkar", callback_data="adhkar:start:dhikr_pm:0")],
        [InlineKeyboardButton("⏰ Remind me in 30 min", callback_data="adhkar:snooze:dhikr_pm:30")],
        [InlineKeyboardButton("✅ Already done",         callback_data="adhkar:already:dhikr_pm")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def send_after_salah_prompt(bot, chat_id: int, prayer_name: str):
    text = (
        f"📿 *Dhikr after {prayer_name}*\n\n"
        "Take a moment for the post-prayer adhkar.\n"
        "SubhanAllah, Alhamdulillah, Allahu Akbar — 99 times. 🤲"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 Begin Dhikr", callback_data="adhkar:start:dhikr:0")],
        [InlineKeyboardButton("✅ Already done", callback_data="adhkar:already:dhikr")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def send_sleep_adhkar_prompt(bot, chat_id: int):
    text = (
        "🌙 *Bedtime Adhkar*\n\n"
        "Before you sleep, remember Allah.\n"
        "A guardian stays with you until morning. 💚"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 Begin Sleep Adhkar", callback_data="adhkar:start:dhikr_nawm:0")],
        [InlineKeyboardButton("✅ Already done",        callback_data="adhkar:already:dhikr_nawm")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ── Callback handler ──────────────────────────────────────

async def handle_adhkar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data          # adhkar:<action>:<collection>:<index>
    parts   = data.split(":")
    action  = parts[1]
    col_key = parts[2]
    user_id = query.from_user.id

    col = ADHKAR_COLLECTIONS.get(col_key)
    if not col:
        return

    adhkar_list = col["data"]
    total       = len(adhkar_list)

    # ── Start ──────────────────────────────────────────────
    if action == "start":
        index = int(parts[3]) if len(parts) > 3 else 0
        ADHKAR_SESSIONS[user_id] = {"collection": col_key, "index": index}
        dhikr = adhkar_list[index]
        text, kb = _adhkar_card(dhikr, index, total, col_key)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

    # ── Next / Done ────────────────────────────────────────
    elif action == "next":
        current_index = int(parts[3])
        next_index    = current_index + 1

        if next_index >= total:
            # Completed the full set — log the deed
            logged, xp = await log_deed(
                user_id, col_key, col["label"], col["points"]
            )
            if logged:
                new_level, leveled_up, total_xp = await add_xp(user_id, xp)
                text = _completion_text(col_key, xp, new_level, total_xp)
                await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
                if leveled_up:
                    milestone = LEVEL_MILESTONES.get(new_level, "")
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=(
                            f"🎉 *Level Up! You're now Level {new_level}!*\n\n"
                            + (f"_{milestone}_\n\n" if milestone else "")
                            + "May Allah bless your consistency. 💚"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await query.edit_message_text(
                    f"✅ *{col['label']}* already logged today! JazakAllah khayran. 💚",
                    parse_mode=ParseMode.MARKDOWN
                )
            ADHKAR_SESSIONS.pop(user_id, None)
        else:
            # Show next dhikr
            ADHKAR_SESSIONS[user_id] = {"collection": col_key, "index": next_index}
            dhikr = adhkar_list[next_index]
            text, kb = _adhkar_card(dhikr, next_index, total, col_key)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

    # ── Skip ───────────────────────────────────────────────
    elif action == "skip":
        current_index = int(parts[3])
        next_index    = current_index + 1
        if next_index >= total:
            # Skipped last one — still log partial completion
            logged, xp = await log_deed(user_id, col_key, col["label"], col["points"])
            if logged:
                new_level, _, total_xp = await add_xp(user_id, xp)
                text = _completion_text(col_key, xp, new_level, total_xp)
            else:
                text = f"✅ *{col['label']}* already logged today! 💚"
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
            ADHKAR_SESSIONS.pop(user_id, None)
        else:
            ADHKAR_SESSIONS[user_id] = {"collection": col_key, "index": next_index}
            dhikr = adhkar_list[next_index]
            text, kb = _adhkar_card(dhikr, next_index, total, col_key)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

    # ── Stop ───────────────────────────────────────────────
    elif action == "stop":
        ADHKAR_SESSIONS.pop(user_id, None)
        await query.edit_message_text(
            "⏸ *Adhkar paused.*\n\n"
            "Come back whenever you're ready. "
            "Allah is pleased with every effort. 🤲",
            parse_mode=ParseMode.MARKDOWN
        )

    # ── Already done ───────────────────────────────────────
    elif action == "already":
        logged, xp = await log_deed(user_id, col_key, col["label"], col["points"])
        if logged:
            new_level, leveled_up, total_xp = await add_xp(user_id, xp)
            _, xp_in, xp_needed = xp_progress(total_xp)
            await query.edit_message_text(
                f"✅ *{col['label']} logged!*\n\n"
                f"*+{col['points']} pts · +{xp} XP*\n"
                f"⭐ Level {new_level} · {xp_in}/{xp_needed} XP\n\n"
                f"_JazakAllah khayran!_ 💚",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                f"✅ *{col['label']}* already logged today! Keep it up. 💚",
                parse_mode=ParseMode.MARKDOWN
            )

    # ── Snooze ─────────────────────────────────────────────
    elif action == "snooze":
        mins     = int(parts[3])
        chat_id  = query.message.chat_id
        for job in context.job_queue.get_jobs_by_name(f"adhkar_snooze_{user_id}_{col_key}"):
            job.schedule_removal()
        context.job_queue.run_once(
            _adhkar_snooze_job,
            when=mins * 60,
            chat_id=chat_id,
            user_id=user_id,
            data={"collection_key": col_key},
            name=f"adhkar_snooze_{user_id}_{col_key}"
        )
        await query.edit_message_text(
            f"⏰ I'll remind you about *{col['label']}* in {mins} minutes.",
            parse_mode=ParseMode.MARKDOWN
        )


async def _adhkar_snooze_job(context):
    d       = context.job.data
    col_key = d["collection_key"]
    col     = ADHKAR_COLLECTIONS.get(col_key, {})
    label   = col.get("label", "Adhkar")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📿 Begin {label}", callback_data=f"adhkar:start:{col_key}:0")],
        [InlineKeyboardButton("✅ Already done",    callback_data=f"adhkar:already:{col_key}")],
    ])
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"🔔 *{label} reminder!*\n\nReady to recite? 🤲",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )
