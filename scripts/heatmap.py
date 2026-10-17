#!/usr/bin/env python3
"""Render the last year of GitHub contributions as a green-phosphor SVG heatmap.

Days with contributions blink softly (CSS animation, each cell on its own
random delay/period so they twinkle out of sync). Empty days stay static.

Usage:
  GITHUB_TOKEN=... python scripts/heatmap.py magnuls assets/heatmap.svg
  python scripts/heatmap.py magnuls assets/heatmap.svg --demo   # fake data, no token
"""
import datetime as dt
import json
import os
import random
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

# Phosphor palette: background, empty cell, then levels 1-4.
BG, PANEL, BORDER = "#050805", "#0a120a", "#1d3a1d"
EMPTY = "#0f1f0f"
GREENS = ["#1f6b1f", "#2fa52f", "#46d846", "#7dff6e"]
TEXT, DIM = "#b6ff9e", "#4f8a4f"


def fetch(login: str):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    cal = json.load(urllib.request.urlopen(req))["data"]["user"][
        "contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]])
              for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def demo():
    rng = random.Random(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    weeks, total, day = [], 0, start
    while day <= today:
        week = []
        for _ in range(7):
            if day > today:
                break
            n = 0 if rng.random() < 0.35 else rng.choice([1, 1, 2, 3, 5, 8])
            total += n
            lvl = 0 if n == 0 else 1 if n < 2 else 2 if n < 4 else 3 if n < 7 else 4
            week.append((day.isoformat(), n, lvl))
            day += dt.timedelta(days=1)
        weeks.append(week)
    return total, weeks


def render(total, weeks):
    cell, gap = 11, 3
    step = cell + gap
    left, top = 46, 64
    w = left + len(weeks) * step + 20
    h = top + 7 * step + 46
    rng = random.Random(total)
    out = []
    a = out.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
      f'viewBox="0 0 {w} {h}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">')
    a("<style>"
      "@keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}"
      ".on{animation:blink var(--d) ease-in-out infinite;animation-delay:var(--t)}"
      "@media (prefers-reduced-motion:reduce){.on{animation:none}}"
      "</style>")
    a('<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
      '<feGaussianBlur stdDeviation="1.6" result="b"/>'
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
      "</filter></defs>")
    a(f'<rect width="{w}" height="{h}" rx="10" fill="{BG}"/>')
    a(f'<rect x="6" y="6" width="{w-12}" height="{h-12}" rx="7" fill="{PANEL}" '
      f'stroke="{BORDER}"/>')

    a(f'<text x="{left}" y="36" fill="{TEXT}" font-size="17" font-weight="700" '
      f'filter="url(#glow)">{total:,} contributions in the last year</text>')

    # Month labels at the first week whose first day starts a new month.
    last_month = None
    for i, week in enumerate(weeks):
        m = dt.date.fromisoformat(week[0][0]).strftime("%b")
        if m != last_month and i < len(weeks) - 1:
            if last_month is not None or dt.date.fromisoformat(week[0][0]).day <= 7:
                a(f'<text x="{left + i*step}" y="{top-8}" fill="{DIM}" font-size="10">{m}</text>')
            last_month = m

    for r, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        a(f'<text x="14" y="{top + r*step + 9}" fill="{DIM}" font-size="9">{label}</text>')

    a('<g filter="url(#glow)">')
    for i, week in enumerate(weeks):
        for date, count, lvl in week:
            r = (dt.date.fromisoformat(date).weekday() + 1) % 7  # Sunday = row 0
            x, y = left + i * step, top + r * step
            tip = f"<title>{count} on {date}</title>"
            if lvl == 0:
                a(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" '
                  f'fill="{EMPTY}">{tip}</rect>')
            else:
                d = rng.uniform(2.4, 5.5)
                t = rng.uniform(0, 6)
                a(f'<rect class="on" style="--d:{d:.2f}s;--t:-{t:.2f}s" x="{x}" y="{y}" '
                  f'width="{cell}" height="{cell}" rx="2.5" fill="{GREENS[lvl-1]}">{tip}</rect>')
    a("</g>")

    a(f'<text x="{left}" y="{h-18}" fill="{DIM}" font-size="10">'
      f"&gt; github activity heatmap // contribution stream online</text>")
    a("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    login, path = sys.argv[1], sys.argv[2]
    total, weeks = demo() if "--demo" in sys.argv else fetch(login)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(render(total, weeks))
    print(f"wrote {path}: {total} contributions, {len(weeks)} weeks")
