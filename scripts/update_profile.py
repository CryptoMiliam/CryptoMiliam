"""Generate profile charts from aggregate GitHub contribution data only."""
import datetime
import json
import pathlib
import subprocess
import os
import xml.sax.saxutils as xml

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUERY = '''query { user(login:"CryptoMiliam") { contributionsCollection {
contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
} } }'''


def fetch():
    fixture = os.environ.get("PROFILE_CALENDAR_INPUT")
    if fixture:
        data = json.loads(pathlib.Path(fixture).read_text())
    else:
        data = json.loads(subprocess.check_output(["gh", "api", "graphql", "-f", "query=" + QUERY], text=True))
    if data.get("errors"):
        raise ValueError("GitHub could not return the contribution calendar")
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    if not days or any(type(d["contributionCount"]) is not int or d["contributionCount"] < 0 for d in days):
        raise ValueError("Invalid contribution calendar")
    if calendar["totalContributions"] != sum(d["contributionCount"] for d in days):
        raise ValueError("Contribution calendar total does not match daily totals")
    return calendar, weeks, days


def svg(width, height, body, label):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{xml.escape(label)}"><rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="14" fill="#0d1724" stroke="#263a4a"/>{body}</svg>\n'


def text(x, y, value, size=14, color="#b8c9da", weight="400"):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{xml.escape(str(value))}</text>'


def main():
    calendar, weeks, days = fetch()
    last_date = datetime.date.fromisoformat(days[-1]["date"])
    cutoff = last_date - datetime.timedelta(days=29)
    recent = [d for d in days if datetime.date.fromisoformat(d["date"]) >= cutoff]
    # Streak ends on today, or yesterday if today's contribution count is still zero.
    streak = 0
    ending = days[:-1] if days[-1]["contributionCount"] == 0 else days
    for day in reversed(ending):
        if day["contributionCount"] == 0:
            break
        streak += 1
    metrics = [("PAST YEAR", f'{calendar["totalContributions"]:,}', "contributions"),
               ("LAST 30 DAYS", f'{sum(d["contributionCount"] for d in recent):,}', "contributions"),
               ("ACTIVE DAYS", str(sum(d["contributionCount"] > 0 for d in days)), "in the past year"),
               ("CURRENT STREAK", str(streak), "consecutive days")]
    body = text(30, 34, "Contribution activity", 18, "#f2f7fc", "700")
    for i, (label, value, caption) in enumerate(metrics):
        x = 30 + i * 242
        body += text(x, 73, label, 11, "#8ba5ba", "700") + text(x, 113, value, 32, "#43e6bf", "700") + text(x, 140, caption, 12)
    body += text(30, 178, f'Rolling calendar through {last_date.isoformat()} · Includes publicized private contributions', 11, "#8ba5ba")
    (ROOT / "assets/activity.svg").write_text(svg(1000, 200, body, "GitHub contribution totals and active-day statistics"))
    colors = ["#172737", "#174b48", "#207e6c", "#2fb393", "#43e6bf"]
    body = text(30, 34, "A year of building", 18, "#f2f7fc", "700")
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            dt = datetime.date.fromisoformat(day["date"])
            row = (dt.weekday() + 1) % 7
            n = day["contributionCount"]
            level = 0 if n == 0 else 1 if n < 10 else 2 if n < 30 else 3 if n < 75 else 4
            x, y = 30 + col * 17, 60 + row * 17
            body += f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{colors[level]}"><title>{dt.isoformat()}: {n} contributions</title></rect>'
    body += text(30, 202, f'{days[0]["date"]} — {days[-1]["date"]}', 11, "#8ba5ba")
    body += text(744, 202, "Less", 11, "#8ba5ba")
    for i, color in enumerate(colors):
        body += f'<rect x="{778+i*17}" y="190" width="13" height="13" rx="3" fill="{color}"/>'
    body += text(870, 202, "More", 11, "#8ba5ba")
    (ROOT / "assets/contributions.svg").write_text(svg(1000, 226, body, "Daily GitHub contributions, including publicized private contributions"))
    print("Profile charts refreshed from aggregate contribution data.")


if __name__ == "__main__":
    main()
