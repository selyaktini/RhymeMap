"""Look lyrics up in LRCLIB.

Captions are the ideal source -- one fetch gives lyrics *and* word timings --
but most music videos do not publish any. That is the single reason "analyse any
song from a link" used to fail: not a bug, an absence.

LRCLIB (https://lrclib.net) fills it. It is a free, open, key-less database of
synced lyrics, contributed by the people using LRC-aware music players. For a
song with no captions it is usually the only source of timing that exists, and
for a song whose only captions are machine transcription it is a *better*
source: real lyrics, correctly broken into lines, instead of an ASR guess at
someone rapping.

Only the standard library is used. Adding `requests` for four GETs would put a
dependency in the core path for nothing.

The network is reached through one injectable function, ``fetch``. Every
decision around it -- building the query, scoring candidates, choosing between
synced and plain -- is pure, and tested without touching the network.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

API_ROOT = "https://lrclib.net/api"

# LRCLIB asks clients to identify themselves and link to the project.
USER_AGENT = "RhymeMapper/2.1 (https://github.com/yahyabmo/RhymeMap)"

TIMEOUT = 12.0

# Past this the two are different songs however alike the titles look.
_DURATION_TOLERANCE = 18.0

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")


class LookupError_(Exception):
    """Raised when LRCLIB cannot be reached or answers unusably."""


@dataclass(frozen=True)
class Match:
    """One LRCLIB record."""

    track: str
    artist: str
    album: str
    duration: float
    plain: str
    synced: str
    instrumental: bool = False

    @property
    def has_synced(self) -> bool:
        return bool(self.synced.strip())

    @property
    def has_plain(self) -> bool:
        return bool(self.plain.strip())


def normalise(text: str) -> str:
    """Fold a name to the form two spellings of it will share."""
    lowered = _PUNCT.sub(" ", (text or "").lower())
    return _SPACE.sub(" ", lowered).strip()


def _token_overlap(left: str, right: str) -> float:
    """Jaccard overlap of word sets, which tolerates word order and extras."""
    a, b = set(normalise(left).split()), set(normalise(right).split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_match(record: Match, track: str, artist: str, duration: float = 0.0) -> float:
    """How well a record answers the query. Higher is better; 0 disqualifies.

    Weighted towards the track name, because the artist is the field most often
    wrong on YouTube: it is frequently a channel name ("EminemMusic"), a label,
    or the uploader of a re-post.
    """
    title_score = _token_overlap(record.track, track)
    if title_score == 0.0:
        return 0.0

    artist_score = _token_overlap(record.artist, artist) if artist else 0.0

    score = title_score * 0.6 + artist_score * 0.25

    # Duration is the strongest signal available that two records are the same
    # recording, when both sides know it.
    if duration > 0 and record.duration > 0:
        gap = abs(record.duration - duration)
        if gap > _DURATION_TOLERANCE:
            score *= 0.35
        else:
            score += 0.15 * (1.0 - gap / _DURATION_TOLERANCE)

    if record.has_synced:
        score += 0.08         # prefer a record that can drive playback
    if record.instrumental:
        score = 0.0           # nothing to analyse

    return score


def _record_from(payload: dict) -> Match:
    return Match(
        track=str(payload.get("trackName") or payload.get("name") or ""),
        artist=str(payload.get("artistName") or ""),
        album=str(payload.get("albumName") or ""),
        duration=float(payload.get("duration") or 0),
        plain=str(payload.get("plainLyrics") or ""),
        synced=str(payload.get("syncedLyrics") or ""),
        instrumental=bool(payload.get("instrumental")),
    )


def fetch(url: str) -> str:
    """GET a URL and return its body. The only impure function in this module."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return ""
        raise LookupError_(f"LRCLIB answered {exc.code}") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise LookupError_(f"could not reach lrclib.net ({exc})") from exc


def build_get_url(track: str, artist: str, album: str = "", duration: float = 0.0) -> str:
    query = {"track_name": track, "artist_name": artist}
    if album:
        query["album_name"] = album
    if duration > 0:
        query["duration"] = str(int(round(duration)))
    return f"{API_ROOT}/get?{urllib.parse.urlencode(query)}"


def build_search_url(track: str, artist: str = "") -> str:
    # The fielded form is more precise, but it needs the artist to be right.
    # Without one, a free-text query over both fields does better.
    if artist:
        query = {"track_name": track, "artist_name": artist}
    else:
        query = {"q": track}
    return f"{API_ROOT}/search?{urllib.parse.urlencode(query)}"


def _parse_records(body: str) -> list[Match]:
    if not body.strip():
        return []
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise LookupError_(f"LRCLIB returned something that is not JSON: {exc}") from exc

    if isinstance(payload, dict):
        if payload.get("statusCode") == 404 or payload.get("code") == 404:
            return []
        payload = [payload]
    if not isinstance(payload, list):
        return []

    return [_record_from(item) for item in payload if isinstance(item, dict)]


def best_match(records: list[Match], track: str, artist: str,
               duration: float = 0.0, minimum: float = 0.30) -> Match | None:
    """The highest-scoring record, or None when nothing is close enough."""
    scored = [(score_match(record, track, artist, duration), record) for record in records]
    scored = [pair for pair in scored if pair[0] >= minimum]
    if not scored:
        return None
    return max(scored, key=lambda pair: pair[0])[1]


def lookup(track: str, artist: str = "", duration: float = 0.0, album: str = "",
           fetcher=None) -> Match | None:
    """Find a song's lyrics. Exact endpoint first, then a search.

    ``/api/get`` matches on all four fields at once and is the cheapest hit when
    the metadata is clean. It misses whenever the duration is off -- and a
    YouTube duration routinely is, because the video has an intro, an outro, or
    a tacked-on music-video skit that the release does not. So a miss there is
    normal, not an error, and the search is the real path.
    """
    track = (track or "").strip()
    if not track:
        return None
    artist = (artist or "").strip()

    # Resolved here rather than as a default argument: a default binds the
    # function object at import time, so `fetch` could never afterwards be
    # replaced - not by a test, and not by anyone wanting to route it through a
    # cache or a proxy of their own.
    if fetcher is None:
        fetcher = fetch

    if artist:
        exact = _parse_records(fetcher(build_get_url(track, artist, album, duration)))
        if exact and not exact[0].instrumental:
            return exact[0]

    candidates = _parse_records(fetcher(build_search_url(track, artist)))
    found = best_match(candidates, track, artist, duration)
    if found is not None:
        return found

    # Last try: drop the artist and search the title alone. Rescue for the case
    # the artist field was a channel name that matches nothing.
    if artist:
        candidates = _parse_records(fetcher(build_search_url(track)))
        return best_match(candidates, track, artist, duration)

    return None
