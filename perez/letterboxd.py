import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_cache = {"data": None, "ts": 0}
_CACHE_TTL = 3600

_RSS_URL = "https://letterboxd.com/issaisa/list/wiki_favorites/rss/"
_TMDB_BASE = "https://api.themoviedb.org/3"
_TMDB_IMG = "https://image.tmdb.org/t/p/w185"


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


def get_favorite_films():
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    try:
        raw = _fetch(_RSS_URL, {"User-Agent": "Mozilla/5.0 (compatible; perez.wiki/1.0)"})
        root = ET.fromstring(raw)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []

        films = []
        for item in items:
            title = (item.findtext("{*}filmTitle") or item.findtext("title") or "").strip()
            year = (item.findtext("{*}filmYear") or "").strip() or None
            link = item.findtext("link") or None
            try:
                poster = _tmdb_poster(title, year)
            except Exception:
                poster = None
            films.append({"title": title, "year": year, "url": link, "poster": poster})

        _cache["data"] = films
        _cache["ts"] = now
    except Exception:
        films = _cache["data"] or []

    return films
