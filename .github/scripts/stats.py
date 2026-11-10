"""Render the profile stats and top-languages cards as static SVGs.

Runs in GitHub Actions with the workflow's GITHUB_TOKEN; no third-party service.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "ArmanAdilMangat")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
HIDE = {"HTML", "CSS", "Jupyter Notebook"}

BG, BORDER, TITLE, TEXT, ICON = "#1a1b27", "#2a2e3f", "#70a5fd", "#a9b1d6", "#bf91f3"
LANG_COLORS = {"Python": "#3572A5", "C++": "#f34b7d", "C": "#555555", "JavaScript": "#f1e05a",
               "TypeScript": "#3178c6", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051",
               "MicroPython": "#3572A5", "Prolog": "#74283c", "HTML": "#e34c26", "CSS": "#663399"}


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": USER,
        **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search_count(kind, q):
    return api("/search/%s?per_page=1&q=%s" % (kind, urllib.parse.quote(q)))["total_count"]


def collect():
    repos, page = [], 1
    while True:
        batch = api("/users/%s/repos?type=owner&per_page=100&page=%d" % (USER, page))
        repos += [r for r in batch if not r["fork"]]
        if len(batch) < 100:
            break
        page += 1
    langs = {}
    for r in repos:
        for name, size in api("/repos/%s/languages" % r["full_name"]).items():
            langs[name] = langs.get(name, 0) + size
    return {
        "repos": len(repos),
        "stars": sum(r["stargazers_count"] for r in repos),
        "commits": search_count("commits", "author:%s" % USER),
        "prs": search_count("issues", "author:%s type:pr" % USER),
        "issues": search_count("issues", "author:%s type:issue" % USER),
        "langs": langs,
    }


def card(width, height, title, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
            'role="img" aria-label="%s"><style>.t{font:600 18px \'Segoe UI\',Ubuntu,sans-serif;fill:%s}'
            '.l{font:400 14px \'Segoe UI\',Ubuntu,sans-serif;fill:%s}.v{font:700 14px \'Segoe UI\',Ubuntu,sans-serif;fill:%s}</style>'
            '<rect x="0.5" y="0.5" rx="4.5" width="%d" height="%d" fill="%s" stroke="%s"/>'
            '<text x="25" y="35" class="t">%s</text>%s</svg>') % (
        width, height, width, height, escape(title), TITLE, TEXT, TEXT,
        width - 1, height - 1, BG, BORDER, escape(title), body)


def stats_svg(s):
    rows = [("Public repositories", s["repos"]), ("Total stars", s["stars"]),
            ("Commits (public, all time)", s["commits"]), ("Languages used", len(s["langs"]))]
    body = "".join('<circle cx="31" cy="%d" r="4" fill="%s"/><text x="45" y="%d" class="l">%s</text>'
                   '<text x="330" y="%d" class="v" text-anchor="end">%s</text>'
                   % (64 + i * 25, ICON, 69 + i * 25, escape(k), 69 + i * 25, v) for i, (k, v) in enumerate(rows))
    return card(355, 170, "%s's GitHub Stats" % USER.replace("ArmanAdilMangat", "Arman Adil Mangat"), body)


def langs_svg(langs):
    top = sorted(((k, v) for k, v in langs.items() if k not in HIDE), key=lambda x: -x[1])[:6]
    total = sum(v for _, v in top) or 1
    x, bar = 25, ""
    for name, v in top:
        w = 250 * v / total
        bar += '<rect x="%.2f" y="55" width="%.2f" height="8" fill="%s"/>' % (x, w, LANG_COLORS.get(name, "#858585"))
        x += w
    legend = ""
    for i, (name, v) in enumerate(top):
        cx, cy = 25 + (i % 2) * 140, 90 + (i // 2) * 25
        legend += ('<circle cx="%d" cy="%d" r="5" fill="%s"/><text x="%d" y="%d" class="l">%s %.1f%%</text>'
                   % (cx + 5, cy - 5, LANG_COLORS.get(name, "#858585"), cx + 15, cy, escape(name), 100 * v / total))
    return card(300, 165, "Most Used Languages", '<clipPath id="c"><rect x="25" y="55" width="250" height="8" rx="4"/></clipPath>'
                '<g clip-path="url(#c)">%s</g>%s' % (bar, legend))


if __name__ == "__main__":
    data = json.load(open(os.environ["STATS_FIXTURE"])) if os.environ.get("STATS_FIXTURE") else collect()
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8").write(stats_svg(data))
    open(os.path.join(OUT, "top-langs.svg"), "w", encoding="utf-8").write(langs_svg(data["langs"]))
    print(json.dumps({k: v for k, v in data.items() if k != "langs"}))
