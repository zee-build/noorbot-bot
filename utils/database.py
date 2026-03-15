"""
Database v2 — asyncpg/PostgreSQL (Supabase) backend.
"""
import asyncpg
import logging
import random
import string
from datetime import date, timedelta
from typing import Optional
from config import DATABASE_URL, XP_PER_POINT, level_from_xp, xp_for_level

logger = logging.getLogger(__name__)

pool: asyncpg.Pool = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

    async with pool.acquire() as conn:
        # ── Create tables ──────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       BIGINT PRIMARY KEY,
                username      TEXT,
                first_name    TEXT,
                city          TEXT DEFAULT 'Dubai',
                country       TEXT DEFAULT 'AE',
                latitude      REAL DEFAULT 25.2048,
                longitude     REAL DEFAULT 55.2708,
                timezone      TEXT DEFAULT 'Asia/Dubai',
                joined_at     TEXT DEFAULT (CURRENT_DATE::TEXT),
                active        INTEGER DEFAULT 1,
                total_xp      INTEGER DEFAULT 0,
                level         INTEGER DEFAULT 1,
                reminders_on  INTEGER DEFAULT 1,
                onboarding    INTEGER DEFAULT 0
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                deed_key    TEXT,
                deed_label  TEXT,
                points      INTEGER,
                active      INTEGER DEFAULT 1,
                added_at    TEXT DEFAULT (CURRENT_DATE::TEXT),
                UNIQUE(user_id, deed_key),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS deed_logs (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                deed_key    TEXT,
                deed_label  TEXT,
                points      INTEGER,
                xp_earned   INTEGER DEFAULT 0,
                log_date    TEXT DEFAULT (CURRENT_DATE::TEXT),
                logged_at   TEXT DEFAULT (CURRENT_TIMESTAMP::TEXT),
                jamaah      INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_scores (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                score_date  TEXT,
                score       INTEGER DEFAULT 0,
                max_score   INTEGER DEFAULT 0,
                UNIQUE(user_id, score_date),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reminder_sent (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                prayer_key  TEXT,
                sent_date   TEXT,
                UNIQUE(user_id, prayer_key, sent_date)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id           SERIAL PRIMARY KEY,
                user_id      BIGINT,
                challenge_id TEXT,
                week_start   TEXT,
                completed    INTEGER DEFAULT 0,
                progress     INTEGER DEFAULT 0,
                xp_awarded   INTEGER DEFAULT 0,
                UNIQUE(user_id, challenge_id, week_start),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id          SERIAL PRIMARY KEY,
                name        TEXT,
                invite_code TEXT UNIQUE,
                created_by  BIGINT,
                created_at  TEXT DEFAULT (CURRENT_TIMESTAMP::TEXT)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                group_id    INTEGER,
                user_id     BIGINT,
                joined_at   TEXT DEFAULT (CURRENT_TIMESTAMP::TEXT),
                PRIMARY KEY (group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS missed_followup_sent (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                prayer_key  TEXT,
                sent_date   TEXT,
                UNIQUE(user_id, prayer_key, sent_date)
            )
        """)

        # ── Migrate older DBs missing v2 columns ──────────────
        migrations = [
            ("users",     "total_xp",     "INTEGER DEFAULT 0"),
            ("users",     "level",        "INTEGER DEFAULT 1"),
            ("users",     "reminders_on", "INTEGER DEFAULT 1"),
            ("users",     "onboarding",   "INTEGER DEFAULT 0"),
            ("deed_logs", "xp_earned",    "INTEGER DEFAULT 0"),
            ("deed_logs", "jamaah",       "INTEGER DEFAULT 0"),
        ]
        for table, col, definition in migrations:
            try:
                await conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {definition}"
                )
                logger.info(f"Migrated: added {table}.{col}")
            except Exception:
                pass

        # ── Deduplicate goals ──────────────────────────────────
        await conn.execute("""
            DELETE FROM goals WHERE id NOT IN (
                SELECT MIN(id) FROM goals GROUP BY user_id, deed_key
            )
        """)
        logger.info("Goals deduplication done")

    logger.info("DB v2 tables ready (PostgreSQL)")


# ── Users ──────────────────────────────────────────────────

async def upsert_user(user_id, username, first_name):
    await pool.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT(user_id) DO UPDATE SET
            username=EXCLUDED.username,
            first_name=EXCLUDED.first_name
    """, user_id, username or "", first_name or "")


async def get_user(user_id) -> Optional[dict]:
    row = await pool.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
    return dict(row) if row else None


async def get_all_active_users():
    rows = await pool.fetch("SELECT * FROM users WHERE active=1")
    return [dict(r) for r in rows]


async def update_user_location(user_id, city, country, lat, lng):
    await pool.execute(
        "UPDATE users SET city=$1,country=$2,latitude=$3,longitude=$4 WHERE user_id=$5",
        city, country, lat, lng, user_id
    )


async def update_user_reminders(user_id, on: bool):
    await pool.execute(
        "UPDATE users SET reminders_on=$1 WHERE user_id=$2",
        1 if on else 0, user_id
    )


async def add_xp(user_id: int, xp: int) -> tuple:
    """Add XP, update level. Returns (new_level, leveled_up, total_xp)."""
    row = await pool.fetchrow(
        "SELECT total_xp, level FROM users WHERE user_id=$1", user_id
    )
    old_xp    = row["total_xp"] if row else 0
    old_level = row["level"]    if row else 1
    new_xp    = old_xp + xp
    new_level = level_from_xp(new_xp)
    leveled_up = new_level > old_level
    await pool.execute(
        "UPDATE users SET total_xp=$1, level=$2 WHERE user_id=$3",
        new_xp, new_level, user_id
    )
    return new_level, leveled_up, new_xp


# ── Goals ──────────────────────────────────────────────────

DEFAULT_GOALS = [
    ("fajr",           "Fajr prayer",       3),
    ("dhuhr",          "Dhuhr prayer",      3),
    ("asr",            "Asr prayer",        3),
    ("maghrib",        "Maghrib prayer",    3),
    ("isha",           "Isha prayer",       3),
    ("sunnah_rawatib", "Sunnah rawatib",    2),
    ("quran",          "Quran (1 page)",    2),
    ("dhikr",          "Dhikr after salah", 1),
]


async def add_default_goals(user_id):
    async with pool.acquire() as conn:
        for key, label, pts in DEFAULT_GOALS:
            await conn.execute("""
                INSERT INTO goals (user_id, deed_key, deed_label, points)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, deed_key) DO NOTHING
            """, user_id, key, label, pts)


async def get_user_goals(user_id):
    rows = await pool.fetch(
        "SELECT * FROM goals WHERE user_id=$1 AND active=1 ORDER BY id", user_id
    )
    return [dict(r) for r in rows]


async def add_goal(user_id, deed_key, deed_label, points):
    await pool.execute("""
        INSERT INTO goals (user_id, deed_key, deed_label, points)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, deed_key) DO NOTHING
    """, user_id, deed_key, deed_label, points)


# ── Deed Logging ───────────────────────────────────────────

async def log_deed(user_id, deed_key, deed_label, points, jamaah=0, log_date=None):
    if not log_date:
        log_date = date.today().isoformat()
    bonus     = 1 if jamaah and deed_key in ("fajr","dhuhr","asr","maghrib","isha") else 0
    total_pts = points + bonus
    xp        = total_pts * XP_PER_POINT

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM deed_logs WHERE user_id=$1 AND deed_key=$2 AND log_date=$3",
            user_id, deed_key, log_date
        )
        if existing:
            return False, 0

        await conn.execute("""
            INSERT INTO deed_logs (user_id, deed_key, deed_label, points, xp_earned, log_date, jamaah)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, user_id, deed_key, deed_label, total_pts, xp, log_date, jamaah)

        await conn.execute("""
            INSERT INTO daily_scores (user_id, score_date, score, max_score)
            VALUES ($1, $2, $3, 0)
            ON CONFLICT(user_id, score_date) DO UPDATE SET score=daily_scores.score+EXCLUDED.score
        """, user_id, log_date, total_pts)

    return True, xp


async def get_today_logs(user_id):
    today = date.today().isoformat()
    return await get_logs_for_date(user_id, today)


async def get_logs_for_date(user_id, log_date):
    rows = await pool.fetch(
        "SELECT * FROM deed_logs WHERE user_id=$1 AND log_date=$2 ORDER BY logged_at",
        user_id, log_date
    )
    return [dict(r) for r in rows]


async def get_week_logs(user_id):
    today      = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    rows = await pool.fetch("""
        SELECT log_date, deed_key, deed_label, points, jamaah
        FROM deed_logs WHERE user_id=$1 AND log_date>=$2
        ORDER BY log_date, logged_at
    """, user_id, week_start)
    return [dict(r) for r in rows]


async def get_month_scores(user_id, year, month):
    prefix = f"{year}-{month:02d}"
    rows = await pool.fetch("""
        SELECT score_date, score FROM daily_scores
        WHERE user_id=$1 AND score_date LIKE $2
        ORDER BY score_date
    """, user_id, f"{prefix}%")
    return [dict(r) for r in rows]


async def get_streak(user_id, deed_key):
    rows = await pool.fetch(
        "SELECT log_date FROM deed_logs WHERE user_id=$1 AND deed_key=$2 ORDER BY log_date DESC",
        user_id, deed_key
    )
    dates  = {r["log_date"] for r in rows}
    streak = 0
    check  = date.today()
    while check.isoformat() in dates:
        streak += 1
        check  -= timedelta(days=1)
    return streak


async def check_all5_today(user_id, log_date=None):
    """Returns True if all 5 prayers logged for the given date."""
    if not log_date:
        log_date = date.today().isoformat()
    prayers = {"fajr","dhuhr","asr","maghrib","isha"}
    rows = await pool.fetch(
        "SELECT deed_key FROM deed_logs WHERE user_id=$1 AND log_date=$2 AND deed_key=ANY($3::text[])",
        user_id, log_date, list(prayers)
    )
    done = {r["deed_key"] for r in rows}
    return prayers.issubset(done)


# ── Reminders dedup ────────────────────────────────────────

async def mark_reminder_sent(user_id, prayer_key, sent_date):
    result = await pool.execute(
        "INSERT INTO reminder_sent (user_id,prayer_key,sent_date) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
        user_id, prayer_key, sent_date
    )
    return result == "INSERT 0 1"


async def mark_missed_followup_sent(user_id, prayer_key, sent_date):
    result = await pool.execute(
        "INSERT INTO missed_followup_sent (user_id,prayer_key,sent_date) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
        user_id, prayer_key, sent_date
    )
    return result == "INSERT 0 1"


# ── Groups ─────────────────────────────────────────────────

async def create_group(name: str, creator_id: int) -> dict:
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    async with pool.acquire() as conn:
        group_id = await conn.fetchval(
            "INSERT INTO groups (name, invite_code, created_by) VALUES ($1,$2,$3) RETURNING id",
            name, code, creator_id
        )
        await conn.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES ($1,$2)",
            group_id, creator_id
        )
    return {"id": group_id, "name": name, "invite_code": code}


async def join_group(invite_code: str, user_id: int) -> Optional[dict]:
    async with pool.acquire() as conn:
        group = await conn.fetchrow("SELECT * FROM groups WHERE invite_code=$1", invite_code)
        if not group:
            return None
        await conn.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
            group["id"], user_id
        )
    return dict(group)


async def get_user_groups(user_id: int) -> list:
    rows = await pool.fetch("""
        SELECT g.* FROM groups g
        JOIN group_members gm ON g.id=gm.group_id
        WHERE gm.user_id=$1
    """, user_id)
    return [dict(r) for r in rows]


async def reset_progress(user_id: int):
    """Wipe all logs and XP for a user, keeping their account and settings."""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM deed_logs       WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM daily_scores    WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM challenges      WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM reminder_sent   WHERE user_id=$1", user_id)
        await conn.execute("UPDATE users SET total_xp=0, level=1 WHERE user_id=$1", user_id)


async def get_total_users() -> int:
    return await pool.fetchval("SELECT COUNT(*) FROM users") or 0


async def get_all_users_admin() -> list:
    rows = await pool.fetch(
        "SELECT user_id, username, first_name, city, active, total_xp, level, joined_at FROM users ORDER BY joined_at DESC"
    )
    return [dict(r) for r in rows]


async def set_user_active(user_id: int, active: bool):
    await pool.execute(
        "UPDATE users SET active=$1 WHERE user_id=$2",
        1 if active else 0, user_id
    )


async def is_new_user(user_id: int) -> bool:
    """Returns True if user does not yet exist in DB."""
    row = await pool.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
    return row is None


async def get_group_leaderboard(group_id: int, period_start: str) -> list:
    rows = await pool.fetch("""
        SELECT u.user_id, u.first_name, u.username, u.level,
               COALESCE(SUM(dl.points),0) as points
        FROM group_members gm
        JOIN users u ON u.user_id=gm.user_id
        LEFT JOIN deed_logs dl ON dl.user_id=u.user_id AND dl.log_date>=$1
        WHERE gm.group_id=$2
        GROUP BY u.user_id, u.first_name, u.username, u.level
        ORDER BY points DESC
    """, period_start, group_id)
    return [dict(r) for r in rows]
