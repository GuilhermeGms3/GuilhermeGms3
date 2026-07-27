#!/usr/bin/env python3
"""Generate a self-hosted GitHub activity card."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
OUTPUT = Path("assets/github-activity.svg")
COLORS = [
    "#00e5ff",
    "#7c3aed",
    "#2ea043",
    "#f59e0b",
    "#f43f5e",
    "#3b82f6",
]


def api_get(path: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-activity-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API_ROOT}{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def generate() -> str:
    username = os.getenv("GITHUB_REPOSITORY_OWNER", "GuilhermeGms3")
    user = api_get(f"/users/{username}")
    repos = api_get(f"/users/{username}/repos?per_page=100&type=owner&sort=pushed")

    if not isinstance(user, dict) or not isinstance(repos, list):
        raise RuntimeError("Unexpected response from GitHub API")

    owned_repos = [
        repo
        for repo in repos
        if not repo.get("fork") and repo.get("name") != username
    ]
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in owned_repos)
    forks = sum(int(repo.get("forks_count", 0)) for repo in owned_repos)

    language_bytes: dict[str, int] = {}
    for repo in owned_repos:
        languages = api_get(f"/repos/{username}/{repo['name']}/languages")
        if not isinstance(languages, dict):
            continue
        for language, size in languages.items():
            language_bytes[language] = language_bytes.get(language, 0) + int(size)

    top_languages = sorted(
        language_bytes.items(), key=lambda item: item[1], reverse=True
    )[:6]
    language_total = sum(size for _, size in top_languages) or 1
    recent = [repo["name"] for repo in owned_repos[:3]]

    metrics = [
        ("REPOSITORIES", user.get("public_repos", 0)),
        ("STARS", stars),
        ("FOLLOWERS", user.get("followers", 0)),
        ("FORKS", forks),
    ]

    metric_cards = []
    for index, (label, value) in enumerate(metrics):
        x = 28 + index * 218
        metric_cards.append(
            f"""
    <g transform="translate({x} 78)">
      <rect width="196" height="78" rx="13" class="metric-card"/>
      <text x="18" y="27" class="metric-label">{escape(label)}</text>
      <text x="18" y="59" class="metric-value">{escape(value)}</text>
    </g>"""
        )

    bar_parts = []
    legend_parts = []
    cursor = 0.0
    for index, (language, size) in enumerate(top_languages):
        width = 844 * size / language_total
        color = COLORS[index % len(COLORS)]
        bar_parts.append(
            f'<rect x="{28 + cursor:.2f}" y="197" width="{width:.2f}" '
            f'height="10" fill="{color}"/>'
        )
        legend_x = 30 + (index % 3) * 285
        legend_y = 231 + (index // 3) * 25
        percent = size / language_total * 100
        percent_label = f"{percent:.1f}" if percent < 1 else f"{percent:.0f}"
        legend_parts.append(
            f'<circle cx="{legend_x}" cy="{legend_y - 4}" r="4" fill="{color}"/>'
            f'<text x="{legend_x + 12}" y="{legend_y}" class="legend">'
            f"{escape(language)} {percent_label}%</text>"
        )
        cursor += width

    recent_text = "  /  ".join(recent) if recent else "building the next project"

    return f"""<svg width="900" height="300" viewBox="0 0 900 300" fill="none"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{escape(username)} GitHub activity</title>
  <desc id="desc">Self-hosted repository, follower and language statistics.</desc>
  <style>
    .root {{ fill: #070b12; stroke: #263241; stroke-width: 1.5; }}
    .metric-card {{ fill: #0d141e; stroke: #263241; }}
    .heading {{ fill: #f0f6fc; font: 700 20px "Fira Code", Consolas, monospace; }}
    .prompt {{ fill: #00e5ff; font: 700 13px "Fira Code", Consolas, monospace; }}
    .muted {{ fill: #7d8b99; font: 500 12px "Fira Code", Consolas, monospace; }}
    .metric-label {{ fill: #7d8b99; font: 700 11px "Fira Code", Consolas, monospace; letter-spacing: 1px; }}
    .metric-value {{ fill: #f0f6fc; font: 800 25px "Fira Code", Consolas, monospace; }}
    .legend {{ fill: #b8c4ce; font: 600 12px "Fira Code", Consolas, monospace; }}
    .status {{ fill: #39d353; font: 700 11px "Fira Code", Consolas, monospace; }}
    .scan {{ animation: scan 4s linear infinite; opacity: .28; }}
    .pulse {{ animation: pulse 1.8s ease-in-out infinite; }}
    @keyframes scan {{ from {{ transform: translateX(-180px); }} to {{ transform: translateX(1080px); }} }}
    @keyframes pulse {{ 50% {{ opacity: .35; }} }}
  </style>
  <rect x="1" y="1" width="898" height="298" rx="18" class="root"/>
  <rect class="scan" x="0" y="1" width="180" height="298" fill="url(#scanGradient)"/>

  <text x="28" y="37" class="prompt">$ github telemetry --owner {escape(username)}</text>
  <text x="28" y="63" class="heading">Repository Activity</text>
  <circle cx="813" cy="40" r="5" fill="#39d353" class="pulse"/>
  <text x="826" y="44" class="status">SELF-HOSTED</text>

  {''.join(metric_cards)}

  <text x="28" y="184" class="muted">LANGUAGE DISTRIBUTION</text>
  <clipPath id="barClip"><rect x="28" y="197" width="844" height="10" rx="5"/></clipPath>
  <g clip-path="url(#barClip)">{''.join(bar_parts)}</g>
  {''.join(legend_parts)}

  <text x="28" y="284" class="muted">recent signals: {escape(recent_text)}</text>

  <defs>
    <linearGradient id="scanGradient" x1="0" y1="0" x2="180" y2="0">
      <stop stop-color="#00e5ff" stop-opacity="0"/>
      <stop offset=".5" stop-color="#00e5ff"/>
      <stop offset="1" stop-color="#7c3aed" stop-opacity="0"/>
    </linearGradient>
  </defs>
</svg>
"""


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generate(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
