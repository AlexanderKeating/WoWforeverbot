"""Write the What's new page for foreversherpa.github.io from content.RELEASE_NOTES.

    python tools/build_whatsnew.py ../foreversherpa.github.io/whatsnew.html
"""
import html
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forever_bot import content as C  # noqa: E402


def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)


def page() -> str:
    items = []
    for r in C.RELEASE_NOTES:
        d = date.fromisoformat(r["date"])
        notes = "\n".join(f"  <li>{inline(n)}</li>" for n in r["notes"])
        items.append(f'<h2 id="v{r["version"]}">{inline(r["title"])}</h2>\n'
                     f'<div class="meta">Version {r["version"]} · {d.strftime("%B")} {d.day}, {d.year}</div>\n'
                     f"<ul>\n{notes}\n</ul>")
    body = "\n\n".join(items)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forever Sherpa · What's new</title>
<meta name="description" content="Recent changes to the Forever Sherpa Discord bot.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
<header>
  <div class="brand">Forever Sherpa</div>
  <h1>What's new</h1>
  <div class="meta">Recent changes to the bot, newest first.</div>
  <nav style="margin-top:12px"><a href="./">Home</a><a href="terms.html">Terms</a><a href="privacy.html">Privacy</a></nav>
</header>

<div class="box">After an update, the next post in your server gets one short 🆕 line about what changed. Admins can turn that off with <code>/updates</code>. <code>/whatsnew</code> shows the latest changes in Discord.</div>

{body}

<footer>Forever Sherpa isn't affiliated with or endorsed by Blizzard Entertainment, Discord or Twitch. World of Warcraft is a trademark of Blizzard Entertainment, Inc.</footer>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "whatsnew.html"
    with open(target, "w", encoding="utf-8") as f:
        f.write(page())
    print(f"wrote {target}")
