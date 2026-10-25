"""Offline tests: python -m pytest tests -q   (or python tests/test_bot.py)"""
import asyncio
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


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} passed")
