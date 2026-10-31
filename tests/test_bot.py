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
    while d <= date(2026, 12, 12):
        post = R.build_daily(cfg, at_post_time(d, cfg), SAMPLE, counts)
        if d > date(2026, 12, 9):
            assert post is None
        else:
            assert post is not None
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
                                 say_once=lambda *a, **k: None)
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

    async def fake_get(session, url, params=None, want_json=False, **k):
        return {"feed": [{"post": {"uri": "at://x/app.bsky.feed.post/1", "author": {"handle": "support.blizzard.com"},
                                   "record": {"text": "WoW: Forever login issues, investigating.", "createdAt": iso(0.1)}}},
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
    for bad in ("13pm", "25:00", "abc", "0am", ""):
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
    assert got and got[0] == latest and "/datamined" in got[1]
    assert C.latest_line_since("1.8.0")[1] == got[1]
    assert C.latest_line_since(latest) is None and C.latest_line_since("1.10.7")[1] == got[1]
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
    assert "Elemental Mastery is gone" not in blob and "300% more" not in blob
