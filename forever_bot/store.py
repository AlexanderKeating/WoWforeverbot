"""SQLite storage. One small file; survives restarts so nothing double-posts."""
import json
import sqlite3
import threading
import time
from dataclasses import dataclass

from . import content as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    staging_channel_id INTEGER,
    ping_role_id INTEGER,
    post_time TEXT NOT NULL DEFAULT '12:00',
    tz TEXT NOT NULL DEFAULT 'America/Chicago',
    faction TEXT NOT NULL DEFAULT 'horde',
    enabled INTEGER NOT NULL DEFAULT 1,
    hold_date TEXT,
    news_off_date TEXT,
    pin_channel_id INTEGER,
    pin_message_id INTEGER,
    verbosity TEXT NOT NULL DEFAULT 'standard',
    status_alerts INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, detail TEXT, updated_at REAL
);
CREATE TABLE IF NOT EXISTS posts (
    guild_id INTEGER, kind TEXT, key TEXT, posted_at REAL,
    PRIMARY KEY (guild_id, kind, key)
);
CREATE TABLE IF NOT EXISTS seen (
    guild_id INTEGER, item_id TEXT, seen_at REAL,
    PRIMARY KEY (guild_id, item_id)
);
CREATE TABLE IF NOT EXISTS rollcall (
    guild_id INTEGER, user_id INTEGER, cls TEXT, updated_at REAL,
    PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS cache (
    source TEXT PRIMARY KEY, payload TEXT, fetched_at REAL
);
"""


@dataclass
class GuildConfig:
    guild_id: int
    channel_id: int | None = None
    staging_channel_id: int | None = None
    ping_role_id: int | None = None
    post_time: str = C.DEFAULT_POST_TIME
    tz: str = C.DEFAULT_TZ
    faction: str = "neutral"
    enabled: bool = True
    hold_date: str | None = None
    news_off_date: str | None = None
    pin_channel_id: int | None = None
    pin_message_id: int | None = None
    verbosity: str = "standard"
    status_alerts: bool = True


class Store:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self._migrate()
        self.db.commit()

    def _migrate(self):
        """Add columns introduced after v1.0 to existing databases."""
        have = {r[1] for r in self.db.execute("PRAGMA table_info(guilds)")}
        for col, typ in (("pin_channel_id", "INTEGER"), ("pin_message_id", "INTEGER"),
                         ("verbosity", "TEXT NOT NULL DEFAULT 'standard'"),
                         ("status_alerts", "INTEGER NOT NULL DEFAULT 1")):
            if col not in have:
                self.db.execute(f"ALTER TABLE guilds ADD COLUMN {col} {typ}")
        # 1.4.2: faction-neutral by default. Servers that never picked a faction got 'horde' as the old
        # default, so reset them once. Anyone who wants Horde runs /setup faction:Horde.
        if self.db.execute("PRAGMA user_version").fetchone()[0] < 2:
            self.db.execute("UPDATE guilds SET faction='neutral' WHERE faction='horde'")
            self.db.execute("PRAGMA user_version = 2")
            self.db.commit()

    def _x(self, sql, args=()):
        with self._lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    # ---------------------------------------------------------- guilds
    def get_guild(self, guild_id: int) -> GuildConfig | None:
        row = self._x("SELECT * FROM guilds WHERE guild_id=?", (guild_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["enabled"] = bool(d["enabled"])
        d["status_alerts"] = bool(d.get("status_alerts", 1))
        return GuildConfig(**d)

    def all_guilds(self) -> list[GuildConfig]:
        rows = self._x("SELECT * FROM guilds WHERE enabled=1 AND channel_id IS NOT NULL").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["enabled"] = bool(d["enabled"])
            d["status_alerts"] = bool(d.get("status_alerts", 1))
            out.append(GuildConfig(**d))
        return out

    def upsert_guild(self, cfg: GuildConfig):
        self._x(
            """INSERT INTO guilds (guild_id, channel_id, staging_channel_id, ping_role_id, post_time, tz,
                                   faction, enabled, hold_date, news_off_date, pin_channel_id, pin_message_id, verbosity, status_alerts)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id,
                 staging_channel_id=excluded.staging_channel_id, ping_role_id=excluded.ping_role_id,
                 post_time=excluded.post_time, tz=excluded.tz, faction=excluded.faction,
                 enabled=excluded.enabled, hold_date=excluded.hold_date, news_off_date=excluded.news_off_date,
                 pin_channel_id=excluded.pin_channel_id, pin_message_id=excluded.pin_message_id,
                 verbosity=excluded.verbosity, status_alerts=excluded.status_alerts""",
            (cfg.guild_id, cfg.channel_id, cfg.staging_channel_id, cfg.ping_role_id, cfg.post_time,
             cfg.tz, cfg.faction, int(cfg.enabled), cfg.hold_date, cfg.news_off_date,
             cfg.pin_channel_id, cfg.pin_message_id, cfg.verbosity or "standard", int(cfg.status_alerts)),
        )

    def remove_guild(self, guild_id: int):
        """Bot was removed from a server: delete everything stored for it (privacy policy, 1.4)."""
        for t in ("guilds", "rollcall", "posts", "seen"):
            self._x(f"DELETE FROM {t} WHERE guild_id=?", (guild_id,))

    def forget_user(self, user_id: int) -> int:
        """/forgetme: delete this person's settings and roll-call picks everywhere. Returns rows removed."""
        n = self._x("DELETE FROM users WHERE user_id=?", (user_id,)).rowcount
        n += self._x("DELETE FROM rollcall WHERE user_id=?", (user_id,)).rowcount
        return n

    def user_data(self, user_id: int) -> dict:
        """Everything stored about one person, for /mydata."""
        detail = self.get_user_detail(user_id)
        picks = self._x("SELECT guild_id, cls FROM rollcall WHERE user_id=?", (user_id,)).fetchall()
        return {"detail": detail, "rollcall": [(int(g), c) for g, c in picks]}

    # ---------------------------------------------------------- posts (dedupe)
    def was_posted(self, guild_id: int, kind: str, key: str) -> bool:
        return self._x("SELECT 1 FROM posts WHERE guild_id=? AND kind=? AND key=?",
                       (guild_id, kind, key)).fetchone() is not None

    def mark_posted(self, guild_id: int, kind: str, key: str):
        self._x("INSERT OR IGNORE INTO posts VALUES (?,?,?,?)", (guild_id, kind, key, time.time()))

    def recent_posts(self, guild_id: int, limit: int = 5) -> list[tuple[str, str, float]]:
        rows = self._x("SELECT kind, key, posted_at FROM posts WHERE guild_id=? ORDER BY posted_at DESC LIMIT ?",
                       (guild_id, limit)).fetchall()
        return [(r["kind"], r["key"], r["posted_at"]) for r in rows]

    def stats(self) -> dict:
        one = lambda q: self._x(q).fetchone()[0]
        return {"guilds": one("SELECT COUNT(*) FROM guilds WHERE enabled=1 AND channel_id IS NOT NULL"),
                "posts": one("SELECT COUNT(*) FROM posts"), "rollcall": one("SELECT COUNT(*) FROM rollcall")}

    # ---------------------------------------------------------- seen items (news/clips)
    def unseen(self, guild_id: int, item_ids: list[str]) -> set[str]:
        if not item_ids:
            return set()
        q = ",".join("?" * len(item_ids))
        rows = self._x(f"SELECT item_id FROM seen WHERE guild_id=? AND item_id IN ({q})",
                       (guild_id, *item_ids)).fetchall()
        return set(item_ids) - {r["item_id"] for r in rows}

    def mark_seen(self, guild_id: int, item_ids: list[str]):
        now = time.time()
        with self._lock:
            self.db.executemany("INSERT OR IGNORE INTO seen VALUES (?,?,?)",
                                [(guild_id, i, now) for i in item_ids])
            self.db.commit()

    def prune_seen(self, older_than_days: int = 60):
        self._x("DELETE FROM seen WHERE seen_at < ?", (time.time() - older_than_days * 86400,))

    # ---------------------------------------------------------- per-user detail level
    def set_user_detail(self, user_id: int, detail: str | None):
        if detail is None:
            self._x("DELETE FROM users WHERE user_id=?", (user_id,))
        else:
            self._x("INSERT INTO users VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET detail=excluded.detail, "
                    "updated_at=excluded.updated_at", (user_id, detail, time.time()))

    def get_user_detail(self, user_id: int) -> str | None:
        row = self._x("SELECT detail FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["detail"] if row else None

    # ---------------------------------------------------------- roll call
    def set_class(self, guild_id: int, user_id: int, cls: str):
        self._x("INSERT INTO rollcall VALUES (?,?,?,?) ON CONFLICT(guild_id,user_id) "
                "DO UPDATE SET cls=excluded.cls, updated_at=excluded.updated_at",
                (guild_id, user_id, cls, time.time()))

    def class_counts(self, guild_id: int) -> dict[str, int]:
        rows = self._x("SELECT cls, COUNT(*) n FROM rollcall WHERE guild_id=? GROUP BY cls",
                       (guild_id,)).fetchall()
        counts = {c: 0 for c in C.CLASSES}
        for r in rows:
            if r["cls"] in counts:
                counts[r["cls"]] = r["n"]
        return counts

    def rollcall_list(self, guild_id: int) -> dict[str, list[int]]:
        """Class -> user ids who picked it in this server, most recent pick first (1.4.3 /rollcall)."""
        rows = self._x("SELECT cls, user_id FROM rollcall WHERE guild_id=? ORDER BY updated_at DESC",
                       (guild_id,)).fetchall()
        out: dict[str, list[int]] = {}
        for r in rows:
            out.setdefault(r["cls"], []).append(int(r["user_id"]))
        return out

    # ---------------------------------------------------------- source cache
    def cache_put(self, source: str, payload):
        self._x("INSERT INTO cache VALUES (?,?,?) ON CONFLICT(source) DO UPDATE SET "
                "payload=excluded.payload, fetched_at=excluded.fetched_at",
                (source, json.dumps(payload), time.time()))

    def cache_get(self, source: str):
        row = self._x("SELECT payload, fetched_at FROM cache WHERE source=?", (source,)).fetchone()
        if not row:
            return None, None
        try:
            return json.loads(row["payload"]), row["fetched_at"]
        except (ValueError, TypeError):
            return None, None
