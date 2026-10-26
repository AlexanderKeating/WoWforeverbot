"""
See exactly what the bot will post, without Discord.

  python -m forever_bot.preview                      # today, sample data
  python -m forever_bot.preview --date 2026-10-25    # any day
  python -m forever_bot.preview --all                # every day through raids
  python -m forever_bot.preview --live               # really fetch news/clips (needs network, Twitch keys)
"""
import argparse
import asyncio
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import content as C
from . import render as R

SAMPLE = {
    "news": [
        {"id": "news:a", "title": "WoW Forever Stress Test Times & Beta End Date Announced", "source": "Warcraft Tavern",
         "url": "https://www.warcrafttavern.com/forever/news/wow-forever-stress-test-times-beta-end-date-announced/",
         "published": None},
    ],
    "clips": [
        {"id": "twitch:x", "url": "https://clips.twitch.tv/Example", "title": "[clip title as written]",
         "author": "Xaryu", "views": 48211, "published": None},
    ],
    "videos": [],
    "health": {"news:Warcraft Tavern": "ok", "twitch": "ok"},
    "fetched_at": 0,
}


@dataclass
class Cfg:
    tz: str = C.DEFAULT_TZ
    faction: str = "horde"
    ping_role_id: int | None = 1234
    post_time: str = C.DEFAULT_POST_TIME
    verbosity: str = "standard"


def at_post_time(d: date, cfg: Cfg) -> datetime:
    h, m = map(int, cfg.post_time.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=ZoneInfo(cfg.tz)).astimezone(timezone.utc)


def show(post, label=""):
    print("=" * 72, label)
    if post is None:
        print("(nothing posted: countdown finished)")
        return
    if post.content:
        print(post.content)
    for e in post.embeds:
        print(f"┌─ {e['title']}")
        for line in e["description"].split("\n"):
            print(f"│ {line}")
        print("└─")
    if post.rollcall:
        print("[" + "] [".join(C.CLASSES) + "]")
    if post.followup:
        print(post.followup)
    total = sum(len(e["title"]) + len(e["description"]) for e in post.embeds)
    print(f"-- main embed {len(post.embeds[0]['description'])} chars · all embeds {total}/6000 · "
          f"followup {len(post.followup or '')}/2000")


async def live_snap():
    from .fetchers import Twitch, YouTube, refresh_all
    from .store import Store
    store = Store(os.path.join(tempfile.mkdtemp(), "p.db"))
    snap = await refresh_all(store, Twitch(os.getenv("TWITCH_CLIENT_ID", ""), os.getenv("TWITCH_CLIENT_SECRET", "")),
                             YouTube(os.getenv("YOUTUBE_API_KEY", "")))
    print(R.health_text(snap))
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--faction", default="horde")
    ap.add_argument("--slot", type=int, default=0, help="0 = full post, 1+ = check-in")
    ap.add_argument("--level", default="standard", choices=["brief", "standard", "detailed"])
    a = ap.parse_args()
    cfg = Cfg(faction=a.faction, verbosity=a.level)
    snap = asyncio.run(live_snap()) if a.live else SAMPLE
    counts = {c: 0 for c in C.CLASSES}
    if a.all:
        d = date(2026, 10, 24)
        while d <= date(2026, 12, 10):
            show(R.build_daily(cfg, at_post_time(d, cfg), snap, counts), d.isoformat())
            d += timedelta(days=1)
        return
    d = date.fromisoformat(a.date) if a.date else datetime.now(ZoneInfo(cfg.tz)).date()
    show(R.build_daily(cfg, at_post_time(d, cfg), snap, counts, slot=a.slot), f"{d.isoformat()} slot {a.slot}")


if __name__ == "__main__":
    main()
