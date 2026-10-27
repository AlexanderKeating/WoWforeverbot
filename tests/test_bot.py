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
    assert [c["title"] for c in clips] == ["Forever beta talents", "insane duel"]  # Forever first; one loose per streamer
    assert not clips[0].get("loose") and clips[1]["loose"]
    snap = {"news": [], "clips": clips, "videos": []}
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


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} passed")
