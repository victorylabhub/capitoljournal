#!/usr/bin/env python3
"""Capitol Journal: static site generator.

Usage:  python3 build.py   -> writes the site to dist/
Settings in site.json; articles in content/articles/*.md (YAML front matter,
created from the newsroom panel at /admin/); institutional pages in
content/pages/*.md; state election data in data/*.json.
"""
import datetime as dt
import hashlib
import json
import shutil
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml
from zoneinfo import ZoneInfo
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
ET = ZoneInfo("America/New_York")  # Eastern Time, with daylight saving

SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
SITE["v"] = hashlib.md5(b"".join((ROOT / "static" / f).read_bytes()
                                 for f in ("site.css", "site.js"))).hexdigest()[:8]
SECTIONS = {s["slug"]: s for s in SITE["sections"]}
PHOTOS = SITE["photos"]

env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                  trim_blocks=True, lstrip_blocks=True)

MONTHS_AP = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.",
             "Sept.", "Oct.", "Nov.", "Dec."]


def ap_date(d):
    """AP style: Oct. 23, 2026."""
    return f"{MONTHS_AP[d.month - 1]} {d.day}, {d.year}"


def ap_time(d):
    d = d.astimezone(ET)
    h = d.hour % 12 or 12
    ampm = "a.m." if d.hour < 12 else "p.m."
    return f"{h}:{d.minute:02d} {ampm} ET" if d.minute else f"{h} {ampm} ET"


env.filters["ap_date"] = ap_date
env.filters["ap_time"] = ap_time


def img(key_or_path, size=1600):
    """Return src/srcset/position for a site photo key or an uploaded path."""
    if not key_or_path:
        return None
    if key_or_path in PHOTOS:
        p = PHOTOS[key_or_path]
        base = f"/static/img/photos/{key_or_path}"
        return {"src": f"{base}-{size}.webp",
                "srcset": f"{base}-800.webp 800w, {base}-1600.webp 1600w",
                "alt": p["alt"], "pos": p.get("pos", "50% 50%")}
    return {"src": key_or_path, "srcset": "", "alt": "", "pos": "50% 50%"}


env.globals["img"] = img


def parse_date(d):
    if isinstance(d, str):
        d = dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
    if isinstance(d, dt.date) and not isinstance(d, dt.datetime):
        d = dt.datetime(d.year, d.month, d.day, 9)
    if d.tzinfo is None:
        d = d.replace(tzinfo=ET)
    return d


def read_md(f):
    raw = f.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return None, raw
    _, head, body = raw.split("---", 2)
    return (yaml.safe_load(head) or {}), body.strip()


def md(text):
    return markdown.markdown(text, extensions=["extra", "sane_lists", "smarty"])


def load_articles():
    out = []
    for f in sorted((ROOT / "content" / "articles").glob("*.md")):
        m, body = read_md(f)
        if not m or m.get("draft") or m.get("section") not in SECTIONS:
            continue
        missing = [k for k in ("title", "dek", "author", "date") if not m.get(k)]
        if missing:
            raise SystemExit(f"{f.name}: missing {', '.join(missing)}")
        m["date"] = parse_date(m["date"])
        if m.get("updated"):
            m["updated"] = parse_date(m["updated"])
        m["slug"] = f.stem.split("-", 3)[-1] if f.stem[:4].isdigit() else f.stem
        m["url"] = f"/{m['section']}/{m['slug']}/"
        m["html"] = md(body)
        m["minutes"] = max(1, round(len(body.split()) / 230))
        m["sources"] = m.get("sources") or []
        m["sec"] = SECTIONS[m["section"]]
        m["photo"] = img(m.get("image"))
        if m["photo"] and m.get("image_alt"):
            m["photo"]["alt"] = m["image_alt"]
        out.append(m)
    out.sort(key=lambda a: (a.get("featured", False), a["date"]), reverse=True)
    return out


def load_pages():
    pages = {}
    for f in sorted((ROOT / "content" / "pages").glob("*.md")):
        m, body = read_md(f)
        m = m or {}
        m["slug"] = f.stem
        m["html"] = md(body)
        if m.get("updated"):
            m["updated"] = parse_date(m["updated"])
        pages[f.stem] = m
    return pages


STATE_NAMES = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California",
    "co": "Colorado", "ct": "Connecticut", "de": "Delaware", "dc": "District of Columbia",
    "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho", "il": "Illinois",
    "in": "Indiana", "ia": "Iowa", "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana",
    "me": "Maine", "md": "Maryland", "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota",
    "ms": "Mississippi", "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada",
    "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York",
    "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma", "or": "Oregon",
    "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota",
    "tn": "Tennessee", "tx": "Texas", "ut": "Utah", "vt": "Vermont", "va": "Virginia",
    "wa": "Washington", "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming",
}


def election_data():
    res = json.loads((ROOT / "data" / "results_urls.json").read_text(encoding="utf-8"))
    clo = json.loads((ROOT / "data" / "poll_closing.json").read_text(encoding="utf-8"))
    results = [{"code": c, "name": STATE_NAMES[c], "url": r["url"], "authority": r["authority"]}
               for c, r in res.items() if r.get("url") and r.get("verified")]
    results.sort(key=lambda r: r["name"])
    closing = [{"et": g["et"], "names": sorted(STATE_NAMES[c] for c in g["states"])}
               for g in clo.get("groups", []) if g.get("states")]
    return results, closing, clo.get("sources", [])


def write(path, html):
    p = DIST / path.strip("/") / "index.html" if path != "/" else DIST / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    articles = load_articles()
    pages = load_pages()
    results, closing, closing_sources = election_data()
    now = dt.datetime.now(ET)
    common = dict(site=SITE, sections=SITE["sections"], build_date=now)
    urls = ["/"]

    by_sec = {s: [a for a in articles if a["section"] == s] for s in SECTIONS}
    latest = sorted(articles, key=lambda a: a["date"], reverse=True)

    shown = articles[:5]  # lead + top stories are not repeated in the section rows
    home_sec = {s: [a for a in lst if a not in shown] for s, lst in by_sec.items()}
    write("/", env.get_template("home.html").render(
        **common, active=None, lead=articles[0] if articles else None,
        top=[a for a in articles[1:5]], latest=latest[:6], by_sec=home_sec,
        canonical="/"))

    for slug, sec in SECTIONS.items():
        tpl = "elections.html" if slug == "elections" else "section.html"
        write(f"/{slug}/", env.get_template(tpl).render(
            **common, active=slug, sec=sec, items=by_sec[slug], results=results,
            closing=closing, closing_sources=closing_sources, canonical=f"/{slug}/"))
        urls.append(f"/{slug}/")

    for a in articles:
        related = [r for r in by_sec[a["section"]] if r is not a][:4]
        if len(related) < 4:
            related += [r for r in latest if r is not a and r not in related][:4 - len(related)]
        write(a["url"], env.get_template("article.html").render(
            **common, active=a["section"], a=a, related=related, canonical=a["url"]))
        urls.append(a["url"])

    for slug, p in pages.items():
        write(f"/{slug}/", env.get_template("page.html").render(
            **common, active=None, p=p, canonical=f"/{slug}/"))
        urls.append(f"/{slug}/")

    (DIST / "404.html").write_text(env.get_template("page.html").render(
        **common, active=None, canonical=None,
        p={"title": "Page not found", "dek": "This address does not exist or has moved.",
           "html": '<p><a href="/">Go to the home page</a> or browse a section from the menu.</p>'}),
        encoding="utf-8")

    shutil.copytree(ROOT / "static", DIST / "static")
    shutil.copytree(ROOT / "admin", DIST / "admin")
    for f in ("favicon.ico",):
        if (ROOT / "static" / "img" / "brand" / f).exists():
            shutil.copy(ROOT / "static" / "img" / "brand" / f, DIST / f)

    base = f"https://{SITE['domain']}"
    items = "".join(
        f"<item><title>{esc(a['title'])}</title><link>{base}{a['url']}</link>"
        f"<guid>{base}{a['url']}</guid><pubDate>{format_datetime(a['date'])}</pubDate>"
        f"<author>{esc(SITE['email'])} ({esc(a['author'])})</author>"
        f"<category>{esc(a['sec']['name'])}</category>"
        f"<description>{esc(a['dek'])}</description></item>" for a in latest[:30])
    (DIST / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>Capitol Journal</title><link>{base}/</link>"
        f"<description>{esc(SITE['description'])}</description><language>en-us</language>"
        f"{items}</channel></rss>", encoding="utf-8")

    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n",
        encoding="utf-8")
    pre = SITE.get("prelaunch")
    (DIST / "robots.txt").write_text(
        ("User-agent: *\nDisallow: /\n" if pre else "User-agent: *\nAllow: /\nDisallow: /admin/\n")
        + f"Sitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (DIST / "_headers").write_text(
        "/*\n  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()\n"
        + ("  X-Robots-Tag: noindex\n" if pre else "")
        + "/admin/*\n  X-Robots-Tag: noindex\n"
        + "/static/*\n  Cache-Control: public, max-age=604800\n", encoding="utf-8")
    print(f"OK dist/: {len(urls)} pages, {len(articles)} articles, "
          f"{len(results)} official results links, {len(closing)} poll-closing groups")


if __name__ == "__main__":
    build()
