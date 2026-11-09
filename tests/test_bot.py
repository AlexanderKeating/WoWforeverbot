"""Offline tests: python -m pytest tests -q   (or python tests/test_bot.py)"""
import asyncio
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from forever_bot import content as C  # noqa: E402
from forever_bot import fetchers as F  # noqa: E402
from forever_bot import render as R  # noqa: E402
from forever_bot.preview import SAMPLE, Cfg, at_post_time  # noqa: E402
from forever_bot.store import Store  # noqa: E402


def tmp_store():
    return Store(os.path.join(tempfile.mkdtemp(), "t.db"))


# ------------------------------------------------------------- 1.10 owner alerts
def test_owner_alert_text():
    j = R.owner_alert_text("join", 6, 9)
    assert j == "➕ Added to a server (6 members). Now in **9** servers."
    assert R.owner_alert_text("setup", 6, 9) == "✅ A server (6 members) finished setup. Now in **9** servers."
    r = R.owner_alert_text("remove", 4, 8, stayed_s=6 * 60 + 40, was_set_up=False)
    assert r == "➖ Removed from a server (4 members) after 6 minutes, never set up. Now in **8** servers."
    assert R.owner_alert_text("remove", None, 7) == "➖ Removed from a server. Now in **7** servers."
    assert R._stayed(30) == "under a minute" and R._stayed(3 * 3600) == "3 hours" and R._stayed(None) == ""
    assert R._stayed(3 * 86400) == "3 days" and R._stayed(60) == "1 minute"


def test_postnow_outcome():
    from forever_bot.bot import postnow_outcome as o
    assert o("Posted.") == "posted" and o("Already posted for this time slot.") == "already_posted"
    assert o("Nothing to post: the countdown is finished.") == "finished"
    assert o("⚠️ I can't post in <#1>: missing perms.") == "blocked" and o("Discord rejected the post: x") == "failed"
    assert o("something new") == "other"


def test_owner_dm_on_real_bot():
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "b.db")
    from types import SimpleNamespace
    from forever_bot.bot import ForeverBot
    b = ForeverBot()
    sent = []

    class U:
        async def send(self, t):
            sent.append(t)

    async def app_info():
        return SimpleNamespace(team=None, owner=SimpleNamespace(id=77))

    b.application_info = app_info
    b.get_user = lambda uid: U() if uid == 77 else None
    os.environ.pop("OWNER_ID", None)
    os.environ.pop("OWNER_ALERTS", None)
    asyncio.run(b.notify_owner("hello", kind="join", guild=1))
    assert sent == ["hello"]


# ------------------------------------------------------------- matching
def test_forever_matching_variants():
    yes = ["WoW: Forever launch time", "World of Warcraft: Forever beta", "#WoWForever is here",
           "WORLD OF WARCRAFT FOREVER", "Classic+ PvP talk", "Skyborne druid forms", "Darkspear Islands guide",
           "Forever Open recap", "warcraft forever patch notes", "Wow  Forever  hotfixes",
           "Forever: new Horde raid info", "Shen’dralas zone preview", "Barrow-Deeps loot"]
    no = ["Diamonds are forever", "Midnight Season 2 tier list", "Forever 21 sale", "Hearthstone patch", ""]
    for t in yes:
        assert F.is_forever(t), t
    for t in no:
        assert not F.is_forever(t), t


def test_blocklist_and_excerpt():
    assert not F.is_clean("this is f*u*c*k crazy".replace("*", ""))
    assert F.is_clean("Insane 1v3 on a warlock")
    long = "word " * 80
    ex = F.excerpt(long, 200)
    assert len(ex) <= 201 and ex.endswith("…")
    assert F.excerpt("<p>Hi &amp; bye</p>") == "Hi & bye"


def test_feed_autodiscovery():
    page = '''<html><head><link type="application/rss+xml" rel="alternate" href="/feed/" title="x">
              <LINK REL='alternate' TYPE='application/atom+xml' HREF='https://ex.com/atom'></head></html>'''
    assert F.discover_feeds(page, "https://ex.com/news/") == ["https://ex.com/feed/", "https://ex.com/atom"]


RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>WoW Forever Layering Explained</title><link>https://ex.com/a?utm=1</link>
 <pubDate>{now}</pubDate><description>about forever</description></item>
<item><title>Retail Midnight hotfixes</title><link>https://ex.com/b</link><pubDate>{now}</pubDate></item>
<item><title>Old Forever news</title><link>https://ex.com/c</link><pubDate>Mon, 01 Sep 2026 10:00:00 GMT</pubDate>
 <description>World of Warcraft Forever</description></item>
<item><title></title><link>https://ex.com/d</link></item>
</channel></rss>"""


def test_parse_and_filter_feed():
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items = F.parse_feed(RSS.format(now=now), "Ex")
    assert len(items) == 3  # empty title dropped
    kept = [i for i in items if F.is_forever(i.pop("_match_text"))]
    assert [i["title"] for i in kept] == ["WoW Forever Layering Explained", "Old Forever news"]
    assert kept[0]["id"] == "news:https://ex.com/a"
    try:
        F.parse_feed("<html>not a feed</html>", "x")
        assert False
    except F.FetchError:
        pass


def test_dedupe_news():
    a = {"id": "1", "title": "WoW Forever Launch!", "url": "https://x.com/a/", "published": "2026-10-24T01:00:00+00:00"}
    b = {"id": "2", "title": "wow forever launch", "url": "https://y.com/z", "published": "2026-10-24T02:00:00+00:00"}
    c = {"id": "3", "title": "Other", "url": "https://x.com/a", "published": None}
    assert [i["id"] for i in F.dedupe_news([a, b, c])] == ["1"]


# ------------------------------------------------------------- fallbacks
def test_guarded_uses_cache_then_gives_up():
    store = tmp_store()

    async def good():
        return [{"id": "x"}]

    async def bad():
        raise F.FetchError("boom")

    data, status = asyncio.run(F._guarded(store, "s", good))
    assert status == "ok" and data == [{"id": "x"}]
    data, status = asyncio.run(F._guarded(store, "s", bad))
    assert data == [{"id": "x"}] and status.startswith("stale")
    store._x("UPDATE cache SET fetched_at=?", (time.time() - 40 * 3600,))
    data, status = asyncio.run(F._guarded(store, "s", bad))
    assert data == [] and status.startswith("down")

    async def crash():
        raise RuntimeError("unexpected shape")
    data, status = asyncio.run(F._guarded(store, "other", crash))
    assert data == [] and "down" in status


def test_news_source_falls_back_to_autodiscovery():
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    pages = {
        "https://ex.com/feed-a": F.FetchError("404 (https://ex.com/feed-a)"),
        "https://ex.com/home": '<link rel="alternate" type="application/rss+xml" href="/real-feed">',
        "https://ex.com/real-feed": RSS.format(now=now),
    }

    async def fake_get(session, url, **kw):
        v = pages[url]
        if isinstance(v, Exception):
            raise v
        return v

    orig = F.http_get
    F.http_get = fake_get
    try:
        items = asyncio.run(F.fetch_news_source(None, {"name": "Ex", "feeds": ["https://ex.com/feed-a"],
                                                       "home": "https://ex.com/home"}))
    finally:
        F.http_get = orig
    assert [i["title"] for i in items] == ["WoW Forever Layering Explained"]  # old item aged out


def test_twitch_category_fallback_and_filtering():
    tw = F.Twitch("id", "secret")
    tw._token, tw._token_exp = "t", time.time() + 999
    calls = []

    async def fake_get(session, path, params):
        calls.append(path)
        if path == "games":
            return {"data": [{"id": "18122", "name": "World of Warcraft"}]}  # exact Forever name not found
        if path == "search/categories":
            return {"data": [{"id": "999", "name": "World of Warcraft: Forever"}, {"id": "5", "name": "Forever Skies"}]}
        if path == "users":
            return {"data": [{"id": "u1", "login": "xaryu", "display_name": "Xaryu"}]}
        if path == "clips":
            p = dict(params) if isinstance(params, list) else params
            if p.get("game_id") == "999":
                return {"data": [
                    {"id": "c1", "url": "u1", "title": "huge 1v3", "broadcaster_name": "A", "view_count": 100, "game_id": "999"},
                    {"id": "c2", "url": "u2", "title": "what the fuck", "broadcaster_name": "B", "view_count": 9999, "game_id": "999"}]}
            if p.get("broadcaster_id") == "u1":
                return {"data": [
                    {"id": "c3", "url": "u3", "title": "xar duel", "broadcaster_name": "Xaryu", "view_count": 80, "game_id": "999"},
                    {"id": "c4", "url": "u4", "title": "Just Chatting", "broadcaster_name": "Xaryu", "view_count": 5000, "game_id": "509658"}]}
            return {"data": []}
        raise AssertionError(path)

    tw.get = fake_get
    clips = asyncio.run(tw.top_clips(None))
    titles = [c["title"] for c in clips]
    assert titles == ["xar duel", "huge 1v3"]  # pinned boost 80*1.5 > 100; profanity + off-game dropped
    assert "search/categories" in calls


def test_twitch_loose_clips_before_category_exists():
    tw = F.Twitch("id", "secret")
    tw._token, tw._token_exp = "t", time.time() + 999

    async def fake_get(session, path, params):
        if path == "games":
            return {"data": [{"id": "18122", "name": "World of Warcraft"}]}
        if path == "search/categories":
            return {"data": []}  # no Forever category yet
        if path == "users":
            return {"data": [{"id": "u1", "login": "xaryu", "display_name": "Xaryu"}]}
        if path == "clips":
            p = dict(params) if isinstance(params, list) else params
            if p.get("game_id") == "18122":
                return {"data": [{"id": "r1", "url": "r", "title": "random wow clip", "broadcaster_name": "Rando",
                                  "view_count": 9000, "game_id": "18122"}]}
            if p.get("broadcaster_id") == "u1":
                return {"data": [
                    {"id": "x1", "url": "a", "title": "insane duel", "broadcaster_name": "Xaryu", "view_count": 300, "game_id": "18122"},
                    {"id": "x2", "url": "b", "title": "another one", "broadcaster_name": "Xaryu", "view_count": 200, "game_id": "18122"},
                    {"id": "x3", "url": "c", "title": "valorant ace", "broadcaster_name": "Xaryu", "view_count": 999, "game_id": "516575"},
                    {"id": "x4", "url": "d", "title": "Forever beta talents", "broadcaster_name": "Xaryu", "view_count": 50, "game_id": "18122"}]}
            return {"data": []}
        raise AssertionError(path)

    tw.get = fake_get
    clips = asyncio.run(tw.top_clips(None))
    assert [c["title"] for c in clips] == ["Forever beta talents"]  # 1.6.1: one clip per streamer, Forever first
    assert not clips[0].get("loose")
    snap = {"news": [], "clips": clips + [{"id": "twitch:l", "url": "l", "title": "loose one", "author": "Other",
                                           "views": 90, "loose": True}], "videos": []}
    cfg = Cfg()
    out = json.dumps(R.build_daily(cfg, at_post_time(date(2026, 10, 27), cfg), snap, {}, slot=0).__dict__, default=str)
    assert "WoW clips from streamers we follow" in out and "Not necessarily Forever" in out


# ------------------------------------------------------------- rendering
def test_every_day_renders_within_limits():
    cfg = Cfg()
    d = date(2026, 10, 20)
    counts = {c: 3 for c in C.CLASSES}
    while d <= date(2027, 2, 15):  # 1.12: no end date; keeps posting after raids
        post = R.build_daily(cfg, at_post_time(d, cfg), SAMPLE, counts)
        if True:
            assert post is not None, d
            total = sum(len(e["title"]) + len(e["description"]) for e in post.embeds)
            assert total < 6000 and all(len(e["description"]) <= 4096 for e in post.embeds)
            assert len(post.followup or "") <= 2000
            assert "None" not in post.embeds[0]["description"]
        d += timedelta(days=1)


def test_checkins_render_and_differ():
    cfg = Cfg()
    d = date(2026, 10, 24)
    while d <= date(2026, 12, 9):
        full = R.build_daily(cfg, at_post_time(d, cfg), SAMPLE, {}, slot=0)
        texts = {full.embeds[0]["description"]}
        for slot in (1, 2, 3):
            ci = R.build_daily(cfg, at_post_time(d, cfg), SAMPLE, None, slot=slot)
            assert ci and ci.key.endswith(f":{slot}") and not ci.rollcall and ci.content == ""
            assert sum(len(e["title"]) + len(e["description"]) for e in ci.embeds) < 6000
            texts.add(ci.embeds[0]["description"])
        assert len(texts) >= 3  # check-ins aren't copies of each other or the full post
        d += timedelta(days=1)


def test_timezone_day_boundaries():
    cfg = Cfg(tz="Pacific/Auckland")
    # Nov 4 23:00 UTC is already Nov 5 in Auckland -> launch day was "yesterday" there
    assert R.phase("Pacific/Auckland", datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)) == ("launch", 0)
    assert R.phase("America/Los_Angeles", datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)) == ("launch", 0)
    assert R.phase(C.DEFAULT_TZ, datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc))[1] == 1
    assert R.build_daily(cfg, datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc), {}, None) is not None


def test_unseen_filtering_and_faction():
    cfg = Cfg(faction="alliance")
    post = R.build_daily(cfg, at_post_time(date(2026, 10, 25), cfg), SAMPLE, None, unseen_ids=set())
    assert len(post.embeds) == 1 and post.followup is None and post.used_ids == []
    assert not post.rollcall
    for _ in range(40):
        pass
    assert "Horde main" not in post.embeds[0]["description"]


def test_markdown_escaping():
    s = R.esc("[gg] **ez** @everyone")
    assert "\\[" in s and "\\*" in s and "@​everyone" in s


def test_spellbook_pages():
    member, admin_ = R.spellbook_pages(False), R.spellbook_pages(True)
    assert "officer" not in member and "officer" in admin_
    e = R.spellbook_embed("officer", {}, False)  # members can't open the officer page
    assert "Officer" not in e["title"]
    e = R.spellbook_embed("learn", {"tips": 42}, False)
    assert "</tips:42>" in e["description"] and "`/faq`" in e["description"]


def test_youtube_top_videos():
    yt = F.YouTube("k")
    calls = []

    async def fake_get(session, url, params=None, want_json=False, **kw):
        calls.append(url.rsplit("/", 1)[1])
        if url.endswith("/search"):
            return {"items": [
                {"id": {"videoId": "a"}, "snippet": {"title": "WoW Forever Warlock guide", "channelTitle": "A"}},
                {"id": {"videoId": "b"}, "snippet": {"title": "Midnight M+ tier list", "channelTitle": "B"}},
                {"id": {"videoId": "c"}, "snippet": {"title": "World of Warcraft: Forever short", "channelTitle": "C"}},
                {"id": {"videoId": "d"}, "snippet": {"title": "Forever launch hype &amp; prep", "channelTitle": "D"}},
                {"id": {}, "snippet": {"title": "a channel result"}}]}
        return {"items": [
            {"id": "a", "snippet": {"title": "WoW Forever Warlock guide", "description": "x " * 200, "channelTitle": "A"},
             "statistics": {"viewCount": "500"}, "contentDetails": {"duration": "PT12M3S"}},
            {"id": "c", "snippet": {"title": "World of Warcraft: Forever short", "channelTitle": "C"},
             "statistics": {"viewCount": "99999"}, "contentDetails": {"duration": "PT45S"}},
            {"id": "d", "snippet": {"title": "Forever launch hype &amp; prep", "description": "Classic wow", "channelTitle": "D"},
             "statistics": {"viewCount": "900"}, "contentDetails": {"duration": "PT1H2M"}}]}

    orig = F.http_get
    F.http_get = fake_get
    try:
        vids = asyncio.run(yt.top_videos(None))
        assert [v["title"] for v in vids] == ["Forever launch hype & prep", "WoW Forever Warlock guide"]  # by views; Short + off-topic dropped
        assert vids[1]["description"].endswith("…") and vids[0]["url"].endswith("v=d")
        asyncio.run(yt.top_videos(None))
        assert calls.count("search") == 1  # cached between searches to save quota

        async def quota(session, url, **kw):
            raise F.FetchError("403 (x)")
        F.http_get = quota
        yt2 = F.YouTube("k")
        try:
            asyncio.run(yt2.top_videos(None))
            assert False
        except F.FetchError as e:
            assert "quota" in str(e)
    finally:
        F.http_get = orig


def test_logging_redacts_and_formats():
    import json as _json
    import logging as _logging
    from forever_bot import logsetup as L
    os.environ["YOUTUBE_API_KEY"] = "AIzaFAKEKEY1234567"
    rec = _logging.LogRecord("forever.fetch", _logging.WARNING, __file__, 1,
                             "GET https://x/?key=AIzaFAKEKEY1234567 failed", (), None)
    assert L.RedactFilter().filter(rec) and "AIzaFAKEKEY" not in rec.getMessage() and "***" in rec.getMessage()
    rec2 = _logging.LogRecord("forever.sched", _logging.INFO, __file__, 1, "post_sent", (), None)
    rec2.fields = {"event": "post_sent", "guild": 1, "error": 'has "quotes" and spaces'}
    line = L.TextFormatter().format(rec2)
    assert "event=post_sent guild=1" in line and "error=\"has 'quotes' and spaces\"" in line
    assert _json.loads(L.JsonFormatter().format(rec2))["event"] == "post_sent"
    del os.environ["YOUTUBE_API_KEY"]


def test_classtips_all_classes():
    from forever_bot import classes as K
    assert set(K.CLASSES) == set(C.CLASSES)
    for cls in C.CLASSES:
        e = R.classtips_embed(cls)
        assert e and len(e["description"]) < 4096
        assert all(0 < len(f["value"]) <= 1024 and len(f["name"]) <= 256 for f in e["fields"])
        total = len(e["title"]) + len(e["description"]) + len(e["footer"]["text"]) + sum(
            len(f["name"]) + len(f["value"]) for f in e["fields"])
        assert total < 6000
        assert R.tourney_line(cls)  # every class has finals data
    assert R.tourney_line("Warlock").startswith("26–7")
    assert R.classtips_embed("Deathknight") is None


def test_pinned_card():
    cfg = Cfg()
    for when in (datetime(2026, 10, 25, 18, tzinfo=timezone.utc), datetime(2026, 11, 10, tzinfo=timezone.utc),
                 datetime(2026, 12, 20, tzinfo=timezone.utc)):
        e = R.pinned_embed(cfg, [(12, 0), (19, 0)], when, "https://discord.com/channels/1/2/3", 555)
        assert len(e["description"]) < 4096 and "<@&555>" in e["description"] and "jump to it" in e["description"]
    assert "**12 PM**" in R._schedule_text([(12, 0), (19, 0)], "America/Chicago")
    assert "7 PM" in R._schedule_text([(12, 0), (19, 0)], "America/Chicago")


def test_every_command_in_spellbook():
    os.environ.setdefault("DB_PATH", os.path.join(tempfile.mkdtemp(), "b.db"))
    from forever_bot import bot as B
    names = {c.name for c in B.bot.tree.get_commands()} - {"help", "spellbook"}
    listed = {sp[0] for page in R.SPELLBOOK.values() for sp in page["spells"]}
    assert names <= listed, names - listed
    assert listed <= names | set(), listed - names


def test_guides_all_classes():
    import re as _re
    from forever_bot import guides as G
    for cls in C.CLASSES:
        for e in (R.keybinds_embed(cls), R.macros_embed(cls), R.rotation_embed(cls)):
            assert e and len(e["description"]) < 4096
            assert all(0 < len(f["value"]) <= 1024 and len(f["name"]) <= 256 for f in e["fields"])
            total = len(e["title"]) + len(e["description"]) + len(e.get("footer", {}).get("text", "")) + sum(
                len(f["name"]) + len(f["value"]) for f in e["fields"])
            assert total < 6000, (cls, e["title"], total)
        for title, text, what, verified in G.MACROS[cls]:
            assert len(text) <= 255, (cls, title)
        assert _re.fullmatch(r"[A-Za-z]{4,10}", cls)  # fits the class-guide button id pattern
    for t in ("basics", "controller"):
        assert len(R.keybinds_embed(None, t)["description"]) < 4096


def test_quiz():
    import itertools
    from forever_bot import guides as G
    tops = set()
    for combo in itertools.product(*[range(len(opts)) for _, opts in G.QUIZ]):
        ranked = G.score_quiz(list(combo))
        tops.add(ranked[0][0])
    assert tops == set(C.CLASSES), set(C.CLASSES) - tops  # every class can win
    for _, opts in G.QUIZ:
        assert 2 <= len(opts) <= 5 and all(len(lbl) <= 80 for lbl, _ in opts)
    e = R.quiz_result_embed([0] * len(G.QUIZ))
    assert "Your match" in e["description"]


def test_event_pings():
    stamps = [datetime.fromisoformat(i) for i, _, _ in C.EVENT_PINGS]
    assert stamps == sorted(stamps) and all(s.tzinfo for s in stamps)
    assert len({k for _, k, _ in C.EVENT_PINGS}) == len(C.EVENT_PINGS)
    assert datetime.fromisoformat(C.EVENT_PINGS[1][0]) == datetime(2026, 10, 27, 20, tzinfo=timezone.utc)  # 1 PM PDT


def test_detail_levels():
    from forever_bot import guides as G
    cfg = Cfg()
    d = date(2026, 10, 24)
    while d <= date(2026, 12, 9):
        sizes = []
        for lvl in R.LEVELS:
            cfg.verbosity = lvl
            for slot in (0, 1):
                p = R.build_daily(cfg, at_post_time(d, cfg), SAMPLE, {}, slot=slot)
                total = sum(len(e["title"]) + len(e["description"]) for e in p.embeds)
                assert total < 6000 and len(p.embeds[0]["description"]) <= 4096, (d, lvl, slot)
                if slot == 0:
                    sizes.append(len(p.embeds[0]["description"]))
        assert sizes[0] < sizes[1] <= sizes[2], (d, sizes)  # brief < standard <= detailed
        d += timedelta(days=1)
    cfg.verbosity = "brief"
    brief = R.build_daily(cfg, at_post_time(date(2026, 10, 26), cfg), SAMPLE, {}).embeds[0]["description"]
    assert "🧙" not in brief and "Did you know" not in brief and "🌱" in brief and "Pro tip" in brief
    for key in C.DEEP_DIVES:
        lens = [len(R.deep_dive_embed(str(key), l)["description"]) for l in R.LEVELS]
        assert lens[0] < lens[1] <= lens[2] and lens[2] < 4096, (key, lens)
    for cls in C.CLASSES:
        for l in R.LEVELS:
            for e in (R.classtips_embed(cls, "horde", l), R.keybinds_embed(cls, "basics", l), R.rotation_embed(cls, l)):
                total = len(e["title"]) + len(e["description"]) + len(e["footer"]["text"]) + sum(
                    len(f["name"]) + len(f["value"]) for f in e["fields"])
                assert total < 6000 and all(len(f["value"]) <= 1024 for f in e["fields"]), (cls, l, e["title"])
        assert len(R.classtips_embed(cls, "horde", "brief")["fields"]) < len(R.classtips_embed(cls, "horde", "detailed")["fields"])
    for t in R.TIP_TOPICS:
        assert len(R.tips_embed(t, "brief")["description"]) <= len(R.tips_embed(t, "detailed")["description"])
    assert "Also worth a look" not in R.quiz_result_embed([0] * len(G.QUIZ), "horde", "brief")["description"]
    assert "Your top 4" in R.quiz_result_embed([0] * len(G.QUIZ), "horde", "detailed")["description"]
    assert R.norm_level("weird") == "standard"


def test_user_detail_store():
    st = tmp_store()
    assert st.get_user_detail(1) is None
    st.set_user_detail(1, "brief")
    st.set_user_detail(1, "detailed")
    assert st.get_user_detail(1) == "detailed"
    st.set_user_detail(1, None)
    assert st.get_user_detail(1) is None


def test_store_roundtrip():
    st = tmp_store()
    st.set_class(1, 10, "Mage")
    st.set_class(1, 10, "Warlock")
    st.set_class(1, 11, "Warlock")
    assert st.class_counts(1)["Warlock"] == 2 and st.class_counts(1)["Mage"] == 0
    assert st.unseen(1, ["a", "b"]) == {"a", "b"}
    st.mark_seen(1, ["a"])
    assert st.unseen(1, ["a", "b"]) == {"b"}
    assert not st.was_posted(1, "daily", "k")
    st.mark_posted(1, "daily", "k")
    st.mark_posted(1, "daily", "k")
    assert st.was_posted(1, "daily", "k")


def test_more_detail_button_answers():
    """Regression for 1.2.0: a log call crashed the 📖 button before it replied."""
    import logging, types
    from forever_bot import bot as B
    from forever_bot import logsetup
    logsetup.ev(logging.getLogger("t"), "x", level="standard")  # must not raise
    B.bot.store = tmp_store()
    sent = {}

    class Resp:
        async def send_message(self, *a, **k):
            sent.update(k)
    inter = types.SimpleNamespace(guild_id=1, user=types.SimpleNamespace(id=5), response=Resp())
    key = next(iter(C.DEEP_DIVES))
    asyncio.run(B.DeepDiveButton(key).callback(inter))
    assert sent.get("ephemeral") and sent.get("embed") is not None


def test_plusone_mode():
    import json
    from forever_bot import plusone as P
    from forever_bot import bot as B
    def size(e):
        assert len(e.get("description") or "") <= 4096
        assert all(len(f["value"]) <= 1024 and len(f["name"]) <= 256 for f in e.get("fields", []))
        assert len(json.dumps(e)) < 6000
    size(P.survival_kit_embed()); size(P.partner_card_embed()); size(P.glossary_embed(None))
    assert len(P.hub_intro()) < 2000
    # glossary: direct, alias, miss, autocomplete
    assert P.lookup("Zug Zug")[0] == "zug zug" and P.lookup("rezz")[0] == "rez" and P.lookup("ganked")[0] == "gank"
    assert P.lookup("xyzzy")[0] is None
    assert P.lookup("BIS")[0] == "bis" and P.lookup("best in slot")[0] == "bis" and P.glossary_embed("bis")["title"].endswith("BiS")
    assert all(t in P.GLOSSARY for t in P.STARTER_TERMS) and all(v in P.GLOSSARY for v in P.ALIASES.values())
    assert len(P.glossary_choices("")) <= 25 and P.glossary_choices("ag")[0] == "aggro"
    for t in P.GLOSSARY:
        size(P.glossary_embed(t))
        assert len(t) <= 100
    # panic: every class, every kind, custom_id fits
    for c in P.HORDE_CLASSES:
        assert c in P.PANIC
        for k in P.PANIC_KINDS:
            size(P.panic_embed(c, k)); assert len(f"pd:{c}:{k}") <= 100
    # duo quiz: every combination gives a real Horde class, never the same class unless it's the only fit
    for partner in P.HORDE_CLASSES + [None]:
        for style in P.STYLES:
            for comfort in P.COMFORT:
                pick, why, alt = P.duo_pick(partner, style, comfort)
                assert pick in P.HORDE_CLASSES and why
                size(P.duo_embed(partner, style, comfort))
    # plain words: drops veteran parts, explains jargon once, stays within limits
    for cls in P.HORDE_CLASSES:
        e = P.plainify(R.classtips_embed(cls, "horde", "plain"))
        size(e); assert not any(f["name"].startswith("🧙") for f in e.get("fields", []))
    for k in C.DEEP_DIVES:
        e = P.plainify(R.deep_dive_embed(k, "plain")); size(e)
        assert "🧙" not in (e.get("description") or "")
    out = P.plain_text("Watch the DPS and the DPS", set())
    assert out.count("damage dealers") == 1
    assert P.plain_text("[DPS guide](https://x.com/DPS)", set()) == "[DPS guide](https://x.com/DPS)"
    # commands registered and listed
    names = {c.name for c in B.bot.tree.get_commands()}
    assert {"draggedalong", "whatdoesthatmean"} <= names and len(names) <= 100
    assert R.LEVEL_LABEL["plain"] == "Plain words"


def test_click_log_names():
    import types
    from forever_bot import bot as B
    it = types.SimpleNamespace(message=None)
    assert B._control_name("dd:professions", it) == "more_detail:professions"
    assert B._control_name("pd:Hunter:heal", it) == "panic:Hunter:heal"
    msg = types.SimpleNamespace(embeds=[types.SimpleNamespace(title="📖 Spellbook · Quest log")], content="")
    assert B._control_name("a1b2c3", types.SimpleNamespace(message=msg)).startswith("other:📖 Spellbook")
    inter = types.SimpleNamespace(data={"options": [{"type": 3, "name": "page", "value": "plusone"}]})
    assert B._args(inter) == "page:plusone"


def test_reservation_alerts_post_without_pings():
    import types
    from datetime import datetime, timezone
    from forever_bot import bot as B
    assert C.EVENT_POSTS and not C.NOTIFY
    for iso, key, text in C.EVENT_PINGS:
        assert datetime.fromisoformat(iso).tzinfo and len(text) < 1900
    sent = []

    class Ch:
        guild = types.SimpleNamespace(name="Test")
        async def send(self, content, allowed_mentions=None):
            sent.append((content, allowed_mentions))
    cfg = types.SimpleNamespace(guild_id=1, channel_id=2, ping_role_id=99)
    st = tmp_store()
    fake = types.SimpleNamespace(store=types.SimpleNamespace(all_guilds=lambda: [cfg], was_posted=st.was_posted,
                                                             mark_posted=st.mark_posted),
                                 get_channel=lambda _id: Ch(), _can_post=lambda ch: None,
                                 say_once=lambda *a, **k: None, live_cfg=lambda c: c)
    asyncio.run(B.ForeverBot.send_event_ping(fake, "names-open", "hi"))
    asyncio.run(B.ForeverBot.send_event_ping(fake, "names-open", "hi"))  # deduped
    assert len(sent) == 1 and "<@&" not in sent[0][0]


def test_privacy_deletion():
    st = tmp_store()
    st.set_class(1, 10, "Mage"); st.set_class(2, 10, "Rogue"); st.set_class(1, 11, "Priest")
    st.set_user_detail(10, "plain")
    st.mark_posted(1, "daily", "k"); st.mark_seen(1, ["n1"])
    d = st.user_data(10)
    assert d["detail"] == "plain" and sorted(c for _, c in d["rollcall"]) == ["Mage", "Rogue"]
    assert st.forget_user(10) == 3
    assert st.user_data(10) == {"detail": None, "rollcall": []}
    assert st.class_counts(1)["Priest"] == 1  # other people untouched
    st.remove_guild(1)
    assert st.class_counts(1).get("Priest", 0) == 0 and not st.was_posted(1, "daily", "k")
    assert st.unseen(1, ["n1"]) == {"n1"}
    from forever_bot import bot as B
    names = {c.name for c in B.bot.tree.get_commands()}
    assert {"mydata", "forgetme"} <= names
    assert C.PRIVACY_URL.endswith("/privacy.html") and C.TERMS_URL.endswith("/terms.html")


def test_faction_neutral_default():
    st = tmp_store()
    from forever_bot.store import GuildConfig
    assert GuildConfig(guild_id=1).faction == "neutral"
    cfg = Cfg(); cfg.faction = "neutral"
    p = R.build_daily(cfg, at_post_time(date(2026, 10, 27), cfg), SAMPLE, {}, slot=0)
    txt = json.dumps(p.embeds)
    assert "Horde name early" not in txt and "Horde main" not in txt
    cfg.faction = "horde"
    p = R.build_daily(cfg, at_post_time(date(2026, 10, 27), cfg), SAMPLE, {}, slot=0)
    assert "Horde" in json.dumps(p.embeds)
    assert R.fit_faction("We're on **PvP, Horde**.", "alliance") == "Pick the one your group agreed on."


def test_rotation_never_stuck():
    from datetime import timedelta
    for n in range(1, 30):
        seq = [f"tip {i}" for i in range(n)]
        got = {R.pick(seq, date(2026, 11, 5) + timedelta(days=i)) for i in range(n)}
        assert len(got) == n, n
    cfg = Cfg()
    keys = {R.build_daily(cfg, at_post_time(date(2026, 11, 5) + timedelta(days=i), cfg), SAMPLE, {}, slot=0).deep_key
            for i in range(7)}
    assert keys == set(C.POST_LAUNCH_TOPICS)
def test_rollcall_list():
    st = tmp_store()
    st.set_class(1, 10, "Mage"); st.set_class(1, 11, "Mage"); st.set_class(1, 12, "Rogue"); st.set_class(2, 13, "Priest")
    g = st.rollcall_list(1)
    assert sorted(g["Mage"]) == [10, 11] and g["Rogue"] == [12] and "Priest" not in g
    e = R.rollcall_embed(g, "Test")
    assert e["fields"][0]["name"] == "Mage · 2" and "<@10>" in e["fields"][0]["value"]
    assert "3" in e["description"] and "healer" in e["description"]
    assert "Nobody" in R.rollcall_embed({})["description"]
    big = {"Warlock": list(range(100))}
    assert len(R.rollcall_embed(big)["fields"][0]["value"]) <= 1024


def test_dungeons_addons_alliance():
    import json
    for lvl in R.LEVELS:
        for e in [R.dungeons_embed(lvl)] + [R.addons_embed(t, lvl) for t in R.ADDON_TOPICS]:
            assert len(json.dumps(e)) < 6000 and len(e.get("description", "")) <= 4096
            assert all(len(f["value"]) <= 1024 for f in e.get("fields", []))
    assert len(C.DUNGEONS) == 9
    from forever_bot import classes as K
    for cls in K.CLASSES:
        for f in ("horde", "alliance", "neutral"):
            e = R.classtips_embed(cls, f, "detailed")
            assert len(json.dumps(e)) < 6000
        al = R.classtips_embed(cls, "alliance", "standard")
        assert "Alliance races" in al["description"] and "Undead (new" not in al["description"]
        assert "Will of the Forsaken (Undead)" not in json.dumps(al)
    assert "Dwarf" in R.classtips_embed("Shaman", "alliance")["description"]
    from forever_bot import bot as B
    assert {"dungeons", "addons", "rollcall"} <= {c.name for c in B.bot.tree.get_commands()}


def test_hidden_channel_error_explains_fix():
    import types
    from forever_bot import bot as B
    sent = {}

    class Resp:
        def is_done(self):
            return False
        async def send_message(self, msg, ephemeral=False, **k):
            sent["msg"] = msg
    ch = types.SimpleNamespace(mention="<#5>", name="wowsherpa")
    tr = types.SimpleNamespace(_error_display_name="TextChannel")
    err = B.app_commands.TransformerError(ch, B.discord.AppCommandOptionType.channel, tr)
    inter = types.SimpleNamespace(command=None, guild_id=1, user=types.SimpleNamespace(id=2), response=Resp())
    orig = B.bot_in_guild
    B.bot_in_guild = lambda i: True
    try:
        asyncio.run(B.on_app_error(inter, err))
    finally:
        B.bot_in_guild = orig
    assert "can't see <#5>" in sent["msg"] and "View Channel" in sent["msg"]


def test_commands_only_install_gets_invite_link():
    import types
    from forever_bot import bot as B
    sent = {}

    class Resp:
        def is_done(self):
            return False
        async def send_message(self, msg, ephemeral=False, **k):
            sent["msg"] = msg
    inter = types.SimpleNamespace(command=None, guild_id=999999, user=types.SimpleNamespace(id=2), response=Resp())
    assert not B.bot_in_guild(inter)  # bot isn't connected in tests, so no guilds
    tr = types.SimpleNamespace(_error_display_name="TextChannel")
    err = B.app_commands.TransformerError(types.SimpleNamespace(mention="<#5>"), B.discord.AppCommandOptionType.channel, tr)
    asyncio.run(B.on_app_error(inter, err))
    assert "isn't in this server" in sent["msg"] and "scope=bot" in sent["msg"]


def test_status_watcher():
    import json
    from datetime import datetime, timezone, timedelta
    from forever_bot import status as S
    now = datetime(2026, 11, 4, 23, 30, tzinfo=timezone.utc)
    iso = lambda h: (now - timedelta(hours=h)).isoformat().replace("+00:00", "Z")
    posts = [
        {"id": "a", "text": "We're investigating login issues affecting WoW: Forever. Updates to follow.", "created": iso(0.2), "url": "u"},
        {"id": "b", "text": "The login issues in World of Warcraft: Forever have been resolved. Thanks for your patience!", "created": iso(0.1), "url": "u"},
        {"id": "c", "text": "Overwatch matchmaking is down, we're on it.", "created": iso(0.1), "url": "u"},
        {"id": "d", "text": "Battle.net login services are experiencing an outage.", "created": iso(0.3), "url": "u"},
        {"id": "e", "text": "Happy launch day, WoW Forever players! Have fun out there.", "created": iso(0.1), "url": "u"},
        {"id": "f", "text": "Scheduled maintenance for WoW: Forever begins at 7 AM PT.", "created": iso(10), "url": "u"},
        {"id": "g", "text": "Weekly maintenance for World of Warcraft: Forever starts at 7 AM PT.", "created": iso(1), "url": "u"},
    ]
    ups = S.pick_updates(posts, seen={"zzz"}, now=now)
    kinds = {u["id"]: u["kind"] for u in ups}
    assert kinds == {"a": "problem", "b": "resolved", "d": "problem", "g": "maintenance"}, kinds  # no Overwatch, no 'all good', nothing old
    assert [u["id"] for u in ups] == ["g", "d", "a", "b"]  # oldest first
    assert S.pick_updates(posts, seen={"a", "b", "d", "g"}, now=now) == []
    e = S.status_embed({**ups[0], "source": "Blizzard Support"}, "Blizzard Support")
    assert len(json.dumps(e)) < 6000 and "Maintenance" in e["title"]
    assert S.post_url("at://did:plc:x/app.bsky.feed.post/3abc", "support.blizzard.com").endswith("/post/3abc")

    # S.check() looks back from the real clock, so this fake post is dated from now (it was pinned to Nov 4
    # and started failing on Nov 5 once the post was older than the 2-hour first-run window)
    recent = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat().replace("+00:00", "Z")

    async def fake_get(session, url, params=None, want_json=False, **k):
        return {"feed": [{"post": {"uri": "at://x/app.bsky.feed.post/1", "author": {"handle": "support.blizzard.com"},
                                   "record": {"text": "WoW: Forever login issues, investigating.", "createdAt": recent}}},
                         {"reason": {"$type": "repost"}, "post": {"uri": "at://x/app.bsky.feed.post/2",
                                                                  "record": {"text": "repost"}}}]}
    orig = S.http_get
    S.http_get = fake_get
    try:
        got = asyncio.run(S.fetch_bluesky(None, "support.blizzard.com"))
        assert len(got) == 1 and got[0]["url"].endswith("/post/1")
        st = tmp_store()
        first = asyncio.run(S.check(None, st))  # first run still posts things from the last 2 hours
        assert len(first) == 1
        assert asyncio.run(S.check(None, st)) == []  # already seen
    finally:
        S.http_get = orig
    st = tmp_store()
    from forever_bot.store import GuildConfig
    st.upsert_guild(GuildConfig(guild_id=5, channel_id=6, status_alerts=False))
    assert st.get_guild(5).status_alerts is False


def test_no_repeats_inside_posts():
    from datetime import timedelta
    cfg = Cfg(); cfg.faction = "neutral"
    for i in range(40):
        d = date(2026, 10, 20) + timedelta(days=i)
        for slot in (0, 1):
            p = R.build_daily(cfg, at_post_time(d, cfg), {"news": [], "videos": [], "clips": [
                {"id": "twitch:1", "url": "a", "title": "a", "author": "Xaryu", "views": 50},
                {"id": "twitch:2", "url": "b", "title": "b", "author": "Xaryu", "views": 40}]}, {}, slot=slot)
            if p is None:
                continue
            assert (p.followup or "").count("Xaryu") <= 1
            desc = p.embeds[0]["description"]
            lines = desc.split("\n")
            pro = [l for l in lines if l.startswith("⚔️ **Pro tip:**")]
            vets = [l for l in lines if l.startswith("🧙")]
            if pro and vets:
                assert not R.too_similar(pro[0].split("**Pro tip:**", 1)[1], vets[0], 0.5), (d, pro[0])


# ------------------------------------------------------------------ 1.7: make setup obvious
def _fake_text_channel(cid=5, position=0):
    from forever_bot import bot as B
    ch = object.__new__(B.discord.TextChannel)
    ch.id, ch.position, ch.name = cid, position, f"c{cid}"
    import types
    ch.guild = types.SimpleNamespace(me=types.SimpleNamespace(display_name="Forever Sherpa"))
    return ch


def test_welcome_and_nudge_text():
    pre, post = datetime(2026, 10, 28, tzinfo=timezone.utc), datetime(2026, 11, 20, tzinfo=timezone.utc)
    for when in (pre, post):
        e = R.welcome_embed(when)
        assert "Post here" in e["description"] and "/setup" in e["description"] and len(e["description"]) < 4096
    assert "countdown to launch" in R.welcome_embed(pre)["description"]
    assert "countdown to launch" not in R.welcome_embed(post)["description"]
    assert "noon Central" in R.setup_nudge_text(True) and "Post here" in R.setup_nudge_text(True)
    assert "admin" in R.setup_nudge_text(False) and "Post here" not in R.setup_nudge_text(False)
    e = R.spellbook_embed("quest", {}, True, pre, unset=True)
    assert e["description"].startswith("⭐ **Start here:**")
    assert not R.spellbook_embed("quest", {}, True, pre)["description"].startswith("⭐")
    setup = next(sp for sp in R.SPELLBOOK["officer"]["spells"] if sp[0] == "setup")
    assert setup[1].startswith("[channel]")


def test_welcome_picks_a_channel_it_can_post_in():
    import types
    from forever_bot import bot as B
    a, b, sys_ch = _fake_text_channel(1, 0), _fake_text_channel(2, 1), _fake_text_channel(3, 2)
    g = types.SimpleNamespace(system_channel=sys_ch, text_channels=[b, a, sys_ch])
    assert B.welcome_channel(g, lambda ch: None) is sys_ch
    assert B.welcome_channel(g, lambda ch: "no" if ch is sys_ch else None) is a  # falls back to the top channel
    assert B.welcome_channel(g, lambda ch: "no") is None
    assert B.welcome_channel(types.SimpleNamespace(system_channel=None, text_channels=[b]), lambda ch: None) is b


def test_quick_setup_button():
    import types
    from forever_bot import bot as B
    B.bot.store = tmp_store()
    ch = _fake_text_channel(77)
    sent = []

    class Resp:
        async def send_message(self, msg, **k):
            sent.append(msg)

    def inter(admin=True, gid=42):
        return types.SimpleNamespace(
            guild_id=gid, channel_id=77, guild=types.SimpleNamespace(get_channel=lambda i: ch if i == 77 else None),
            user=types.SimpleNamespace(id=9, display_name="Al", guild_permissions=types.SimpleNamespace(manage_guild=admin)),
            response=Resp(), message=None)
    orig_in, orig_can = B.bot_in_guild, B.bot._can_post
    B.bot_in_guild = lambda i: True
    try:
        B.bot._can_post = lambda c: None
        asyncio.run(B.quick_setup(inter(admin=False)))
        assert "Manage Server" in sent[-1] and not B.is_set_up(42)
        asyncio.run(B.quick_setup(inter()))
        assert sent[-1].startswith("✅") and "<#77>" in sent[-1]
        cfg = B.bot.store.get_guild(42)
        assert cfg.channel_id == 77 and cfg.post_time == C.DEFAULT_POST_TIME and cfg.tz == C.DEFAULT_TZ
        asyncio.run(B.quick_setup(inter()))
        assert sent[-1].startswith("Already set up")
        B.bot._can_post = lambda c: "missing permissions: Send Messages"
        asyncio.run(B.quick_setup(inter(gid=43)))
        assert "can't post" in sent[-1] and not B.is_set_up(43)
    finally:
        B.bot_in_guild, B.bot._can_post = orig_in, orig_can


def test_setup_nudge_once_and_only_when_unset():
    import types
    from forever_bot import bot as B
    B.bot.store = tmp_store()
    B.bot._nudged.clear()
    out = []

    class Resp:
        def is_done(self):
            return True

    class Follow:
        async def send(self, text, **k):
            out.append((text, k))

    def inter(uid=1, admin=True, gid=50):
        return types.SimpleNamespace(guild_id=gid, response=Resp(), followup=Follow(),
                                     user=types.SimpleNamespace(id=uid, guild_permissions=types.SimpleNamespace(manage_guild=admin)))
    cmd = types.SimpleNamespace(qualified_name="countdown", default_permissions=None)
    admin_cmd = types.SimpleNamespace(qualified_name="frequency", default_permissions=B.discord.Permissions(manage_guild=True))
    orig = B.bot_in_guild
    B.bot_in_guild = lambda i: True
    try:
        asyncio.run(B.bot.maybe_nudge(inter(), cmd))
        assert len(out) == 1 and "Post here" in out[0][0] and "view" in out[0][1] and out[0][1]["ephemeral"]
        asyncio.run(B.bot.maybe_nudge(inter(), cmd))  # same person, same server: not again for 6 hours
        assert len(out) == 1
        asyncio.run(B.bot.maybe_nudge(inter(uid=2, admin=False), cmd))
        assert len(out) == 2 and "admin" in out[1][0] and "view" not in out[1][1]
        asyncio.run(B.bot.maybe_nudge(inter(uid=3), admin_cmd))  # admin commands explain themselves
        asyncio.run(B.bot.maybe_nudge(inter(uid=3), types.SimpleNamespace(qualified_name="help", default_permissions=None)))
        assert len(out) == 2
        from forever_bot.store import GuildConfig
        B.bot.store.upsert_guild(GuildConfig(guild_id=60, channel_id=5))
        asyncio.run(B.bot.maybe_nudge(inter(uid=4, gid=60), cmd))  # set up: silent
        assert len(out) == 2
        B.bot_in_guild = lambda i: False  # commands-only install: admins get the invite link
        asyncio.run(B.bot.maybe_nudge(inter(uid=5, gid=70), cmd))
        assert "scope=bot" in out[-1][0]
    finally:
        B.bot_in_guild = orig


def test_mid_day_setup_skips_backfill_and_sends_short_first_post():
    """1.7.1: Oct 28 a server set up at 12:36 PM got the noon full post 37 min late (another 146 min late),
    and one left 11 minutes later. Mid-day setup now skips passed slots and sends a short first look."""
    from forever_bot import bot as B
    from forever_bot.store import GuildConfig
    B.bot.store = tmp_store()
    ch = _fake_text_channel(77)
    sent, ticked = [], []

    async def fake_send(channel, post, ping_role_id=None):
        sent.append(post)
        return 1, None

    async def fake_post_daily(cfg, now, force=False, slot=0):
        ticked.append(slot)
        return "Posted."
    B.bot.get_channel, B.bot._can_post = (lambda i: ch if i == 77 else None), (lambda c: None)
    B.bot.send_post, B.bot.post_daily = fake_send, fake_post_daily
    try:
        cst = datetime(2026, 10, 28, 18, 36, tzinfo=timezone.utc)  # 1:36 PM Central, noon post already due
        cfg = GuildConfig(guild_id=42, channel_id=77, enabled=True)
        B.bot.store.upsert_guild(cfg)
        assert B.bot.skip_passed_slots(cfg, cst) == [0]
        asyncio.run(B.bot._tick_guild(cfg, cst))
        assert ticked == []  # no stale backfill
        key = asyncio.run(B.bot.send_first_post(cfg, cst))
        assert key == "launch:2026-10-28:first" and len(sent) == 1
        post = sent[0]
        desc = post.embeds[0]["description"]
        assert len(post.embeds) == 1 and post.followup is None and not post.used_ids  # no news, no clips
        assert "First look" in desc and "<t:" in desc and len(desc) < 1500 and not post.rollcall
        assert asyncio.run(B.bot.send_first_post(cfg, cst)) is None and len(sent) == 1  # once
        # tomorrow's noon post still goes out normally
        asyncio.run(B.bot._tick_guild(cfg, datetime(2026, 10, 29, 17, 1, tzinfo=timezone.utc)))
        assert ticked == [0]

        # set up before noon: nothing skipped, the regular post covers today
        early = GuildConfig(guild_id=43, channel_id=77, enabled=True)
        B.bot.store.upsert_guild(early)
        assert B.bot.skip_passed_slots(early, datetime(2026, 10, 28, 15, 0, tzinfo=timezone.utc)) == []

        # set up at 6:30 PM with a 7 PM check-in: skip noon, no first look (the check-in is minutes away)
        two = GuildConfig(guild_id=44, channel_id=77, enabled=True, post_time="12pm,7pm")
        B.bot.store.upsert_guild(two)
        evening = datetime(2026, 10, 28, 23, 30, tzinfo=timezone.utc)
        assert B.bot.skip_passed_slots(two, evening) == [0]
        assert asyncio.run(B.bot.send_first_post(two, evening)) is None and len(sent) == 1

        # the 📍 Post here button wires it up end to end
        import types
        replies = []

        class Resp:
            async def send_message(self, msg, **k):
                replies.append(msg)
        inter = types.SimpleNamespace(
            guild_id=45, channel_id=77, guild=types.SimpleNamespace(get_channel=lambda i: ch if i == 77 else None),
            user=types.SimpleNamespace(id=9, display_name="Al", guild_permissions=types.SimpleNamespace(manage_guild=True)),
            response=Resp(), message=None)
        orig_now, orig_in = B.now_utc, B.bot_in_guild
        B.now_utc, B.bot_in_guild = (lambda: cst), (lambda i: True)
        try:
            asyncio.run(B.quick_setup(inter))
        finally:
            B.now_utc, B.bot_in_guild = orig_now, orig_in
        assert replies[-1].startswith("✅") and len(sent) == 2 and sent[-1].key.endswith(":first")
        assert B.bot.store.was_posted(45, "daily", "launch:2026-10-28:0")
    finally:
        for a in ("get_channel", "_can_post", "send_post", "post_daily"):
            B.bot.__dict__.pop(a, None)



# ------------------------------------------------------------- 1.12
def test_after_raids_keeps_posting_with_day_number():
    cfg = Cfg()
    assert R.phase(C.DEFAULT_TZ, datetime(2026, 12, 10, 18, 0, tzinfo=timezone.utc)) == ("live", 37)
    assert R.phase(C.DEFAULT_TZ, datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc))[0] == "launch"
    post = R.build_daily(cfg, at_post_time(date(2027, 6, 1), cfg), SAMPLE, {})
    assert post and post.embeds[0]["title"].startswith("Day ") and post.key.startswith("live:")
    chk = R.build_checkin(cfg, at_post_time(date(2027, 6, 1), cfg), SAMPLE, 1)
    assert chk and chk.embeds[0]["title"].startswith("Day ")
    seen = {R.build_daily(cfg, at_post_time(date(2026, 12, 10) + timedelta(days=i), cfg), SAMPLE, {}).deep_key
            for i in range(30)}
    assert "raids" in seen  # raids join the rotation


def test_raid_day_is_about_raids_and_names_onyxia():
    cfg = Cfg()
    post = R.build_daily(cfg, at_post_time(date(2026, 12, 9), cfg), SAMPLE, {})
    desc = post.embeds[0]["description"]
    assert post.deep_key == "raids" and "Raid night" in desc and "Onyxia" in desc
    before = R.build_daily(cfg, at_post_time(date(2026, 11, 20), cfg), SAMPLE, {})
    assert "Onyxia's Lair (40)" in before.embeds[0]["description"]


def test_next_up_drops_when_stale():
    assert R.live_next_up(date(2026, 12, 10))
    assert R.live_next_up(date(2030, 1, 1)) is None


def test_launch_posts_without_pings():
    assert C.LAUNCH_POST_MINUTES == (60, 0)
    assert "For the Alliance." in R.milestone_text(0, "alliance")
    assert "Horde" not in R.milestone_text(0, "neutral") and "Horde" not in R.milestone_text(60, "neutral")
    assert "/draggedalong" in R.milestone_text(0, "horde")


def test_blocked_notice_text():
    t = R.blocked_notice_text(123, "missing permissions: Send Messages", "**Fix:** do the thing")
    assert "<#123>" in t and "Send Messages" in t and "/setup" in t and "@" not in t.replace("<#123>", "")


def test_blocked_channel_tells_admins_once_on_real_bot():
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "x.db")
    from types import SimpleNamespace
    from forever_bot.bot import ForeverBot
    from forever_bot.store import GuildConfig
    b = ForeverBot()
    b.store = tmp_store()
    b.snap = dict(SAMPLE, fetched_at=time.time())
    sent = []

    class Ch:
        def __init__(self, cid, pos):
            self.id, self.position = cid, pos
            self.guild = guild

        async def send(self, text=None, **kw):
            sent.append((self.id, text))

    guild = SimpleNamespace(id=9, me=SimpleNamespace(display_name="Forever Sherpa"))
    blocked, system = Ch(100, 0), Ch(5, 1)
    guild.system_channel, guild.text_channels = system, [blocked, system]
    b.get_channel = lambda cid: {100: blocked, 5: system}.get(cid)
    b.get_guild = lambda gid: guild if gid == 9 else None
    b._can_post = lambda ch: "missing permissions: Send Messages" if ch is blocked else None
    cfg = GuildConfig(guild_id=9, channel_id=100, post_time="12:00", tz="America/Chicago")
    b.store.upsert_guild(cfg)
    now = datetime(2026, 11, 20, 18, 1, tzinfo=timezone.utc)
    for _ in range(3):  # the scheduler retries every minute
        asyncio.run(b.post_daily(cfg, now))
    assert len(sent) == 1 and sent[0][0] == 5 and "<#100>" in sent[0][1]
    assert b.store.was_posted(9, "blocked", "raids:2026-11-20:0")


def test_launch_loop_posts_t60_and_live_without_pings():
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "l.db")
    from types import SimpleNamespace
    import forever_bot.bot as B
    from forever_bot.store import GuildConfig
    b = B.ForeverBot()
    b.store = tmp_store()
    sent = []

    class Ch:
        id = 100
        guild = SimpleNamespace(name="Test")

        async def send(self, text=None, **kw):
            sent.append((text, kw.get("allowed_mentions")))

    b.get_channel = lambda cid: Ch() if cid == 100 else None
    b._can_post = lambda ch: None
    b.store.upsert_guild(GuildConfig(guild_id=9, channel_id=100, ping_role_id=55, faction="horde"))
    real_now, real_sleep = B.now_utc, B.asyncio.sleep

    async def no_sleep(_):
        return None
    B.asyncio.sleep = no_sleep
    try:
        for at in (C.LAUNCH - timedelta(minutes=60), C.LAUNCH - timedelta(minutes=10), C.LAUNCH,
                   C.LAUNCH + timedelta(minutes=1)):
            B.now_utc = lambda at=at: at
            asyncio.run(b.launch_loop.coro(b))
    finally:
        B.now_utc, B.asyncio.sleep = real_now, real_sleep
    assert len(sent) == 2, sent  # T-60 and live, once each; T-10 stays off
    assert "One hour" in sent[0][0] and "is live" in sent[1][0]
    assert all("<@&" not in t for t, _ in sent)


def test_setup_reminder_once_for_unconfigured_servers():
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "r.db")
    from types import SimpleNamespace
    import forever_bot.bot as B
    from forever_bot.store import GuildConfig
    b = B.ForeverBot()
    b.store = tmp_store()
    sent = []
    now = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)

    def guild(gid, hours_ago):
        ch = SimpleNamespace(id=gid * 10, position=0)

        async def send(**kw):
            sent.append((gid, kw["embed"].title, kw.get("view") is not None))
        ch.send = send
        return SimpleNamespace(id=gid, name=f"g{gid}", system_channel=ch, text_channels=[ch],
                               me=SimpleNamespace(joined_at=now - timedelta(hours=hours_ago)))

    gs = [guild(1, 5), guild(2, 1), guild(3, 5), guild(4, 24 * 30)]  # due, too new, set up, too old
    b.store.upsert_guild(GuildConfig(guild_id=3, channel_id=30))
    b._can_post = lambda ch: None
    type(b).guilds = property(lambda self: gs)
    try:
        for _ in range(3):  # heartbeat runs every 30 min; only one reminder ever
            asyncio.run(b.send_setup_reminders(now))
    finally:
        del type(b).guilds
    assert sent == [(1, "📍 Forever Sherpa isn't posting here yet", True)], sent
    e = R.setup_reminder_embed(now)
    assert "launches" in e["description"] and "@" not in e["description"]
    assert "is live" in R.setup_reminder_embed(C.LAUNCH + timedelta(hours=1))["description"]

if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} passed")


# ------------------------------------------------------------------ 1.8: /clips
def test_clips_can_be_turned_off():
    snap = {"news": [], "videos": [], "clips": [
        {"id": "twitch:1", "url": "https://clips.example/a", "title": "big pull", "author": "Xaryu", "views": 50}]}
    d = date(2026, 10, 30)
    for slot in (0, 1):
        on, off = Cfg(), Cfg()
        off.clips = False
        p_on = R.build_daily(on, at_post_time(d, on), snap, {}, slot=slot)
        p_off = R.build_daily(off, at_post_time(d, off), snap, {}, slot=slot)
        assert "big pull" in (p_on.followup or "") and "twitch:1" in p_on.used_ids
        assert "big pull" not in (p_off.followup or "") and "twitch:1" not in p_off.used_ids
    st = tmp_store()
    from forever_bot.store import GuildConfig
    st.upsert_guild(GuildConfig(guild_id=7, channel_id=8))
    assert st.get_guild(7).clips is True  # on by default
    st.upsert_guild(GuildConfig(guild_id=7, channel_id=8, clips=False))
    assert st.get_guild(7).clips is False and st.all_guilds()[0].clips is False


def test_welcome_calls_out_key_admin_commands():
    desc = R.welcome_embed(datetime(2026, 10, 30, tzinfo=timezone.utc))["description"]
    for cmd in ("/preview", "/verbosity", "/clips", "/frequency", "/hold", "/statusalerts"):
        assert cmd in desc, cmd


# ------------------------------------------------------------------ 1.8.1: forgiving inputs
def test_timezones_people_actually_type():
    from forever_bot import inputs as I
    cases = {"central": "America/Chicago", "Central": "America/Chicago", "CST": "America/Chicago",
             "america/chicago": "America/Chicago", "America/Chicago": "America/Chicago",
             "Central Standard Time": "America/Chicago", "eastern": "America/New_York", "New York": "America/New_York",
             "pacific time": "America/Los_Angeles", "PST": "America/Los_Angeles", "Mountain": "America/Denver",
             "Arizona": "America/Phoenix", "UK": "Europe/London", "london": "Europe/London", "CET": "Europe/Paris",
             "Helsinki": "Europe/Helsinki", "finland": "Europe/Helsinki", "europe/helsinki": "Europe/Helsinki",
             "Sydney": "Australia/Sydney", "utc": "UTC", "UTC-6": "Etc/GMT+6", "GMT+2": "Etc/GMT-2"}
    for typed, want in cases.items():
        assert I.resolve_tz(typed) == want, (typed, I.resolve_tz(typed))
    for bad in ("", "asdf", "centrl", "UTC+99"):
        assert I.resolve_tz(bad) is None, bad
    assert I.suggest_tz("centrl")[0] == "America/Chicago"
    assert "America/Chicago" in I.bad_tz_text("centrl") and "`centrl`" in I.bad_tz_text("centrl")
    assert I.tz_choices("")[0][1] == "America/Chicago"
    assert any(v == "Europe/Helsinki" for _, v in I.tz_choices("hel"))
    assert I.tz_choices("central")[0][1] == "America/Chicago"
    assert all(len(n) <= 100 and len(v) <= 100 for n, v in I.tz_choices("a")) and len(I.tz_choices("a")) <= 25


def test_times_people_actually_type():
    os.environ.setdefault("DB_PATH", os.path.join(tempfile.mkdtemp(), "b.db"))
    from forever_bot import bot as B
    ok = {"12pm": (12, 0), "12 PM": (12, 0), "7:30pm": (19, 30), "7p": (19, 0), "7 p.m.": (19, 0),
          "19:30": (19, 30), "19.30": (19, 30), "1930": (19, 30), "730pm": (19, 30), "noon": (12, 0),
          "Midnight": (0, 0), "12am": (0, 0), "19h30": (19, 30)}
    for typed, want in ok.items():
        assert B.parse_hhmm(typed) == want, (typed, B.parse_hhmm(typed))
    for bad in ("25pm", "25:00", "abc", "0am", ""):  # 1.11.1: "13pm" now reads as 13:00
        assert B.parse_hhmm(bad) is None, bad
    assert B.parse_times("noon and 7p") == [(12, 0), (19, 0)]
    assert B.parse_times("12 pm, 7 pm") == [(12, 0), (19, 0)]
    assert "`lunch`" in B.check_times(None, "lunch")


def test_no_dead_end_setup_replies():
    src = open(os.path.join(os.path.dirname(__file__), "..", "forever_bot", "bot.py")).read()
    assert 'Run `/setup` first."' not in src  # every one offers the Post here button now (need_setup)


def test_tips_are_consistent():
    seen = set()
    for topic, tips in C.TIPS.items():
        assert len(tips) >= 3, topic  # Brief shows the first 3
        for t in tips:
            assert t.startswith("**") and " → " in t, (topic, t)  # "**do this** → why"
            assert t not in seen, t
            seen.add(t)
        assert R.tips_embed(topic)["title"] in R.TIP_TITLES.values()
    for a in (t for v in C.TIPS.values() for t in v):  # no near-duplicates across topics either
        for b in seen:
            assert a == b or not R.too_similar(a, b, 0.8), (a, b)


# ------------------------------------------------------------------ 1.9: what's new
def test_release_notes_and_update_line():
    from forever_bot import __version__
    assert C.RELEASE_NOTES[0]["version"] == __version__, "add player-facing notes for this release to RELEASE_NOTES"
    vs = [C._vkey(r["version"]) for r in C.RELEASE_NOTES]
    assert vs == sorted(vs, reverse=True)
    latest = C.RELEASE_NOTES[0]["version"]
    # servers that never heard of anything get the newest release with a line; up-to-date ones get nothing
    got = C.latest_line_since(None)
    newest_line = next(r for r in C.RELEASE_NOTES if r["line"])  # the line comes from the newest release that has one
    assert got and got[0] == latest and got[1] == newest_line["line"]
    assert C.latest_line_since("1.8.0")[1] == got[1]
    older = next(r["version"] for r in C.RELEASE_NOTES if C._vkey(r["version"]) < C._vkey(newest_line["version"]))
    assert C.latest_line_since(latest) is None and C.latest_line_since(older)[1] == got[1]
    assert C.latest_line_since(newest_line["version"]) is None  # heard the newest line: nothing more to say
    for r in C.RELEASE_NOTES:
        assert r["notes"] and (r["line"] is None or len(R.update_line(r["line"])) < 250)
    cfg = Cfg()
    for slot in (0, 1):
        p = R.build_daily(cfg, at_post_time(date(2026, 10, 30), cfg), SAMPLE, {}, slot=slot)
        before = p.embeds[0]["description"].split("\n")
        R.add_update_line(p, got[1])
        lines = p.embeds[0]["description"].split("\n")
        assert lines[-1] == before[-1] and lines[-3].startswith("🆕") and len(lines) == len(before) + 2
    e = R.whatsnew_embed()
    public = C.public_notes()
    assert e["url"] == C.WHATSNEW_URL and len(e["description"]) < 4000 and public[0]["version"] in e["description"]
    for r in C.RELEASE_NOTES:
        if r.get("internal"):
            assert r not in public and f"v{r['version']} " not in e["description"] and r["line"] is None


def test_store_remembers_announced_and_updates():
    from forever_bot.store import GuildConfig
    st = tmp_store()
    st.upsert_guild(GuildConfig(guild_id=9, channel_id=1))
    g = st.get_guild(9)
    assert g.updates is True and g.announced is None
    st.set_announced(9, "1.9.0")
    st.upsert_guild(GuildConfig(guild_id=9, channel_id=1, updates=False, announced="1.9.0"))
    g = st.get_guild(9)
    assert g.updates is False and g.announced == "1.9.0" and st.all_guilds()[0].announced == "1.9.0"


def test_whatsnew_page_builds():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools"))
    import build_whatsnew as W
    html_ = W.page()
    assert html_.startswith("<!doctype html>") and "<code>/clips</code>" in html_ and "`" not in html_
    assert all(f'id="v{r["version"]}"' in html_ for r in C.public_notes())
    assert not any(f'id="v{r["version"]}"' in html_ for r in C.RELEASE_NOTES if r.get("internal"))


# ------------------------------------------------------------------ 1.11: datamined content, more tips and facts
def test_datamined_marker_and_label():
    d = C.dm("**Do it** → why")
    assert isinstance(d, str) and C.is_dm(d) and not C.is_dm("plain")
    assert C.show(d).endswith(C.DM_LABEL) and C.show("plain") == "plain"
    assert C.is_dm(("vet", d)) and not C.is_dm(("vet", "x"))
    with R.datamined(True):
        assert any(t.endswith(C.DM_LABEL) for t in R.V(C.TIPS["gold"]))
    with R.datamined(False):
        assert not any(C.DM_LABEL in t for t in R.V(C.TIPS["gold"]))
        assert R.V([d]) == [str(d)]  # never leave a pool empty


def test_content_volume():
    assert all(len(v) >= 15 for v in C.TIPS.values()), {k: len(v) for k, v in C.TIPS.items()}
    assert len(C.DID_YOU_KNOW) >= 115
    facts = [t for _, t in C.DID_YOU_KNOW]
    assert len(set(facts)) == len(facts)
    assert sum(C.is_dm(t) for t in facts) < len(facts) / 4  # mostly Blizzard-confirmed
    from forever_bot import plusone as P
    assert len(P.PLUS_FACTS) >= 25 and P.fact_embed(len(P.PLUS_FACTS) + 1)["description"] == P.PLUS_FACTS[1]


def test_datamined_off_hides_everything_on_screen():
    for topic in C.TIPS:
        for lvl in ("brief", "standard", "detailed"):
            with R.datamined(False):
                e = R.tips_embed(topic, lvl)
            assert C.DM_LABEL not in e["description"] and len(e["description"]) <= 4000
            with R.datamined(True):
                assert len(R.tips_embed(topic, lvl)["description"]) <= 4000
    for on in (False, True):
        cfg = Cfg()
        cfg.datamined = on
        seen = False
        for d in range(60):  # through launch and well into the raid countdown
            day = date(2026, 10, 31) + timedelta(days=d)
            for slot in (0, 1, 2):
                p = R.build_daily(cfg, at_post_time(day, cfg), SAMPLE, {}, slot=slot)
                text = "\n".join(e.get("description", "") for e in (p.embeds if p else []))
                seen |= C.DM_LABEL in text
                if not on:
                    assert C.DM_LABEL not in text, (day, slot)
        assert seen == on


def test_store_remembers_datamined():
    s = tmp_store()
    from forever_bot.store import GuildConfig
    cfg = GuildConfig(guild_id=5, channel_id=1)
    s.upsert_guild(cfg)
    assert s.get_guild(5).datamined is True
    cfg.datamined = False
    s.upsert_guild(cfg)
    assert s.get_guild(5).datamined is False and s.all_guilds()[0].datamined is False


def test_content_corrections():
    assert not any("Merchant Coast in Dustwallow" in t for t in C.TIPS["pvp"])
    assert any("Merchant Coast in the Barrens" in t for t in C.TIPS["pvp"])
    from forever_bot import classes as K
    blob = json.dumps(K.__dict__.get("CLASS_INFO", {}), default=str) + open(K.__file__).read()
    assert "Elemental Mastery is gone" not in blob
    # 1.12.1: Blizzard's Nov 2 launch notes
    from forever_bot import guides as G
    text = blob + open(G.__file__).read() + open(C.__file__).read()
    # Lava Burst may be named as cut ("Lava Burst was cut…"), never listed as an ability, keybind or rotation step
    for gone in ("200% more", "Totemic Projection at", "\"Lava Burst\"", "\"Lava Burst (", "Lava Burst on cooldown",
                 "signatures: Lava Burst", "separate cooldowns", "10% health", "Binding Heal (Holy",
                 "guarantees a Soul Shard", "every 8 seconds"):
        assert gone not in text, gone
    assert "Totemic Call" in text and "Lightning Mastery" in text and "300% more" in text


# ------------------------------------------------------------------ 1.11.1: setup fixes from live logs
def test_24h_pm_times():
    from forever_bot.bot import parse_hhmm, parse_times, check_times
    assert parse_hhmm("16pm") == (16, 0) and parse_hhmm("22pm") == (22, 0) and parse_hhmm("13:30pm") == (13, 30)
    t = parse_times("16pm, 22pm")
    assert t == [(16, 0), (22, 0)] and check_times(t) is None
    assert parse_hhmm("7pm") == (19, 0) and parse_hhmm("12pm") == (12, 0) and parse_hhmm("12am") == (0, 0)
    assert parse_hhmm("25pm") is None and parse_hhmm("0am") is None and parse_hhmm("13am") is None


def test_postnow_after_skip_or_channel_move():
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "p.db")
    import forever_bot.bot as B
    from forever_bot.store import GuildConfig
    B.bot.store = tmp_store()
    st = B.bot.store
    cfg = GuildConfig(guild_id=9, channel_id=100, post_time="12:00", tz="America/New_York")
    st.upsert_guild(cfg)
    key = "launch:2026-10-31:0"
    now = datetime(2026, 10, 31, 22, 0, tzinfo=timezone.utc)  # 6 PM Eastern, after the noon slot
    assert B.bot.skip_passed_slots(cfg, now) == [0]
    assert st.was_posted(9, "daily", key) and B.full_post_needed(cfg, key)  # skipped: nothing actually went out
    st.unmark_posted(9, "skipped", key)
    st.mark_posted(9, "dailychan", f"{key}@100")
    assert not B.full_post_needed(cfg, key)  # really posted here
    cfg.channel_id = 200
    assert B.full_post_needed(cfg, key)  # moved channels since
    st.mark_posted(9, "dailychan", f"{key}@200")
    assert not B.full_post_needed(cfg, key) and st.posted_channels(9, key) == {100, 200}
    other = GuildConfig(guild_id=10, channel_id=1)
    st.mark_posted(10, "daily", key)  # posted before 1.11.1: no channel record, so no repeat
    assert not B.full_post_needed(other, key)


# ------------------------------------------------------------------ 1.12.2: hardening from live logs (Oct 30 – Nov 3)
import contextlib  # noqa: E402
import logging  # noqa: E402
import types as _t  # noqa: E402


@contextlib.contextmanager
def _events(*names):
    """Collect (event, level, fields) from our structured loggers."""
    got = []

    class H(logging.Handler):
        def emit(self, record):
            f = getattr(record, "fields", {}) or {}
            got.append((f.get("event", record.getMessage()), record.levelno, f))
    h = H(level=logging.DEBUG)
    loggers = [logging.getLogger(n) for n in (names or ("forever.bot", "forever.sched", "forever.cmd"))]
    old = [(lg, lg.level) for lg in loggers]
    for lg in loggers:
        lg.addHandler(h)
        lg.setLevel(logging.DEBUG)
    try:
        yield got
    finally:
        for lg, lvl in old:
            lg.removeHandler(h)
            lg.setLevel(lvl)


def _http(status, code, cls=None):
    from forever_bot import bot as B
    cls = cls or (B.discord.NotFound if status == 404 else B.discord.HTTPException)
    return cls(_t.SimpleNamespace(status=status, reason="x"), {"code": code, "message": "x"})


class _Resp:
    def __init__(self, ack_error=None):
        self.ack_error, self.done, self.calls = ack_error, False, []

    def is_done(self):
        return self.done

    async def _ack(self, name, *a, **k):
        self.calls.append(name)
        if self.ack_error:
            raise self.ack_error
        self.done = True

    async def edit_message(self, **k):
        await self._ack("edit_message", **k)

    async def defer(self, **k):
        await self._ack("defer", **k)

    async def send_message(self, msg=None, **k):
        if self.done:
            raise RuntimeError("second response")
        await self._ack(f"send_message:{msg}", **k)


def _inter(resp, on_board=True, gid=7, uid=70):
    sent = []

    class Followup:
        async def send(self, msg=None, **k):
            sent.append((msg, k))
    msg = _t.SimpleNamespace(author=_t.SimpleNamespace(id=1), components=[]) if on_board else None
    i = _t.SimpleNamespace(guild_id=gid, user=_t.SimpleNamespace(id=uid), message=msg, response=resp, followup=Followup())
    return i, sent


def _rollcall_cb(cls="Warrior"):
    from forever_bot import bot as B
    B.bot.store = tmp_store()
    fake_bot = _t.SimpleNamespace(store=B.bot.store, user=_t.SimpleNamespace(id=1))

    async def make():
        return B.RollcallView(fake_bot)._make_cb(cls)
    return B, asyncio.run(make())


def test_interaction_expired_detection():
    from forever_bot import bot as B
    from discord import app_commands
    assert B.interaction_expired(_http(404, 10062)) and B.interaction_expired(_http(400, 40060))
    wrapped = app_commands.CommandInvokeError(_t.SimpleNamespace(qualified_name="x", name="x"), _http(404, 10062))
    assert B.interaction_expired(wrapped)
    assert not B.interaction_expired(_http(404, 10008)) and not B.interaction_expired(RuntimeError("boom"))


def test_rollcall_late_click_saves_and_never_double_replies():
    """Nov 2, Runedone: a Warrior click reached Discord after the 3-second window (10062). The edit failed,
    then the 'Saved as' fallback failed the same way and dumped a traceback."""
    B, cb = _rollcall_cb("Warrior")
    resp = _Resp(ack_error=_http(404, 10062))
    inter, sent = _inter(resp)
    with _events() as evs:
        asyncio.run(cb(inter))  # must not raise
    assert {k: v for k, v in B.bot.store.class_counts(7).items() if v} == {"Warrior": 1}  # the pick is saved anyway
    assert resp.calls == ["edit_message"] and sent == []  # no second reply into a dead interaction
    late = [e for e in evs if e[0] == "rollcall_late"]
    assert len(late) == 1 and late[0][1] == logging.WARNING and late[0][2]["saved"] is True
    assert not any(lvl >= logging.ERROR for _, lvl, _ in evs)


def test_rollcall_happy_paths_ack_first():
    B, cb = _rollcall_cb("Mage")
    resp = _Resp()
    inter, sent = _inter(resp)
    with _events() as evs:
        asyncio.run(cb(inter))
    assert resp.calls == ["edit_message"] and len(sent) == 1 and sent[0][0].startswith("Locked in: **Mage**")
    assert any(e[0] == "rollcall" for e in evs)
    # pressed somewhere that isn't the bot's own board: defer, then one private followup
    resp2 = _Resp()
    inter2, sent2 = _inter(resp2, on_board=False, uid=71)
    asyncio.run(cb(inter2))
    assert resp2.calls == ["defer"] and len(sent2) == 1 and {k: v for k, v in B.bot.store.class_counts(7).items() if v} == {"Mage": 2}


def test_rollcall_other_failures_still_answer_once():
    B, cb = _rollcall_cb("Rogue")
    resp = _Resp(ack_error=_http(500, 0))  # a real Discord error, interaction still open
    inter, sent = _inter(resp)
    asyncio.run(cb(inter))
    resp.ack_error = None
    assert resp.calls[0] == "edit_message" and {k: v for k, v in B.bot.store.class_counts(7).items() if v} == {"Rogue": 1}
    # storage blew up: apologise privately, don't throw
    B2, cb2 = _rollcall_cb("Rogue")

    def boom(*a):
        raise RuntimeError("db locked")
    B2.bot.store.set_class = boom
    resp2 = _Resp()
    inter2, _ = _inter(resp2)
    with _events() as evs:
        asyncio.run(cb2(inter2))
    assert resp2.calls and resp2.calls[0].startswith("send_message:Couldn't save")
    assert any(e[0] == "rollcall_failed" and e[2].get("stage") == "save" for e in evs)


def test_rollcall_tips_failure_keeps_the_pick():
    B, cb = _rollcall_cb("Druid")
    orig = B.R.classtips_embed
    B.R.classtips_embed = lambda *a, **k: (_ for _ in ()).throw(KeyError("x"))
    try:
        resp = _Resp()
        inter, sent = _inter(resp)
        asyncio.run(cb(inter))
    finally:
        B.R.classtips_embed = orig
    assert resp.calls == ["edit_message"] and sent and sent[0][0].startswith("Locked in: **Druid**")
    assert "embed" not in sent[0][1]


def test_component_errors_are_one_line_and_reply_once():
    from forever_bot import bot as B
    item = _t.SimpleNamespace(custom_id="rc:Warrior")
    for err, replies, level in ((_http(404, 10062), 0, logging.WARNING), (RuntimeError("bug"), 1, logging.ERROR)):
        resp = _Resp()
        inter, _ = _inter(resp)

        async def go():
            view = B.discord.ui.View()
            await view.on_error(inter, err, item)
        with _events() as evs:
            asyncio.run(go())
        assert len(resp.calls) == replies
        assert [e for e in evs if e[0] in ("component_late", "component_error")][0][1] == level


def test_app_command_late_is_quiet():
    from forever_bot import bot as B
    from discord import app_commands
    resp = _Resp()
    inter, sent = _inter(resp)
    inter.command = _t.SimpleNamespace(qualified_name="setup", name="setup")
    err = app_commands.CommandInvokeError(inter.command, _http(404, 10062))
    with _events() as evs:
        asyncio.run(B.on_app_error(inter, err))
    assert resp.calls == [] and sent == [] and evs[0][0] == "command_late" and evs[0][1] == logging.WARNING


def test_mention_text_is_not_an_error():
    """Nov 1: 'Ignoring exception in command None' at ERROR, from someone @mentioning the bot with words."""
    from forever_bot import bot as B
    from discord.ext import commands
    ctx = _t.SimpleNamespace(guild=_t.SimpleNamespace(id=3))
    with _events() as evs:
        asyncio.run(B.bot.on_command_error(ctx, commands.CommandNotFound('Command "hey" is not found')))
    assert evs and all(lvl < logging.WARNING for _, lvl, _ in evs)


def test_expired_interaction_log_filter():
    """Oct 30: 'Ignoring exception in autocomplete for setup' (ERROR + traceback) was Discord's 10062."""
    from forever_bot.logsetup import ExpiredInteractionFilter
    import sys
    try:
        raise _http(404, 10062)
    except Exception:
        rec = logging.LogRecord("discord.app_commands.tree", logging.ERROR, __file__, 1,
                                "Ignoring exception in autocomplete for %r", ("setup",), sys.exc_info())
    assert ExpiredInteractionFilter().filter(rec)
    assert rec.levelno == logging.WARNING and rec.exc_info is None and "code 10062" in rec.getMessage()
    try:
        raise ValueError("real bug")
    except Exception:
        real = logging.LogRecord("discord.app_commands.tree", logging.ERROR, __file__, 1, "x", None, sys.exc_info())
    ExpiredInteractionFilter().filter(real)
    assert real.levelno == logging.ERROR and real.exc_info  # real bugs keep their traceback


def test_autocomplete_never_throws():
    from forever_bot import bot as B
    weird = ["", "🔥" * 50, "x" * 300, "America/", "\x00", "12pm", "  "]
    for typed in weird:
        for ac in (B._tz_ac, B._glossary_ac):
            out = asyncio.run(ac(None, typed))
            assert len(out) <= 25 and all(len(c.name) <= 100 and len(str(c.value)) <= 100 for c in out)
    orig = B.P.glossary_choices
    B.P.glossary_choices = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    try:
        assert asyncio.run(B._glossary_ac(None, "bis")) == []
    finally:
        B.P.glossary_choices = orig


def _sched_bot():
    from forever_bot import bot as B
    B.bot.store = tmp_store()
    ticked, posted = [], []

    async def fake_post_daily(cfg, now, force=False, slot=0):
        posted.append((cfg.guild_id, slot))
        return "Posted."
    B.bot.post_daily = fake_post_daily
    return B, ticked, posted


def _cleanup(B, *names):
    for a in names:
        B.bot.__dict__.pop(a, None)


def test_server_removed_mid_pass_is_skipped():
    """Nov 3, WoWffles: set up at 7:27 PM (noon skipped), removed the bot at 7:32. The pass that was already
    running held the old config, whose 'posted' marks had just been deleted, and logged a false
    slot_missed reason=offline 15 seconds later."""
    from forever_bot.store import GuildConfig
    B, ticked, posted = _sched_bot()
    try:
        st = B.bot.store
        a = GuildConfig(guild_id=1, channel_id=10, enabled=True)
        w = GuildConfig(guild_id=2, channel_id=20, enabled=True)
        st.upsert_guild(a)
        st.upsert_guild(w)
        setup_at = datetime(2026, 11, 4, 1, 27, tzinfo=timezone.utc)  # 7:27 PM Central
        assert B.bot.skip_passed_slots(w, setup_at) == [0]
        real_tick = B.bot._tick_guild

        async def tick(cfg, now):
            ticked.append(cfg.guild_id)
            if cfg.guild_id == 1:
                st.remove_guild(2)  # WoWffles kicks the bot while the pass is on server 1
            await real_tick(cfg, now)
        B.bot._tick_guild = tick
        with _events() as evs:
            asyncio.run(B.bot.run_schedule_pass(datetime(2026, 11, 4, 1, 33, tzinfo=timezone.utc)))
        assert ticked == [1]
        assert not [e for e in evs if e[0] == "slot_missed" and e[2]["guild"] == 2]
        assert not posted
    finally:
        _cleanup(B, "post_daily", "_tick_guild")


def test_live_cfg_skips_servers_the_bot_left():
    from forever_bot.store import GuildConfig
    B, _, _ = _sched_bot()
    try:
        st = B.bot.store
        st.upsert_guild(GuildConfig(guild_id=5, channel_id=50, enabled=True))
        stale = GuildConfig(guild_id=5, channel_id=50, enabled=True, post_time="12pm")
        st.upsert_guild(GuildConfig(guild_id=5, channel_id=50, enabled=True, post_time="9am"))
        assert B.bot.live_cfg(stale).post_time == "9am"  # picks up a /frequency change made mid-pass
        st.upsert_guild(GuildConfig(guild_id=5, channel_id=50, enabled=False))
        assert B.bot.live_cfg(stale) is None  # turned off
        st.upsert_guild(GuildConfig(guild_id=5, channel_id=50, enabled=True))
        B.bot.is_ready, B.bot.get_guild = (lambda: True), (lambda gid: None)
        with _events() as evs:
            assert B.bot.live_cfg(stale) is None and B.bot.live_cfg(stale) is None
        assert len([e for e in evs if e[0] == "tick_skipped"]) <= 1  # said once, not every minute
        B.bot.get_guild = lambda gid: _t.SimpleNamespace(id=gid)
        assert B.bot.live_cfg(stale) is not None
    finally:
        _cleanup(B, "post_daily", "is_ready", "get_guild")
        B.bot._said.clear()


def test_schedule_change_into_past_skips_quietly():
    """A /frequency or /setup change that moves a slot into the past used to backfill it late or log it as
    missed ('offline'). The reply already said passed slots wait for tomorrow; now the scheduler agrees."""
    from forever_bot.store import GuildConfig
    B, _, posted = _sched_bot()
    try:
        st = B.bot.store
        before = GuildConfig(guild_id=8, channel_id=80, enabled=True, post_time="12:00")
        st.upsert_guild(before)
        st.mark_posted(8, "daily", "launch:2026-11-04:0")  # noon went out
        after = GuildConfig(guild_id=8, channel_id=80, enabled=True, post_time="12:00,13:00")
        st.upsert_guild(after)
        four_pm = datetime(2026, 11, 4, 22, 0, tzinfo=timezone.utc)
        assert B.bot.skip_passed_slots(after, four_pm, before=before) == [1]
        with _events() as evs:
            asyncio.run(B.bot._tick_guild(after, four_pm))
        assert not posted and not [e for e in evs if e[0] == "slot_missed"]
        # an unchanged slot that's due right now is left for the scheduler to post
        due = GuildConfig(guild_id=9, channel_id=90, enabled=True, post_time="12:00")
        st.upsert_guild(due)
        noon = datetime(2026, 11, 4, 18, 0, 30, tzinfo=timezone.utc)
        assert B.bot.skip_passed_slots(due, noon, before=GuildConfig(guild_id=9, channel_id=90, post_time="12:00")) == []
        asyncio.run(B.bot._tick_guild(due, noon))
        assert posted == [(9, 0)]
        # a new time zone moves every slot: the passed ones are skipped
        tz = GuildConfig(guild_id=10, channel_id=1, enabled=True, post_time="12:00", tz="Europe/London")
        st.upsert_guild(tz)
        assert B.bot.skip_passed_slots(tz, four_pm, before=GuildConfig(guild_id=10, post_time="12:00")) == [0]
    finally:
        _cleanup(B, "post_daily")


def test_missed_slot_reported_once_across_restarts():
    """Nov 1, The NeverEnding Story: the same missed noon slot was logged three times across deploys."""
    from forever_bot.store import GuildConfig
    B, _, _ = _sched_bot()
    try:
        cfg = GuildConfig(guild_id=11, channel_id=110, enabled=True)
        B.bot.store.upsert_guild(cfg)
        late = datetime(2026, 11, 1, 3, 30, tzinfo=timezone.utc)  # 10:30 PM Central, noon window long gone
        with _events() as evs:
            for _ in range(3):
                B.bot._said.clear()  # what a restart does to the in-memory dedupe
                asyncio.run(B.bot._tick_guild(cfg, late))
        missed = [e for e in evs if e[0] == "slot_missed"]
        assert len(missed) == 1 and missed[0][2]["reason"] == "offline"
    finally:
        _cleanup(B, "post_daily")


def test_blocked_channel_logs_error_once_a_week():
    """'Forever and ever.' has been blocked since Nov 1: an ERROR for every slot and event, every day."""
    from forever_bot.bot import ForeverBot
    from forever_bot.store import GuildConfig
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "x.db")
    b = ForeverBot()
    b.store = tmp_store()
    b.snap = dict(SAMPLE, fetched_at=time.time())
    b.get_channel, b.get_guild = (lambda cid: None), (lambda gid: None)
    cfg = GuildConfig(guild_id=12, channel_id=120, post_time="12:00", tz="Australia/Sydney")
    b.store.upsert_guild(cfg)
    levels = []
    with _events() as evs:
        for day in (3, 4, 5, 11):  # Tue, Wed, Thu, then the next Tuesday
            asyncio.run(b.post_daily(cfg, datetime(2026, 11, day, 1, 1, tzinfo=timezone.utc)))
        levels = [lvl for ev_, lvl, _ in evs if ev_ == "post_blocked"]
    assert levels == [logging.ERROR, logging.INFO, logging.INFO, logging.ERROR]


def test_one_bad_server_never_stops_event_posts():
    from forever_bot import bot as B
    sent = []

    class Ch:
        def __init__(self, gid):
            self.gid, self.guild = gid, _t.SimpleNamespace(name=f"g{gid}")

        async def send(self, content, allowed_mentions=None):
            if self.gid == 1:
                raise RuntimeError("weird channel")
            sent.append(self.gid)
    cfgs = [_t.SimpleNamespace(guild_id=g, channel_id=g, ping_role_id=None) for g in (1, 2)]
    st = tmp_store()
    fake = _t.SimpleNamespace(store=_t.SimpleNamespace(all_guilds=lambda: cfgs, was_posted=st.was_posted,
                                                        mark_posted=st.mark_posted),
                              get_channel=lambda cid: Ch(cid), _can_post=lambda ch: None,
                              say_once=lambda *a, **k: None, live_cfg=lambda c: c)
    with _events() as evs:
        asyncio.run(B.ForeverBot.send_event_ping(fake, "launch-test", "hi"))
    assert sent == [2] and any(e[0] == "event_crashed" for e in evs)


def test_status_and_heartbeat_loops_never_raise():
    """Nov 2: Bluesky timed out three times in a row. A failed check skips that round; the loop lives."""
    from forever_bot import bot as B
    orig = B.S.check

    async def down(session, store):
        raise TimeoutError("bsky")
    B.S.check = down
    try:
        with _events() as evs:
            asyncio.run(B.ForeverBot.status_loop.coro(B.bot))
        assert any(e[0] == "status_check_failed" and e[1] == logging.WARNING for e in evs)
    finally:
        B.S.check = orig

    async def broken():
        raise RuntimeError("x")
    B.bot._heartbeat = broken
    try:
        with _events() as evs:
            asyncio.run(B.ForeverBot.heartbeat_loop.coro(B.bot))
        assert any(e[0] == "heartbeat_crashed" for e in evs)
    finally:
        _cleanup(B, "_heartbeat")


def test_daily_post_renders_when_every_source_is_down():
    cfg = Cfg()
    empty = {"fetched_at": time.time()}  # no news, clips, videos or status: every fetcher failed
    for slot in (0, 1):
        p = R.build_daily(cfg, at_post_time(date(2026, 11, 4), cfg), empty, {}, slot=slot)
        assert p and p.embeds and 0 < len(p.embeds[0]["description"]) < 4096


# ------------------------------------------------------------------ 1.12.3
def test_blocked_retries_are_not_logged_as_late():
    """Nov 4-6: blocked channels logged slot_late "bot restarted or was down" every day while the bot was up."""
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "l.db")
    from types import SimpleNamespace
    import forever_bot.bot as B
    from forever_bot.store import GuildConfig
    b = B.ForeverBot()
    b.store = tmp_store()
    events = []
    b.say_once = lambda logger, dedupe, event, *a, **kw: events.append(event)

    async def post_daily(cfg, now, slot=0):
        events.append("post_daily")
    b.post_daily = post_daily
    cfg = GuildConfig(guild_id=9, channel_id=100, post_time="12:00", tz="America/Chicago")
    b.store.upsert_guild(cfg)
    late = datetime(2026, 11, 20, 18, 10, tzinfo=timezone.utc)  # 10 min after noon Central
    asyncio.run(b._tick_guild(cfg, late))
    assert events == ["slot_late", "post_daily"], events  # really late: still reported
    events.clear()
    b.store.mark_posted(9, "blocked", "raids:2026-11-20:0")
    asyncio.run(b._tick_guild(cfg, late))
    assert events == ["post_daily"], events  # blocked retry: keeps trying, no slot_late


def test_setup_button_refused_falls_back_to_plain_embed():
    """Nov 6 Eternal Wardens: Discord refused the 📍 Post here button with 20062; welcome and reminder never landed."""
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "w.db")
    from types import SimpleNamespace
    import discord
    import forever_bot.bot as B
    b = B.ForeverBot()
    sent = []
    resp = SimpleNamespace(status=403, reason="Forbidden")

    class Ch:
        id = 1

        def __init__(self, code):
            self.code = code

        async def send(self, **kw):
            if "view" in kw and self.code:
                raise discord.HTTPException(resp, {"code": self.code, "message": "nope"})
            sent.append(("view" in kw, kw["embed"].title))

    e = discord.Embed(title="hi")
    assert asyncio.run(b.send_with_setup_button(Ch(None), embed=e)) is False and sent == [(True, "hi")]
    sent.clear()
    assert asyncio.run(b.send_with_setup_button(Ch(20062), embed=e)) is True and sent == [(False, "hi")]
    sent.clear()
    try:  # any other refusal (e.g. Missing Permissions) still surfaces to the caller
        asyncio.run(b.send_with_setup_button(Ch(50013), embed=e))
        assert False, "should raise"
    except discord.HTTPException:
        assert sent == []
    assert "/setup" in R.welcome_embed(datetime(2026, 11, 6, tzinfo=timezone.utc))["description"]
    assert "/setup" in R.setup_reminder_embed(datetime(2026, 11, 6, tzinfo=timezone.utc))["description"]


def test_refresh_done_ignores_sources_switched_off():
    """YouTube has been off since 1.1.1; every refresh still logged ok=4 total=5."""
    import logging
    orig_news, orig_fetch, orig_show = C.NEWS_SOURCES, F.fetch_news_source, C.SHOW_YOUTUBE
    lines = []

    class H(logging.Handler):
        def emit(self, rec):
            if rec.getMessage() == "refresh_done":
                lines.append(rec.fields)
    h = H()
    logging.getLogger().addHandler(h)
    logging.getLogger().setLevel(logging.INFO)

    async def fake_news(session, src):
        return []
    C.NEWS_SOURCES, F.fetch_news_source, C.SHOW_YOUTUBE = [{"name": "A"}, {"name": "B"}], fake_news, False
    try:
        snap = asyncio.run(F.refresh_all(tmp_store(), None, None))
    finally:
        C.NEWS_SOURCES, F.fetch_news_source, C.SHOW_YOUTUBE = orig_news, orig_fetch, orig_show
        logging.getLogger().removeHandler(h)
    assert snap["health"]["youtube"] == "off"
    assert lines and lines[-1]["ok"] == 2 and lines[-1]["total"] == 2 and "youtube" in lines[-1]["off"], lines


# ------------------------------------------------------------- 1.12.4 facts ledger, refusals, hotfix line
def _with_ledger(entries, fn):
    """Run fn with a temporary ledger (the real one is restored after)."""
    from forever_bot import ledger as L
    orig = L.PATH
    path = os.path.join(tempfile.mkdtemp(), "ledger.json")
    with open(path, "w") as f:
        json.dump({"entries": entries}, f)
    L.PATH = path
    L.entries.cache_clear()
    try:
        return fn()
    finally:
        L.PATH = orig
        L.entries.cache_clear()


def test_ledger_matches_pools():
    """Every tip/fact line has a ledger entry and the ledger has no lines that were removed from the pools."""
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "facts.py"),
                        "check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_fresh_lines_get_one_day_each():
    pool = [f"old fact {i}" for i in range(20)] + ["new A", "new B", C.dm("new C")]
    e = [{"text": "new A", "added": "2026-11-09"}, {"text": "new B", "added": "2026-11-09"},
         {"text": "new C", "added": "2026-11-09"}]

    def run():
        shown = [R.pick(R.V(pool), date(2026, 11, 9) + timedelta(days=k), salt=3) for k in range(0, 6)]
        later = R.pick(R.V(pool), date(2026, 11, 10), salt=16)  # evening check-in: no featuring
        return shown, later
    with R.datamined(True):
        shown, later = _with_ledger(e, run)
    assert shown[1:4] == ["new A", "new B", "new C" + C.DM_LABEL], shown  # then one a day, in order
    assert later != "new A"


def test_expired_lines_drop_out():
    pool = ["keeps going", "only until the 10th"]
    e = [{"text": "only until the 10th", "expires": "2026-11-10"}]

    def run():
        return {R.pick(pool, date(2026, 11, 11) + timedelta(days=k)) for k in range(10)}
    assert _with_ledger(e, run) == {"keeps going"}


def test_hotfix_headlines_first_with_wrench():
    snap = {"news": [{"id": "news:1", "title": "Top 10 Forever clips this week", "url": "https://a", "source": "X"},
                     {"id": "news:2", "title": "WoW Forever Hotfixes for November 6", "url": "https://b", "source": "Y"}]}
    embeds, used, _ = R._media(snap, None, datetime(2026, 11, 9, tzinfo=timezone.utc), True, False)
    desc = embeds[0]["description"]
    assert desc.startswith("🔧 [WoW Forever Hotfixes"), desc
    assert "🔧 [Top 10" not in desc
    assert R.is_hotfix("Dungeon Enemy XP Increased - November 8") and not R.is_hotfix("World First Level 60")


def test_refused_post_outcome():
    from forever_bot.bot import postnow_outcome as o, REFUSED_CODES
    assert 20062 in REFUSED_CODES
    assert o("Discord refused the post: 403 Forbidden") == "refused"


def test_new_facts_present():
    lev = " ".join(map(str, C.TIPS["leveling"]))
    assert "50%" in lev and "dual specialization" in lev
    assert any("Tanning Rack at 125" in str(t) for t in C.TIPS["professions"])
    dd9 = " ".join(C.DEEP_DIVES[9][1])
    assert "Blizzard can pause" not in dd9 and "recalculates the balance" in dd9
