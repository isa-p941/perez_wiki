"""Gathers my favorite films from Letterboxd for the about page.

It visits the list, collects what it finds, and keeps the results for an
hour so Letterboxd is not asked on every visit. Posters come from TMDB, since
Letterboxd keeps its own hidden behind JavaScript.
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

_cache = {"data": None, "ts": 0}
_CACHE_TTL = 3600

_SITE = "https://letterboxd.com"
_LIST_URL = _SITE + "/issaisa/list/wiki_favorites/"
_TMDB_BASE = "https://api.themoviedb.org/3"
_TMDB_IMG = "https://image.tmdb.org/t/p/w185"
# Matches youtube_music._MAX_TRACKS so both lists on the about page line up.
_MAX_FILMS = 4
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"


def _fetch(url, headers=None):
    """Fetches a URL and hands back whatever the server says.

    Args:
        url: The address to visit.
        headers: Optional request headers, such as a User-Agent.

    Returns:
        The raw response body as bytes.

    Raises:
        urllib.error.URLError: If the server is unreachable, refuses us, or
            takes longer than eight seconds to answer.
    """
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.read()


def _tmdb_poster(title, year):
    """Looks up a film's poster on TMDB.

    Without a TMDB_API_KEY in the environment there is nothing to ask with,
    so the film simply goes without a poster.

    Args:
        title: The film's title.
        year: The release year, used to tell remakes apart. May be None.

    Returns:
        The full URL of the best-matching poster, or None if there is no key
        or no match.

    Raises:
        urllib.error.URLError: If TMDB cannot be reached.
    """
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
    """Picks the films out of a Letterboxd list page.

    Letterboxd has used two layouts over the years, one tagging films with
    data-film-* attributes and the other with data-item-*. Both are
    understood here, and a film that appears twice is counted once.

    Args:
        html: The list page's HTML, as bytes or a string.

    Returns:
        A list of dicts, in list order, each with a "title", a "year" (or
        None), and the film's Letterboxd "url".
    """
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
    """Returns my favorite films, with posters where they can be found.

    Results are kept for an hour. If Letterboxd turns us away or comes back
    empty, the last good results are served instead, and if there are none,
    the page gets an empty list.

    Returns:
        A list of dicts, each with a "title", a "year" (or None), a
        Letterboxd "url", and a "poster" URL (or None).
    """
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    try:
        html = _fetch(_LIST_URL, {"User-Agent": _UA, "Accept": "text/html"})
        films = _parse_list(html)[:_MAX_FILMS]
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
