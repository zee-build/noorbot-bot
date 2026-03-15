import os
from contextlib import asynccontextmanager
from datetime import date, timedelta, datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import database
from auth import validate_init_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB pool
    await database.get_pool()
    yield
    # Shutdown: close pool
    if database.pool:
        await database.pool.close()


app = FastAPI(title="NoorBot API", lifespan=lifespan)

FRONTEND_URL = os.getenv("FRONTEND_URL", "")

origins = ["*"]
if FRONTEND_URL:
    origins = [FRONTEND_URL, "http://localhost:5173", "http://localhost:3000", "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── helpers ──────────────────────────────────────────────────────────────────

def compute_level(total_xp: int):
    level = min(total_xp // 200, 50)
    xp_in_level = total_xp % 200
    xp_needed = 200
    return level, xp_in_level, xp_needed


async def compute_streak(user_id: int, deed_key: str) -> int:
    """Walk backwards from today counting consecutive days with a log."""
    rows = await database.fetch(
        """
        SELECT DISTINCT log_date FROM deed_logs
        WHERE user_id=$1 AND deed_key=$2
        ORDER BY log_date DESC
        """,
        user_id,
        deed_key,
    )
    if not rows:
        return 0

    logged_dates = {r["log_date"] for r in rows}
    streak = 0
    current = date.today()

    # Allow today OR yesterday as starting point (in case today not yet logged)
    if current not in logged_dates:
        current = current - timedelta(days=1)

    while current in logged_dates:
        streak += 1
        current -= timedelta(days=1)

    return streak


# ── request bodies ───────────────────────────────────────────────────────────

class LogBody(BaseModel):
    user_id: int
    deed_key: str
    deed_label: str
    points: int
    jamaah: bool = False


class UpdateUserBody(BaseModel):
    reminders_on: bool


# ── endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/user/{user_id}")
async def get_user(
    user_id: int,
    _user: dict = Depends(validate_init_data),
):
    user = await database.fetchrow(
        "SELECT * FROM users WHERE user_id=$1", user_id
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_xp = user.get("total_xp", 0) or 0
    level, xp_in_level, xp_needed = compute_level(total_xp)

    fajr_streak = await compute_streak(user_id, "fajr")
    quran_streak = await compute_streak(user_id, "quran")

    return {
        "user_id": user["user_id"],
        "first_name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "city": user.get("city", ""),
        "country": user.get("country", ""),
        "level": level,
        "xp_in_level": xp_in_level,
        "xp_needed": xp_needed,
        "total_xp": total_xp,
        "reminders_on": user.get("reminders_on", True),
        "joined_at": str(user.get("joined_at", "")),
        "fajr_streak": fajr_streak,
        "quran_streak": quran_streak,
    }


@app.get("/api/user/{user_id}/today")
async def get_today(
    user_id: int,
    _user: dict = Depends(validate_init_data),
):
    today = date.today()

    goals = await database.fetch(
        "SELECT * FROM goals WHERE user_id=$1 AND active=1 ORDER BY id",
        user_id,
    )

    logs = await database.fetch(
        "SELECT deed_key, jamaah FROM deed_logs WHERE user_id=$1 AND log_date=$2",
        user_id,
        today,
    )

    logged_map = {}
    jamaah_map = {}
    for log in logs:
        dk = log["deed_key"]
        logged_map[dk] = True
        jamaah_map[dk] = bool(log.get("jamaah", False))

    result_goals = []
    max_score = 0
    score = 0

    for g in goals:
        dk = g["deed_key"]
        pts = g.get("points", 0) or 0
        max_score += pts
        logged = logged_map.get(dk, False)
        jamaah = jamaah_map.get(dk, False)
        if logged:
            score += pts
        result_goals.append({
            **g,
            "logged": logged,
            "jamaah": jamaah,
        })

    pct = round((score / max_score * 100) if max_score > 0 else 0)

    return {
        "goals": result_goals,
        "score": score,
        "max_score": max_score,
        "pct": pct,
    }


@app.get("/api/user/{user_id}/weekly")
async def get_weekly(
    user_id: int,
    _user: dict = Depends(validate_init_data),
):
    today = date.today()
    seven_days_ago = today - timedelta(days=6)

    goals = await database.fetch(
        "SELECT points FROM goals WHERE user_id=$1 AND active=1",
        user_id,
    )
    max_per_day = sum(g.get("points", 0) or 0 for g in goals)

    scores = await database.fetch(
        """
        SELECT score_date, score FROM daily_scores
        WHERE user_id=$1 AND score_date >= $2
        ORDER BY score_date
        """,
        user_id,
        seven_days_ago,
    )

    score_map = {}
    for s in scores:
        score_map[str(s["score_date"])] = s.get("score", 0) or 0

    result = []
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        ds = str(d)
        sc = score_map.get(ds, 0)
        pct = round((sc / max_per_day * 100) if max_per_day > 0 else 0)
        result.append({
            "date": ds,
            "score": sc,
            "max_score": max_per_day,
            "pct": pct,
        })

    return result


@app.get("/api/user/{user_id}/monthly")
async def get_monthly(
    user_id: int,
    _user: dict = Depends(validate_init_data),
):
    today = date.today()
    month_prefix = today.strftime("%Y-%m")

    goals = await database.fetch(
        "SELECT points FROM goals WHERE user_id=$1 AND active=1",
        user_id,
    )
    max_per_day = sum(g.get("points", 0) or 0 for g in goals)

    scores = await database.fetch(
        """
        SELECT score_date, score FROM daily_scores
        WHERE user_id=$1 AND CAST(score_date AS TEXT) LIKE $2
        ORDER BY score_date
        """,
        user_id,
        f"{month_prefix}%",
    )

    result = []
    for s in scores:
        sc = s.get("score", 0) or 0
        pct = round((sc / max_per_day * 100) if max_per_day > 0 else 0)
        result.append({
            "date": str(s["score_date"]),
            "score": sc,
            "pct": pct,
        })

    return result


@app.get("/api/user/{user_id}/streaks")
async def get_streaks(
    user_id: int,
    _user: dict = Depends(validate_init_data),
):
    goals = await database.fetch(
        "SELECT deed_key, deed_label FROM goals WHERE user_id=$1 AND active=1",
        user_id,
    )

    result = []
    for g in goals:
        dk = g["deed_key"]
        streak = await compute_streak(user_id, dk)
        result.append({
            "deed_key": dk,
            "deed_label": g.get("deed_label", dk),
            "streak": streak,
        })

    return result


@app.get("/api/leaderboard")
async def get_leaderboard(
    period: str = "week",
    _user: dict = Depends(validate_init_data),
):
    today = date.today()

    if period == "week":
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        date_filter = week_start
        query = """
            SELECT u.user_id, u.first_name, u.level,
                   COALESCE(SUM(dl.points), 0) AS points
            FROM users u
            LEFT JOIN deed_logs dl ON dl.user_id = u.user_id AND dl.log_date >= $1
            WHERE u.active = 1
            GROUP BY u.user_id, u.first_name, u.level
            ORDER BY points DESC
            LIMIT 50
        """
        rows = await database.fetch(query, date_filter)

    elif period == "month":
        month_start = today.replace(day=1)
        date_filter = month_start
        query = """
            SELECT u.user_id, u.first_name, u.level,
                   COALESCE(SUM(dl.points), 0) AS points
            FROM users u
            LEFT JOIN deed_logs dl ON dl.user_id = u.user_id AND dl.log_date >= $1
            WHERE u.active = 1
            GROUP BY u.user_id, u.first_name, u.level
            ORDER BY points DESC
            LIMIT 50
        """
        rows = await database.fetch(query, date_filter)

    else:  # alltime
        query = """
            SELECT u.user_id, u.first_name, u.level,
                   COALESCE(SUM(dl.points), 0) AS points
            FROM users u
            LEFT JOIN deed_logs dl ON dl.user_id = u.user_id
            WHERE u.active = 1
            GROUP BY u.user_id, u.first_name, u.level
            ORDER BY points DESC
            LIMIT 50
        """
        rows = await database.fetch(query)

    result = []
    for i, row in enumerate(rows):
        result.append({
            "rank": i + 1,
            "user_id": row["user_id"],
            "first_name": row["first_name"],
            "level": row.get("level", 0) or 0,
            "points": int(row.get("points", 0) or 0),
        })

    return result


@app.get("/api/group/{group_id}/leaderboard")
async def get_group_leaderboard(
    group_id: int,
    _user: dict = Depends(validate_init_data),
):
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    rows = await database.fetch(
        """
        SELECT u.user_id, u.first_name, u.level,
               COALESCE(SUM(dl.points), 0) AS points
        FROM group_members gm
        JOIN users u ON u.user_id = gm.user_id
        LEFT JOIN deed_logs dl ON dl.user_id = u.user_id AND dl.log_date >= $1
        WHERE gm.group_id = $2
        GROUP BY u.user_id, u.first_name, u.level
        ORDER BY points DESC
        """,
        week_start,
        group_id,
    )

    result = []
    for i, row in enumerate(rows):
        result.append({
            "rank": i + 1,
            "user_id": row["user_id"],
            "first_name": row["first_name"],
            "level": row.get("level", 0) or 0,
            "points": int(row.get("points", 0) or 0),
        })

    return result


@app.get("/api/user/{user_id}/groups")
async def get_user_groups(
    user_id: int,
    _user: dict = Depends(validate_init_data),
):
    rows = await database.fetch(
        """
        SELECT g.id, g.name, g.invite_code
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = $1
        """,
        user_id,
    )
    return [{"id": r["id"], "name": r["name"], "invite_code": r.get("invite_code", "")} for r in rows]


@app.post("/api/log")
async def log_deed(
    body: LogBody,
    _user: dict = Depends(validate_init_data),
):
    today = date.today()

    existing = await database.fetchrow(
        """
        SELECT id FROM deed_logs
        WHERE user_id=$1 AND deed_key=$2 AND log_date=$3
        """,
        body.user_id,
        body.deed_key,
        today,
    )

    if existing:
        user = await database.fetchrow(
            "SELECT total_xp, level FROM users WHERE user_id=$1", body.user_id
        )
        total_xp = user.get("total_xp", 0) or 0
        level, _, _ = compute_level(total_xp)
        return {
            "logged": False,
            "xp_earned": 0,
            "new_level": level,
            "leveled_up": False,
            "total_xp": total_xp,
        }

    xp_earned = body.points * 10

    await database.execute(
        """
        INSERT INTO deed_logs (user_id, deed_key, deed_label, points, jamaah, log_date, xp_earned)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        body.user_id,
        body.deed_key,
        body.deed_label,
        body.points,
        body.jamaah,
        today,
        xp_earned,
    )

    # Upsert daily_scores
    await database.execute(
        """
        INSERT INTO daily_scores (user_id, score_date, score)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, score_date)
        DO UPDATE SET score = daily_scores.score + EXCLUDED.score
        """,
        body.user_id,
        today,
        body.points,
    )

    user = await database.fetchrow(
        "SELECT total_xp, level FROM users WHERE user_id=$1", body.user_id
    )
    old_total_xp = user.get("total_xp", 0) or 0
    old_level, _, _ = compute_level(old_total_xp)

    new_total_xp = old_total_xp + xp_earned
    new_level, _, _ = compute_level(new_total_xp)

    await database.execute(
        "UPDATE users SET total_xp=$1, level=$2 WHERE user_id=$3",
        new_total_xp,
        new_level,
        body.user_id,
    )

    leveled_up = new_level > old_level

    return {
        "logged": True,
        "xp_earned": xp_earned,
        "new_level": new_level,
        "leveled_up": leveled_up,
        "total_xp": new_total_xp,
    }


@app.patch("/api/user/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserBody,
    _user: dict = Depends(validate_init_data),
):
    await database.execute(
        "UPDATE users SET reminders_on=$1 WHERE user_id=$2",
        body.reminders_on,
        user_id,
    )
    return {"success": True}
