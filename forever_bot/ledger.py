"""
1.12.4: facts ledger. One entry per tip/fact/deep-dive line, with where it came from and when it was last checked.

The ledger (facts_ledger.json, next to this file) is written by the rolling facts check (tools/facts.py) and read
here for two things the daily post needs:

  * fresh-first: a line added in the last FRESH_DAYS gets its own day at the front of its pool, once, instead of
    waiting behind 120 older ones. Days are handed out in the order lines were added, one per day per pool, so a
    batch of five new facts shows over five days rather than all at once or the same one every day.
  * expiry: a line with "expires" (e.g. "class tuning lands Nov 10") drops out of rotation after that date, so a
    post never says something that has stopped being true, even if nobody has edited the file yet.

Everything is deterministic for a given date, so the staging preview and the real post still match.
"""
import json
import os
from datetime import date, timedelta
from functools import lru_cache

PATH = os.path.join(os.path.dirname(__file__), "facts_ledger.json")
FRESH_DAYS = 14
DM_LABEL = " *(⛏️ datamined, may change)*"  # same text as content.DM_LABEL (no import: content imports nothing from here)


def key(text: str) -> str:
    """Ledger key for a line as players see it: the datamined label is display-only."""
    t = str(text)
    return t[: -len(DM_LABEL)] if t.endswith(DM_LABEL) else t


@lru_cache(maxsize=1)
def entries() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {e["text"]: e for e in data.get("entries", []) if e.get("text")}


def _day(v) -> date | None:
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None


def added_on(text) -> date | None:
    e = entries().get(key(text))
    return _day(e.get("added")) if e else None


def expired(text, d: date) -> bool:
    e = entries().get(key(text))
    end = _day(e.get("expires")) if e else None
    return bool(end and d > end)


def live(seq, d: date) -> list:
    """The pool minus anything past its expiry date (never empty if the pool wasn't)."""
    out = [x for x in seq if not (isinstance(x, str) and expired(x, d))]
    return out or list(seq)


def featured(seq, d: date):
    """The fresh line this pool shows on day d, or None. Lines added on the same day get consecutive days starting
    the next day (in ledger order), so a batch shows one a day. No queue carries across batches, so the answer for
    a line never shifts as newer lines arrive; if two batches want the same day, the newer line wins and the other
    one simply joins the normal rotation."""
    by_day: dict[date, list] = {}
    for x in seq:
        a = added_on(x) if isinstance(x, str) else None
        if a and timedelta(0) < d - a <= timedelta(days=FRESH_DAYS):
            by_day.setdefault(a, []).append(x)
    order = {k: i for i, k in enumerate(entries())}
    for a in sorted(by_day, reverse=True):  # newest batch first
        batch = sorted(by_day[a], key=lambda x: order.get(key(x), 0))
        r = (d - a).days - 1
        if r < len(batch):
            return batch[r]
    return None
