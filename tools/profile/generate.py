#!/usr/bin/env python3
"""Generate the self-hosted SVG console used by the GitHub profile."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

USER = "GuilhermeGms3"
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
DATA_FILE = Path(__file__).with_name("data.json")
API = "https://api.github.com/graphql"

BG, PANEL, PANEL_2, LINE = "#05080d", "#0a111a", "#0d1722", "#1f3545"
TEXT, MUTED = "#e6f1f5", "#7e95a3"
CYAN, TEAL, AMBER, BLUE, RED, PURPLE = (
    "#22d3ee", "#2dd4bf", "#f59e0b", "#38bdf8", "#fb7185", "#a78bfa"
)

PROJECTS = [
    ("muse-studio", "MUSE STUDIO", "PRODUCT / MUSIC OS",
     ("Connected workspace for learning,", "practice, repertoire and creation."),
     ("REACT 19", "SPRING BOOT", "JAVA 21"), CYAN, "M"),
    ("scriptorium-os", "SCRIPTORIUM OS", "PRODUCT / LOCAL-FIRST",
     ("Textual research workspace with local", "corpora, search and semantic tooling."),
     ("REACT 19", "SQLITE", "FTS5"), PURPLE, "S"),
    ("hub-infrasec", "HUB JORNADA INFRASEC", "LEARNING / PLATFORM",
     ("Guided certification paths with labs,", "assessments and portfolio evidence."),
     ("CCNA", "AWS", "KUBERNETES"), AMBER, "H"),
    ("aws-cicd", "AWS CI/CD BLUEPRINT", "CLOUD / DELIVERY",
     ("Security-gated delivery pipeline", "for container workloads on ECS."),
     ("TERRAFORM", "ACTIONS", "FARGATE"), BLUE, "A"),
    ("noc-sentinel", "NOC INCIDENT SENTINEL", "OPS / OBSERVABILITY",
     ("HTTP, TCP and DNS probes with", "metrics, alerting and incident routing."),
     ("PROMETHEUS", "GRAFANA", "ALERTS"), TEAL, "N"),
    ("network-monitor", "NETWORK MONITOR", "NETWORK / TELEMETRY",
     ("SNMP telemetry for device health", "and interface traffic visibility."),
     ("PYTHON", "SNMP", "DOCKER"), RED, "W"),
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def write(name: str, content: str) -> None:
    path = ASSETS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
    path.write_text(normalized, encoding="utf-8", newline="\n")


def shell(width: int, height: int, title: str, desc: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(title)}</title><desc id="desc">{esc(desc)}</desc>
  <style>
    .mono {{ font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace; }}
    .ui {{ font-family: "Segoe UI", Arial, sans-serif; }}
    .scan {{ animation: scan 6s linear infinite; opacity: .16; }}
    .blink {{ animation: blink 1.1s steps(2,start) infinite; }}
    @keyframes scan {{ from {{ transform: translateX(-220px); }} to {{ transform: translateX({width + 220}px); }} }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
  </style>
  <rect width="{width}" height="{height}" rx="16" fill="{BG}"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="15" fill="none" stroke="{LINE}" stroke-width="2"/>
  {body}
</svg>'''


def graphql(query: str, variables: dict[str, object]) -> dict[str, object]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not available")
    request = Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "guilhermegms3-profile-console",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("; ".join(item.get("message", "GraphQL error") for item in result["errors"]))
    return result["data"]


def fetch_data() -> dict[str, object]:
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=370)
    query = '''
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        pullRequests { totalCount }
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount weekday } }
          }
        }
        repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
          totalCount
          nodes {
            stargazerCount forkCount
            languages(first: 20) { edges { size node { name } } }
          }
        }
      }
    }'''
    user = graphql(query, {
        "login": USER,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    })["user"]
    repos = user["repositories"]["nodes"]
    languages: dict[str, int] = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            language = edge["node"]["name"]
            if language not in {"HTML", "CSS", "SCSS", "Less"}:
                languages[language] = languages.get(language, 0) + int(edge["size"])
    days = [day for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]
            for day in week["contributionDays"]]
    data = {
        "updated": today.isoformat(),
        "created_at": user["createdAt"],
        "followers": user["followers"]["totalCount"],
        "pull_requests": user["pullRequests"]["totalCount"],
        "repositories": user["repositories"]["totalCount"],
        "stars": sum(repo["stargazerCount"] for repo in repos),
        "forks": sum(repo["forkCount"] for repo in repos),
        "contributions": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "languages": dict(sorted(languages.items(), key=lambda item: item[1], reverse=True)),
        "calendar": days,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def load_data() -> dict[str, object]:
    try:
        return fetch_data()
    except Exception as error:  # Preserve the last good render during transient API failures.
        print(f"warning: GitHub data refresh failed: {error}")
        if DATA_FILE.exists():
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        raise


def render_header() -> None:
    body = f'''
  <defs>
    <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{CYAN}" stop-opacity="0"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
  </defs>
  <rect class="scan" width="220" height="330" fill="url(#scan)"/>
  <circle cx="30" cy="28" r="4" fill="{RED}"/><circle cx="45" cy="28" r="4" fill="{AMBER}"/><circle cx="60" cy="28" r="4" fill="{TEAL}"/>
  <text x="88" y="34" class="mono" font-size="12" fill="{MUTED}">guilherme@ops-console: ~/profile</text>
  <path d="M30 58H850" stroke="{LINE}"/>
  <text x="44" y="96" class="mono" font-size="14" fill="{TEAL}">$ identity --resolve</text>
  <text x="44" y="157" class="ui" font-size="48" font-weight="800" fill="{TEXT}">Guilherme Aires</text>
  <text x="47" y="190" class="mono" font-size="15" fill="{CYAN}">SOFTWARE ENGINEERING STUDENT // BUILDER</text>
  <text x="47" y="228" class="mono" font-size="13" fill="{MUTED}">NOC · DEVOPS · BACKEND · PRODUCT ENGINEERING</text>
  <text x="47" y="264" class="mono" font-size="13" fill="{TEXT}">Building useful systems across product, cloud and operations.</text>
  <text x="47" y="299" class="mono" font-size="12" fill="{TEAL}">STATUS: ONLINE</text><rect x="169" y="287" width="9" height="16" fill="{CYAN}" class="blink"/>
  <g transform="translate(681 91)">
    <path d="M0 90L78 44l78 46-78 46Z" fill="{PANEL_2}" stroke="{LINE}"/>
    <path d="M78 44V0l78 45v45Z" fill="#102536" stroke="{CYAN}"/>
    <path d="M78 44V0L0 45v45Z" fill="#0b1c28" stroke="{TEAL}"/>
    <path d="M78 68v68" stroke="{AMBER}" stroke-width="2"/>
    <circle cx="78" cy="68" r="8" fill="{CYAN}"/><circle cx="78" cy="68" r="18" fill="none" stroke="{CYAN}" opacity=".35"/>
  </g>'''
    write("header.svg", shell(880, 330, "Guilherme Aires", "Software engineering, product and operations profile", body))


def section_asset(name: str, label: str, command: str) -> None:
    body = f'''<text x="28" y="35" class="mono" font-size="12" fill="{TEAL}">$ {esc(command)}</text>
  <text x="28" y="76" class="ui" font-size="25" font-weight="800" fill="{TEXT}">{esc(label)}</text>
  <path d="M28 92H852" stroke="{LINE}"/><path d="M28 92H174" stroke="{CYAN}" stroke-width="3"/>'''
    write(name, shell(880, 110, label, label, body))


def link_asset(name: str, label: str, code: str, accent: str) -> None:
    body = f'''<rect x="10" y="10" width="200" height="72" rx="12" fill="{PANEL}" stroke="{LINE}"/>
  <rect x="22" y="25" width="42" height="42" rx="9" fill="{accent}" opacity=".15" stroke="{accent}"/>
  <text x="43" y="52" text-anchor="middle" class="mono" font-size="16" font-weight="800" fill="{accent}">{esc(code)}</text>
  <text x="76" y="42" class="mono" font-size="11" fill="{MUTED}">OPEN CHANNEL</text>
  <text x="76" y="62" class="mono" font-size="14" font-weight="700" fill="{TEXT}">{esc(label)}</text>'''
    write(f"links/{name}.svg", shell(220, 92, label, f"Open {label}", body))


def render_stats(data: dict[str, object]) -> None:
    metrics = [
        ("REPOSITORIES", data["repositories"]), ("STARS", data["stars"]),
        ("CONTRIBUTIONS / 12M", data["contributions"]),
    ]
    cards = []
    for index, (label, value) in enumerate(metrics):
        x, y = 28 + index * 282, 68
        cards.append(f'''<g transform="translate({x} {y})"><rect width="260" height="70" rx="10" fill="{PANEL}" stroke="{LINE}"/><text x="16" y="24" class="mono" font-size="10" fill="{MUTED}">{label}</text><text x="16" y="54" class="mono" font-size="25" font-weight="800" fill="{TEXT}">{value}</text><circle cx="239" cy="18" r="4" fill="{TEAL}"/></g>''')
    languages = list(data["languages"].items())[:6]
    total = sum(value for _, value in languages) or 1
    colors, bars, legend, cursor = [CYAN, PURPLE, TEAL, AMBER, BLUE, RED], [], [], 0.0
    for index, (language, size) in enumerate(languages):
        width, percent = 824 * size / total, size / total * 100
        bars.append(f'<rect x="{28 + cursor:.2f}" y="180" width="{width:.2f}" height="10" fill="{colors[index]}"/>')
        lx, ly = 30 + (index % 3) * 282, 217 + (index // 3) * 24
        legend.append(f'<circle cx="{lx}" cy="{ly - 4}" r="4" fill="{colors[index]}"/><text x="{lx + 12}" y="{ly}" class="mono" font-size="11" fill="{MUTED}">{esc(language)} {percent:.0f}%</text>')
        cursor += width
    body = f'''<text x="28" y="34" class="mono" font-size="12" fill="{TEAL}">$ telemetry --window 12m</text>
  <text x="852" y="34" text-anchor="end" class="mono" font-size="10" fill="{MUTED}">UPDATED {esc(data['updated'])}</text>
  {''.join(cards)}<text x="28" y="164" class="mono" font-size="10" fill="{MUTED}">APPLICATION LANGUAGE DISTRIBUTION</text>
  <clipPath id="bar"><rect x="28" y="180" width="824" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">{''.join(bars)}</g>{''.join(legend)}'''
    write("stats.svg", shell(880, 276, "GitHub telemetry", "Repository and language statistics", body))


def render_city(data: dict[str, object]) -> None:
    days = data.get("calendar", [])[-371:]
    maximum = max((int(day["contributionCount"]) for day in days), default=1) or 1
    dated_days = [(dt.date.fromisoformat(day["date"]), day) for day in days]
    first_date = min((date for date, _ in dated_days), default=dt.date.today())
    active_days = sum(1 for _, day in dated_days if int(day["contributionCount"]) > 0)
    busiest_date, busiest = max(
        ((date, int(day["contributionCount"])) for date, day in dated_days),
        key=lambda item: item[1],
        default=(dt.date.today(), 0),
    )

    stars = []
    for index in range(46):
        x = 468 + ((index * 83) % 344)
        y = 102 + ((index * 47) % 150)
        radius = .7 + (index % 3) * .25
        stars.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{TEXT}" opacity="{.28 + (index % 5) * .1:.2f}"/>')

    buildings = []
    for date, day in dated_days:
        count = int(day["contributionCount"])
        week = (date - first_date).days // 7
        weekday = int(day.get("weekday", date.weekday()))
        cx = 92 + (week + weekday) * 12.5
        cy = 282 + (week - weekday) * 6.25
        ratio = count / maximum
        height = 10 if count == 0 else 17 + 78 * ratio ** .52
        roof = "#123246" if count == 0 else BLUE if ratio < .18 else TEAL if ratio < .45 else CYAN
        left = "#0b2231" if count == 0 else "#123047"
        right = "#071a27" if count == 0 else "#0b2233"
        top_y = cy - height
        windows = []
        if count:
            levels = max(1, int((height - 8) // 8))
            for level in range(levels):
                wy = cy - 7 - level * 8
                if (date.toordinal() + level) % 3:
                    windows.append(f'<path d="M{cx - 9:.1f} {wy:.1f}l4 2v3l-4 -2Z" fill="{CYAN}" opacity=".75"/>')
                if (date.toordinal() + level) % 4:
                    windows.append(f'<path d="M{cx + 5:.1f} {wy + 2:.1f}l4 -2v3l-4 2Z" fill="{TEAL}" opacity=".7"/>')
        buildings.append((cy, f'''<g>
  <path d="M{cx - 12.5:.1f} {cy:.1f}L{cx:.1f} {cy + 6.25:.1f}L{cx + 12.5:.1f} {cy:.1f}L{cx:.1f} {cy - 6.25:.1f}Z" fill="#07111a" stroke="{LINE}" stroke-width=".45"/>
  <path d="M{cx - 12.5:.1f} {top_y:.1f}L{cx:.1f} {top_y + 6.25:.1f}V{cy + 6.25:.1f}L{cx - 12.5:.1f} {cy:.1f}Z" fill="{left}"/>
  <path d="M{cx:.1f} {top_y + 6.25:.1f}L{cx + 12.5:.1f} {top_y:.1f}V{cy:.1f}L{cx:.1f} {cy + 6.25:.1f}Z" fill="{right}"/>
  <path d="M{cx - 12.5:.1f} {top_y:.1f}L{cx:.1f} {top_y - 6.25:.1f}L{cx + 12.5:.1f} {top_y:.1f}L{cx:.1f} {top_y + 6.25:.1f}Z" fill="{roof}"/>{''.join(windows)}</g>'''))

    body = f'''<defs>
    <linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#071a2b"/><stop offset=".55" stop-color="#06111d"/><stop offset="1" stop-color="{BG}"/></linearGradient>
    <radialGradient id="moon"><stop stop-color="{TEXT}" stop-opacity=".22"/><stop offset="1" stop-color="{TEXT}" stop-opacity="0"/></radialGradient>
  </defs>
  <rect x="16" y="16" width="848" height="648" rx="12" fill="url(#night)"/>
  <text x="34" y="49" class="mono" font-size="12" fill="{TEAL}">$ contributions --render city --last 365d</text>
  <text x="34" y="82" class="ui" font-size="22" font-weight="800" fill="{TEXT}">CONTRIBUTION CITY</text>
  <text x="34" y="106" class="mono" font-size="11" fill="{MUTED}">one block per day · height and light reflect activity</text>
  {''.join(stars)}<circle cx="785" cy="153" r="42" fill="url(#moon)"/><circle cx="785" cy="153" r="13" fill="{TEXT}"/><circle cx="791" cy="148" r="12" fill="#071522"/>
  <path d="M68 292L430 111L825 309L455 494Z" fill="#07111a" stroke="{LINE}" opacity=".72"/>
  {''.join(item for _, item in sorted(buildings, key=lambda item: item[0]))}
  <text x="34" y="626" class="mono" font-size="11" fill="{MUTED}"><tspan fill="{CYAN}" font-weight="700">{esc(data['contributions'])}</tspan> CONTRIBUTIONS · {active_days} ACTIVE DAYS</text>
  <text x="846" y="626" text-anchor="end" class="mono" font-size="11" fill="{MUTED}">BUSIEST: {busiest_date.strftime('%b %d').upper()} · <tspan fill="{TEXT}">{busiest}</tspan></text>'''
    write("contribution-city.svg", shell(880, 680, "Contribution city", "Isometric city generated from GitHub contributions", body))


def render_project(project: tuple[object, ...]) -> None:
    slug, title, code, description, project_tags, accent, symbol = project
    tags, cursor = [], 24
    for tag in project_tags:
        width = 16 + len(tag) * 7
        tags.append(f'<rect x="{cursor}" y="171" width="{width}" height="22" rx="4" fill="{accent}" opacity=".12" stroke="{accent}"/><text x="{cursor + 8}" y="186" class="mono" font-size="9" fill="{accent}">{esc(tag)}</text>')
        cursor += width + 8
    body = f'''<rect x="14" y="14" width="412" height="192" rx="12" fill="{PANEL}" stroke="{LINE}"/>
  <path d="M14 52H426" stroke="{LINE}"/><circle cx="31" cy="33" r="4" fill="{accent}"/><text x="44" y="37" class="mono" font-size="10" fill="{MUTED}">{esc(code)}</text>
  <rect x="24" y="69" width="48" height="48" rx="11" fill="{accent}" opacity=".12" stroke="{accent}"/>
  <text x="48" y="101" text-anchor="middle" class="mono" font-size="23" font-weight="800" fill="{accent}">{esc(symbol)}</text>
  <text x="88" y="89" class="ui" font-size="18" font-weight="800" fill="{TEXT}">{esc(title)}</text>
  <text x="88" y="113" class="mono" font-size="10" fill="{accent}">OPEN REPOSITORY →</text>
  <text x="24" y="140" class="mono" font-size="11" fill="{MUTED}">{esc(description[0])}</text>
  <text x="24" y="157" class="mono" font-size="11" fill="{MUTED}">{esc(description[1])}</text>{''.join(tags)}'''
    write(f"card-{slug}.svg", shell(440, 220, str(title), " ".join(description), body))


def render_footer() -> None:
    body = f'''<path d="M24 24H856" stroke="{LINE}"/><text x="28" y="54" class="mono" font-size="11" fill="{MUTED}">guilherme@ops-console:~$</text><rect x="197" y="41" width="9" height="16" fill="{CYAN}" class="blink"/><text x="852" y="54" text-anchor="end" class="mono" font-size="10" fill="{TEAL}">CONNECTION ACTIVE</text>'''
    write("footer.svg", shell(880, 78, "Profile footer", "Connection active", body))


def main() -> None:
    data = load_data()
    render_header()
    section_asset("links.svg", "CONNECTIONS", "open secure channels")
    link_asset("linkedin", "LINKEDIN", "IN", BLUE)
    link_asset("portfolio", "PORTFOLIO", "//", PURPLE)
    link_asset("gitlab", "GITLAB", "GL", AMBER)
    link_asset("github", "GITHUB", "GH", TEXT)
    render_stats(data)
    render_city(data)
    section_asset("projects.svg", "SELECTED SYSTEMS", "ls ./projects --featured")
    for project in PROJECTS:
        render_project(project)
    section_asset("stack.svg", "TECH STACK", "inspect ./capabilities --cards")
    render_footer()
    print(f"profile assets generated for {USER} ({data['updated']})")


if __name__ == "__main__":
    main()
