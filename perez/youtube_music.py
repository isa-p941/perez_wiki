"""Gathers my favorite music from a YouTube Music playlist for the about page.

The playlist is the hive and this module the beekeeper, much like its
neighbor letterboxd.py: it visits once, collects each track's title, artist
and cover, and keeps a jar of it for an hour so YouTube is not disturbed on
every visit. A YouTube Music playlist is an ordinary YouTube playlist
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


def _parse_feed(xml, playlist_id):
    """Picks the tracks out of a playlist feed.

    Args:
        xml: The feed's XML, as bytes or a string.
        playlist_id: The playlist's ID, so each link opens inside it.

    Returns:
        A list of dicts, in playlist order, each with a "title", an "artist"
        (or None), a YouTube Music "url", and a "cover" image URL (or None).
    """
    root = ET.fromstring(xml)
    tracks = []
    for entry in root.findall("atom:entry", _NS):
        title = entry.findtext("atom:title", namespaces=_NS)
        video_id = entry.findtext("yt:videoId", namespaces=_NS)
        if not title or not video_id:
            continue
        thumb = entry.find("media:group/media:thumbnail", _NS)
        query = urllib.parse.urlencode({"v": video_id, "list": playlist_id})
        tracks.append({
            "title": title.strip(),
            "artist": _artist(entry.findtext("atom:author/atom:name", namespaces=_NS)),
            "url": f"{_WATCH_URL}?{query}",
            "cover": thumb.get("url") if thumb is not None else None,
        })
    return tracks


def get_favorite_music():
    """Returns my favorite tracks, with covers and listening links.

    A jar of results is kept for an hour. If YouTube turns us away or comes
    back empty, the last good jar is served instead, and if there is none,
    the page shows its own hand-written list.

    Returns:
        A list of dicts, each with a "title", an "artist" (or None), a
        YouTube Music "url" and a "cover" URL (or None). Empty when nothing
        could be gathered.
    """
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    try:
        tracks = _parse_feed(_fetch_feed(_PLAYLIST_ID), _PLAYLIST_ID)
        if not tracks:
            raise ValueError("no tracks parsed")
        _cache["data"] = tracks
        _cache["ts"] = now
    except Exception:
        tracks = _cache["data"] or []

    return tracks
