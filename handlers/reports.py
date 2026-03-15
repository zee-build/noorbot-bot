"""
Report builders v2 — daily, weekly, monthly with XP context.
"""
import logging
from datetime import date, timedelta
from telegram import Bot
from telegram.constants import ParseMode

from utils.database import get_all_active_users, get_user_goals, get_logs_for_date, get_week_logs, get_month_scores, get_user, is_period_mode
from utils.prayer_times import is_ramadan
from config import PERFORMANCE_TIERS, xp_progress

FARDH_KEYS = {"fajr", "dhuhr", "asr", "maghrib", "isha"}

logger = logging.getLogger(__name__)


def _tier(pct):
    for t, label in PERFORMANCE_TIERS:
        if pct >= t:
            return label
    return PERFORMANCE_TIERS[-1][1]


def _bar(pct, w=8):
    filled = round(pct / 100 * w)
    return "█" * filled + "░" * (w - filled)


async def build_daily_report(user_id: int, for_date: str = None) -> str:
    if not for_date:
        for_date = date.today().isoformat()
    goals = await get_user_goals(user_id)
    logs  = await get_logs_for_date(user_id, for_date)
    logged_keys = {l["deed_key"] for l in logs}

    prayers = [g for g in goals if g["deed_key"] in FARDH_KEYS]
    sunnah  = [g for g in goals if g["deed_key"] not in FARDH_KEYS]

    db_user = await get_user(user_id)
    level, xp_in, xp_needed = xp_progress(db_user["total_xp"]) if db_user else (1, 0, 200)

    ramadan = await is_ramadan(
        db_user["latitude"] if db_user else 25.2048,
        db_user["longitude"] if db_user else 55.2708
    )
    in_period = await is_period_mode(user_id)

    lines = [f"📋 *Daily Report — {for_date}*"]
    if ramadan:
        lines.append("_🌙 Ramadan Mubarak!_")
    lines.append("")

    lines.append("*🕌 Fardh Prayers:*")
    for g in prayers:
        if in_period:
            lines.append(f"🌙 {g['deed_label']} — _resting_")
        else:
            log    = next((l for l in logs if l["deed_key"] == g["deed_key"]), None)
            done   = g["deed_key"] in logged_keys
            jm_txt = " _(jama'ah)_" if log and log.get("jamaah") else ""
            lines.append(f"{'✅' if done else '❌'} {g['deed_label']}{jm_txt}")

    if sunnah:
        lines.append("\n*📿 Sunnah & Voluntary:*")
        for g in sunnah:
            done = g["deed_key"] in logged_keys
            lines.append(f"{'✅' if done else '❌'} {g['deed_label']}")

    # Score excludes prayers during period mode
    if in_period:
        prayer_pts = sum(g["points"] for g in prayers)
        earned  = sum(l["points"] for l in logs)
        max_pts = sum(g["points"] for g in goals) - prayer_pts
    else:
        earned  = sum(l["points"] for l in logs)
        max_pts = sum(g["points"] for g in goals)
    pct = round(earned / max_pts * 100) if max_pts else 0

    lines.append(f"\n*Score: {earned}/{max_pts} pts ({pct}%)*")
    lines.append(f"`{_bar(pct)}` {_tier(pct)}")
    lines.append(f"\n⭐ Level {level} · {xp_in}/{xp_needed} XP")

    if in_period:
        lines.append("\n🌙 _Tracking paused — streaks protected. Keep up your adhkar!_ 💚")

    return "\n".join(lines)


async def build_weekly_report(user_id: int) -> str:
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    goals      = await get_user_goals(user_id)
    max_per_day = sum(g["points"] for g in goals)
    logs        = await get_week_logs(user_id)

    by_date = {}
    for l in logs:
        by_date.setdefault(l["log_date"], []).append(l)

    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    lines     = ["📅 *Weekly Report*\n"]
    scores    = []

    for i in range(7):
        d = week_start + timedelta(days=i)
        if d > today:
            break
        earned = sum(l["points"] for l in by_date.get(d.isoformat(), []))
        pct    = round(earned / max_per_day * 100) if max_per_day else 0
        scores.append(pct)
        today_marker = " ← today" if d == today else ""
        lines.append(f"*{day_names[i]}* `{_bar(pct, 6)}` {pct}%{today_marker}")

    if scores:
        avg = round(sum(scores) / len(scores))
        best_i  = scores.index(max(scores))
        lines.append(f"\n*Average: {avg}%* — {_tier(avg)}")
        lines.append(f"🏆 Best day: *{day_names[best_i]}* ({scores[best_i]}%)")
        if min(scores) < max(scores):
            worst_i = scores.index(min(scores))
            lines.append(f"⚠️  Weakest: *{day_names[worst_i]}* ({scores[worst_i]}%)")

    return "\n".join(lines)


async def build_monthly_report(user_id: int) -> str:
    today   = date.today()
    goals   = await get_user_goals(user_id)
    max_per = sum(g["points"] for g in goals)
    scores  = await get_month_scores(user_id, today.year, today.month)

    if not scores:
        return "📆 No data yet this month. Keep going! 💚"

    total   = sum(s["score"] for s in scores)
    days    = len(scores)
    pct     = round(total / (max_per * days) * 100) if max_per and days else 0

    week_totals = {}
    for s in scores:
        wk = (date.fromisoformat(s["score_date"]).day - 1) // 7 + 1
        week_totals.setdefault(wk, []).append(s["score"])

    lines = [f"📆 *{today.strftime('%B %Y')}*\n"]
    for wk, wk_scores in week_totals.items():
        wp = round(sum(wk_scores) / (max_per * len(wk_scores)) * 100) if max_per else 0
        lines.append(f"Week {wk}: `{_bar(wp, 8)}` {wp}%")

    lines.append(f"\n*Month: {pct}%* — {_tier(pct)}")
    lines.append(f"_{days} days tracked_")

    last_month   = today.replace(day=1) - timedelta(days=1)
    last_scores  = await get_month_scores(user_id, last_month.year, last_month.month)
    if last_scores and max_per:
        lp   = round(sum(s["score"] for s in last_scores) / (max_per * len(last_scores)) * 100)
        diff = pct - lp
        lines.append(f"{'📈' if diff >= 0 else '📉'} vs last month: *{'+' if diff >= 0 else ''}{diff}%*")

    return "\n".join(lines)


async def send_all_daily_reports(bot: Bot):
    for user in await get_all_active_users():
        try:
            text = "🌙 *End of Day Report*\n\n" + await build_daily_report(user["user_id"])
            await bot.send_message(chat_id=user["user_id"], text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Daily report {user['user_id']}: {e}")


async def send_all_weekly_reports(bot: Bot):
    for user in await get_all_active_users():
        try:
            text = "📅 *Jumu'ah Mubarak! Weekly Summary:*\n\n" + await build_weekly_report(user["user_id"])
            await bot.send_message(chat_id=user["user_id"], text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Weekly report {user['user_id']}: {e}")


async def send_all_monthly_reports(bot: Bot):
    for user in await get_all_active_users():
        try:
            text = "📆 *New Month! Last month's summary:*\n\n" + await build_monthly_report(user["user_id"])
            await bot.send_message(chat_id=user["user_id"], text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Monthly report {user['user_id']}: {e}")
