import json
import os
import re
import time
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

_cache = {"data": None, "ts": 0}
_CACHE_TTL = 3600

_LIST_URL = "https://letterboxd.com/issaisa/list/wiki_favorites/"
_SITE = "https://letterboxd.com"
_TMDB_BASE = "https://api.themoviedb.org/3"
_TMDB_IMG = "https://image.tmdb.org/t/p/w185"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"


def _fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.read()


def _tmdb_poster(title, year):
    key = os.environ.get("TMDB_API_KEY")
    if not key:
        return None
    params = {"api_key": key, "query": title}
    if year:
        params["year"] = year
    url = f"{_TMDB_BASE}/search/movie?{urllib.parse.urlencode(params)}"
    data = json.loads(_fetch(url))
    results = data.get("results", [])
    if results and results[0].get("poster_path"):
        return _TMDB_IMG + results[0]["poster_path"]
    return None


def _parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    films = []
    seen = set()
    # Letterboxd has used both data-film-* and data-item-* attributes
    for el in soup.select("[data-item-link], [data-target-link]"):
        link = el.get("data-item-link") or el.get("data-target-link")
        if not link or link in seen:
            continue
        seen.add(link)

        title = el.get("data-film-name")
        year = el.get("data-film-release-year")
        if not title:
            name = el.get("data-item-name") or ""
            m = re.match(r"^(.*?)\s*\((\d{4})\)$", name)
            title, year = (m.group(1), m.group(2)) if m else (name, year)
        if not title:
            img = el.find("img")
            title = img.get("alt", "") if img else ""
        if not title:
            continue
        films.append({
            "title": title.strip(),
            "year": year or None,
            "url": _SITE + link,
        })
    return films


def get_favorite_films():
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    try:
        html = _fetch(_LIST_URL, {"User-Agent": _UA, "Accept": "text/html"})
        films = _parse_list(html)
        for film in films:
            try:
                film["poster"] = _tmdb_poster(film["title"], film["year"])
            except Exception:
                film["poster"] = None
        if not films:
            raise ValueError("no films parsed")
        _cache["data"] = films
        _cache["ts"] = now
    except Exception:
        films = _cache["data"] or []

    return films
