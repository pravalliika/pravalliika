#!/usr/bin/env python3
"""Generate assets/stats-card.svg and assets/languages-card.svg from live GitHub data.

Usage: GH_TOKEN=... python scripts/generate_cards.py [username]
       python scripts/generate_cards.py --demo      (renders with sample numbers)
"""
import json, os, sys, urllib.request
from html import escape

USER = "pravalliika"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT = "Segoe UI,Helvetica,Arial,sans-serif"

QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    pullRequests{totalCount}
    contributionsCollection{
      totalCommitContributions
      contributionCalendar{totalContributions}
    }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{
        stargazerCount forkCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}){
          edges{size node{name color}}
        }
      }
    }
  }
}"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    u = data["data"]["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]
            cur = langs.setdefault(n["name"], {"size": 0, "color": n["color"] or "#94a3b8"})
            cur["size"] += e["size"]
    return {
        "contrib": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "commits": u["contributionsCollection"]["totalCommitContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "forks": sum(r["forkCount"] for r in repos),
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "bytes": sum(v["size"] for v in langs.values()),
        "langs": langs,
    }


def demo():
    langs = {"Python": 52000, "HCL": 31000, "Shell": 14000, "Dockerfile": 6000, "YAML": 9000}
    cols = {"Python": "#3572A5", "HCL": "#844FBA", "Shell": "#89e051", "Dockerfile": "#384d54", "YAML": "#cb171e"}
    return {"contrib": 0, "commits": 0, "prs": 0, "stars": 0, "forks": 0, "repos": 0,
            "followers": 0, "bytes": sum(langs.values()),
            "langs": {k: {"size": v, "color": cols[k]} for k, v in langs.items()}}


def human_bytes(n):
    if n >= 1_000_000: return f"{n/1_000_000:.2f} MB"
    if n >= 1_000: return f"{n/1_000:.1f} KB"
    return f"{n} B"


DEFS = """<defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#020617"/><stop offset="100%" stop-color="#1e1b4b"/></linearGradient></defs>"""


def stats_svg(s, login):
    rows = [("Total Contributions (all time)", f"{s['contrib']:,}"), ("Commits (past year)", f"{s['commits']:,}"),
            ("Pull Requests", f"{s['prs']:,}"), ("Stars Earned", f"{s['stars']:,}"),
            ("Community Forks", f"{s['forks']:,}"), ("Public Repositories", f"{s['repos']:,}"),
            ("Followers", f"{s['followers']:,}"), ("Code Written", human_bytes(s["bytes"]))]
    body = ""
    for i, (k, v) in enumerate(rows):
        y = 74 + i * 30
        body += (f'<text x="26" y="{y}" fill="#94a3b8" font-family="{FONT}" font-size="13">{k}</text>'
                 f'<text x="434" y="{y}" fill="#e0f2fe" text-anchor="end" font-family="{FONT}" font-size="14" font-weight="600">{v}</text>\n')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="460" height="330" viewBox="0 0 460 330" role="img" '
            f'aria-label="GitHub statistics for {escape(login)}"><title>GitHub statistics for {escape(login)}</title>{DEFS}'
            f'<rect x="0.5" y="0.5" width="459" height="329" rx="12" fill="url(#bg)" stroke="#334155"/>'
            f'<text x="26" y="36" fill="#67e8f9" font-family="{FONT}" font-size="17" font-weight="600">GitHub Statistics</text>'
            f'<rect x="26" y="50" width="408" height="1" fill="#334155"/>\n{body}</svg>\n')


def langs_svg(s, login, top=6):
    items = sorted(s["langs"].items(), key=lambda kv: -kv[1]["size"])[:top]
    total = sum(v["size"] for _, v in items) or 1
    body, bar_x = "", 26.0
    for name, v in items:  # stacked bar
        w = 408 * v["size"] / total
        body += f'<rect x="{bar_x:.1f}" y="62" width="{w:.1f}" height="10" fill="{v["color"]}"/>'
        bar_x += w
    for i, (name, v) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = 26 + col * 210, 112 + row * 36
        pct = 100 * v["size"] / total
        body += (f'<circle cx="{x+5}" cy="{y-4}" r="5" fill="{v["color"]}"/>'
                 f'<text x="{x+18}" y="{y}" fill="#94a3b8" font-family="{FONT}" font-size="13">{escape(name)}</text>'
                 f'<text x="{x+190}" y="{y}" fill="#e0f2fe" text-anchor="end" font-family="{FONT}" font-size="13" font-weight="600">{pct:.1f}%</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="460" height="330" viewBox="0 0 460 330" role="img" '
            f'aria-label="Most used languages for {escape(login)}"><title>Most used languages</title>{DEFS}'
            f'<rect x="0.5" y="0.5" width="459" height="329" rx="12" fill="url(#bg)" stroke="#334155"/>'
            f'<text x="26" y="36" fill="#67e8f9" font-family="{FONT}" font-size="17" font-weight="600">Most Used Languages</text>'
            f'<clipPath id="c"><rect x="26" y="62" width="408" height="10" rx="5"/></clipPath><g clip-path="url(#c)">{body.split("<circle")[0]}</g>'
            f'<circle{"<circle".join(body.split("<circle")[1:])}</svg>\n')



CAL_QUERY = """
query($login:String!, $from:DateTime, $to:DateTime){
  user(login:$login){
    createdAt
    contributionsCollection(from:$from, to:$to){
      contributionCalendar{ weeks{ contributionDays{ date contributionCount } } }
    }
  }
}"""


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def fetch_days(login, token):
    """Every day since the account was created -> {date: count} (GitHub allows 1 year per query)."""
    import datetime as dt
    created = dt.datetime.fromisoformat(gql(CAL_QUERY, {"login": login}, token)["createdAt"].replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    days, start = {}, created
    while start < now:
        end = min(start + dt.timedelta(days=364), now)
        u = gql(CAL_QUERY, {"login": login, "from": start.isoformat(), "to": end.isoformat()}, token)
        for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        start = end + dt.timedelta(days=1)
    return days


def streaks(days):
    import datetime as dt
    dates = sorted(days)
    total = sum(days.values())
    longest = run = 0
    longest_end = None
    prev = None
    for d in dates:
        cur = dt.date.fromisoformat(d)
        if days[d] > 0:
            run = run + 1 if prev and (cur - prev).days == 1 else 1
            if run > longest: longest, longest_end = run, cur
            prev = cur
        else:
            run, prev = 0, None
    # current streak: walk back from today (a zero today doesn't break it yet)
    today = dt.date.fromisoformat(dates[-1])
    cur_len, d = 0, today
    if days.get(d.isoformat(), 0) == 0: d -= dt.timedelta(days=1)
    while days.get(d.isoformat(), 0) > 0:
        cur_len += 1; d -= dt.timedelta(days=1)
    return {"total": total, "since": dates[0], "current": cur_len, "longest": longest}


def demo_days():
    import datetime as dt, random
    random.seed(1)
    t = dt.date.today()
    return {(t - dt.timedelta(days=i)).isoformat(): random.choice([0, 1, 2, 3]) for i in range(900)}


def streak_svg(st, login):
    import datetime as dt
    since = dt.date.fromisoformat(st["since"]).strftime("%b %Y")
    cols = [(st["total"], "Total Contributions", f"{since} - Present", "#67e8f9"),
            (st["current"], "Current Streak", "days in a row", "#a78bfa"),
            (st["longest"], "Longest Streak", "days in a row", "#34d399")]
    body = ""
    for i, (num, label, sub, color) in enumerate(cols):
        cx = 77 + i * 153
        body += (f'<text x="{cx}" y="95" fill="{color}" text-anchor="middle" font-family="{FONT}" font-size="32" font-weight="700">{num:,}</text>'
                 f'<text x="{cx}" y="125" fill="#e0f2fe" text-anchor="middle" font-family="{FONT}" font-size="13" font-weight="600">{label}</text>'
                 f'<text x="{cx}" y="146" fill="#94a3b8" text-anchor="middle" font-family="{FONT}" font-size="11">{sub}</text>')
        if i: body += f'<rect x="{cx-76}" y="62" width="1" height="100" fill="#334155"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="460" height="180" viewBox="0 0 460 180" role="img" '
            f'aria-label="{escape(login)}: {st["total"]} total contributions, {st["current"]}-day current streak, {st["longest"]}-day longest streak">'
            f'<title>Contribution streak</title>{DEFS}<rect x="0.5" y="0.5" width="459" height="179" rx="12" fill="url(#bg)" stroke="#334155"/>'
            f'<text x="26" y="36" fill="#67e8f9" font-family="{FONT}" font-size="17" font-weight="600">Contributions &amp; Streak</text>'
            f'{body}</svg>\n')


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    login = args[0] if args else USER
    is_demo = "--demo" in sys.argv
    stats = demo() if is_demo else fetch(login, os.environ["GH_TOKEN"])
    days = demo_days() if is_demo else fetch_days(login, os.environ["GH_TOKEN"])
    st = streaks(days)
    stats["contrib"] = st["total"]          # lifetime total, not just the past year
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "stats-card.svg"), "w").write(stats_svg(stats, login))
    open(os.path.join(OUT, "languages-card.svg"), "w").write(langs_svg(stats, login))
    open(os.path.join(OUT, "streak-card.svg"), "w").write(streak_svg(st, login))
    print("cards written for", login, st)
