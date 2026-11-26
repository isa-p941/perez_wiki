"""Gathers my favorite music from a YouTube Music playlist for the about page.

Like its neighbor letterboxd.py, it visits once, collects each track's
title, artist and cover, and keeps the results for an hour so YouTube is not
asked on every visit. A YouTube Music playlist is an ordinary YouTube playlist
underneath, and YouTube leaves a public feed at the door of every public or
unlisted one, so no key or account is needed to read it.
"""

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_cache = {"data": None, "ts": 0}
_CACHE_TTL = 3600

# The "list=" value from the playlist's share link. The playlist must be
# public or unlisted; a private one has no feed.
_PLAYLIST_ID = "PLQb9Q7TTD4Ys"
_FEED_URL = "https://www.youtube.com/feeds/videos.xml"
_WATCH_URL = "https://music.youtube.com/watch"
# Matches letterboxd._MAX_FILMS so both lists on the about page line up.
_MAX_TRACKS = 5

# The feed's XML namespaces, so its tags can be found by name.
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def _fetch_feed(playlist_id):
    """Fetches a playlist's public feed.

    Args:
        playlist_id: The playlist's ID, such as "PL...".

    Returns:
        The feed's raw XML as bytes.

    Raises:
        urllib.error.URLError: If YouTube is unreachable, refuses us, or
            takes longer than eight seconds to answer.
    """
    url = f"{_FEED_URL}?{urllib.parse.urlencode({'playlist_id': playlist_id})}"
    with urllib.request.urlopen(url, timeout=8) as resp:
        return resp.read()


def _artist(name):
    """Works out who made a track.

    YouTube Music files each artist's songs under an automatic channel named
    "<Artist> - Topic", so the suffix is trimmed away to leave the name.

    Args:
        name: The track's channel name from the feed, or None.

    Returns:
        The artist's name, or None if the feed does not say.
    """
    if not name:
        return None
    return name.removesuffix(" - Topic").strip()


def _parse_feed(xml):
    """Picks the first few tracks out of a playlist feed.

    Each link opens the single track on its own, not the whole playlist.

    Args:
        xml: The feed's XML, as bytes or a string.

    Returns:
        A list of up to _MAX_TRACKS dicts, in playlist order, each with a
        "title", an "artist" (or None), a YouTube Music "url", and a "cover"
        image URL (or None).
    """
    root = ET.fromstring(xml)
    tracks = []
    for entry in root.findall("atom:entry", _NS):
        title = entry.findtext("atom:title", namespaces=_NS)
        video_id = entry.findtext("yt:videoId", namespaces=_NS)
        if not title or not video_id:
            continue
        thumb = entry.find("media:group/media:thumbnail", _NS)
        query = urllib.parse.urlencode({"v": video_id})
        tracks.append({
            "title": title.strip(),
            "artist": _artist(entry.findtext("atom:author/atom:name", namespaces=_NS)),
            "url": f"{_WATCH_URL}?{query}",
            "cover": thumb.get("url") if thumb is not None else None,
        })
        if len(tracks) == _MAX_TRACKS:
            break
    return tracks


def get_favorite_music():
    """Returns my favorite tracks, with covers and listening links.

    Results are kept for an hour. If YouTube turns us away or comes back
    empty, the last good results are served instead, and if there are none,
    the page shows its own hand-written list.

    Returns:
        A list of up to _MAX_TRACKS dicts, each with a "title", an "artist"
        (or None), a YouTube Music "url" and a "cover" URL (or None). Empty
        when nothing could be gathered.
    """
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    try:
        tracks = _parse_feed(_fetch_feed(_PLAYLIST_ID))
        if not tracks:
            raise ValueError("no tracks parsed")
        _cache["data"] = tracks
        _cache["ts"] = now
    except Exception:
        tracks = _cache["data"] or []

    return tracks
