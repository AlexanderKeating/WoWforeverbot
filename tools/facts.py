"""
1.12.4: the facts ledger tool, used by the rolling facts check (and by hand).

  python tools/facts.py sync                 # add a ledger entry for every line in the pools, drop removed ones
  python tools/facts.py due [N]              # the N lines most overdue for re-checking (never checked first)
  python tools/facts.py dupes "candidate"    # existing lines a new fact would repeat (word overlap)
  python tools/facts.py verified "substring" --source URL [--date YYYY-MM-DD]
  python tools/facts.py record "exact text" --source URL [--added DATE] [--expires DATE] [--note ...]
  python tools/facts.py expiring [DAYS]      # lines that expire soon or already have
  python tools/facts.py check                # exit 1 if pools and ledger disagree (used by the tests)

Ledger entry: {"text", "pool", "source", "added", "verified", "expires", "note"}.
  added     date the line went in (drives fresh-first in the bot); null for lines from before the ledger
  verified  last date someone checked it against a source; null = never checked since the ledger started
  expires   optional: after this date the bot stops showing it (for "planned for Nov 10"-style lines)
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from forever_bot import classes as K  # noqa: E402
from forever_bot import content as C  # noqa: E402
from forever_bot import ledger as L  # noqa: E402

DUP_THRESHOLD = 0.5


def pools() -> list[tuple[str, str]]:
    """(pool name, text) for every line the bot can show as a tip or fact."""
    out = []
    for topic, items in C.TIPS.items():
        out += [(f"TIPS.{topic}", str(t)) for t in items]
    out += [("NEWBIE_TIPS", str(t)) for t in C.NEWBIE_TIPS]
    out += [(f"DID_YOU_KNOW.{tag}", str(t)) for tag, t in C.DID_YOU_KNOW]
    for k, (_, items) in C.DEEP_DIVES.items():
        out += [(f"DEEP_DIVES.{k}", str(t)) for t in items]
    out += [(f"PRO_TIPS.{k}", str(t)) for k, t in C.PRO_TIPS.items()]
    for cls, d in K.CLASSES.items():
        for part in ("new", "leveling", "pvp"):
            out += [(f"CLASSES.{cls}.{part}", str(t)) for t in d.get(part, [])]
    seen, uniq = set(), []
    for p, t in out:
        if t not in seen:
            seen.add(t)
            uniq.append((p, t))
    return uniq


def load() -> dict:
    try:
        with open(L.PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"entries": []}


def save(data: dict):
    data["entries"].sort(key=lambda e: (e.get("pool", ""), e["text"]))
    with open(L.PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    L.entries.cache_clear()


def words(t: str) -> set:
    return {w for w in re.findall(r"[a-z0-9']+", t.lower()) if len(w) > 3}


def cmd_sync(_):
    data = load()
    have = {e["text"]: e for e in data["entries"]}
    live = pools()
    names = {t for _, t in live}
    added = 0
    for p, t in live:
        if t in have:
            have[t]["pool"] = p
        else:
            have[t] = {"text": t, "pool": p, "source": "", "added": None, "verified": None, "expires": None, "note": ""}
            added += 1
    removed = [t for t in have if t not in names]
    for t in removed:
        del have[t]
    data["entries"] = list(have.values())
    save(data)
    print(f"ledger: {len(data['entries'])} lines, {added} new, {len(removed)} removed")


def cmd_due(a):
    es = load()["entries"]
    es.sort(key=lambda e: (e.get("verified") is not None, e.get("verified") or "", e["pool"]))
    for e in es[: a.n]:
        print(f"[{e.get('verified') or 'never'}] {e['pool']}: {e['text']}")


def cmd_dupes(a):
    cand = words(a.text)
    hits = []
    for p, t in pools():
        w = words(t)
        if cand and w:
            score = len(cand & w) / min(len(cand), len(w))
            if score >= a.threshold:
                hits.append((score, p, t))
    for score, p, t in sorted(hits, reverse=True)[:10]:
        print(f"{score:.2f}  {p}: {t}")
    if not hits:
        print("no near-duplicates")
    sys.exit(1 if hits else 0)


def _find(data, sub):
    m = [e for e in data["entries"] if sub in e["text"]]
    if len(m) != 1:
        sys.exit(f"'{sub}' matches {len(m)} lines; make it more specific")
    return m[0]


def cmd_verified(a):
    data = load()
    e = _find(data, a.substring)
    e["verified"] = a.date or date.today().isoformat()
    if a.source:
        e["source"] = a.source
    save(data)
    print(f"verified {e['verified']}: {e['text'][:90]}")


def cmd_record(a):
    data = load()
    e = next((x for x in data["entries"] if x["text"] == a.text), None)
    if e is None:
        sys.exit("not in the ledger: add the line to content.py / classes.py and run sync first")
    today = date.today().isoformat()
    e.update(source=a.source or e.get("source", ""), added=a.added or e.get("added") or today,
             verified=a.verified or today, expires=a.expires or e.get("expires"), note=a.note or e.get("note", ""))
    save(data)
    print(f"recorded: {e['text'][:90]}")


def cmd_expiring(a):
    soon = (date.today() + timedelta(days=a.days)).isoformat()
    for e in load()["entries"]:
        if e.get("expires") and e["expires"] <= soon:
            print(f"[expires {e['expires']}] {e['pool']}: {e['text']}")


def cmd_check(_):
    have = {e["text"] for e in load()["entries"]}
    names = {t for _, t in pools()}
    missing, orphans = names - have, have - names
    for t in sorted(missing)[:20]:
        print("not in ledger:", t[:100])
    for t in sorted(orphans)[:20]:
        print("in ledger but not in any pool:", t[:100])
    sys.exit(1 if (missing or orphans) else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync").set_defaults(f=cmd_sync)
    p = sub.add_parser("due"); p.add_argument("n", nargs="?", type=int, default=15); p.set_defaults(f=cmd_due)
    p = sub.add_parser("dupes"); p.add_argument("text"); p.add_argument("--threshold", type=float, default=DUP_THRESHOLD)
    p.set_defaults(f=cmd_dupes)
    p = sub.add_parser("verified"); p.add_argument("substring"); p.add_argument("--source"); p.add_argument("--date")
    p.set_defaults(f=cmd_verified)
    p = sub.add_parser("record"); p.add_argument("text"); p.add_argument("--source", required=True)
    for opt in ("--added", "--verified", "--expires", "--note"):
        p.add_argument(opt)
    p.set_defaults(f=cmd_record)
    p = sub.add_parser("expiring"); p.add_argument("days", nargs="?", type=int, default=3); p.set_defaults(f=cmd_expiring)
    sub.add_parser("check").set_defaults(f=cmd_check)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
