"""Read a YouTube video's metadata and captions.

Audio is deliberately never downloaded. The viewer embeds YouTube's own player
and drives the highlight from its clock, which keeps playback on the platform
licensed to serve it, avoids shipping copyrighted audio, and costs no bandwidth.

Two things here exist because of how YouTube behaves rather than how it is
documented:

* **Client rotation.** YouTube serves different payloads to its Android app, its
  TV interface and its website, and blocks them independently. A request refused
  for one client often succeeds for another, so a failure is retried across
  clients before being reported. The list is intersected with the clients the
  installed yt-dlp actually knows, so a version change can never make this pass
  a name yt-dlp rejects.
* **oEmbed fallback.** When extraction is blocked outright, YouTube's public
  oEmbed endpoint still returns the title and the channel. That is enough to
  look the song up in a lyrics database, so a blocked extraction degrades to a
  lyrics-only result instead of failing.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, urlparse

# youtu.be/ID, /watch?v=ID, /embed/ID, /shorts/ID, /live/ID
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_PREFIXES = ("/embed/", "/shorts/", "/live/", "/v/")

# Caption formats in order of preference: json3 carries per-word offsets.
_FORMAT_PREFERENCE = ("json3", "srv3", "vtt", "srv1")

# Tried in order. The empty tuple means "whatever yt-dlp would pick by itself",
# which is kept first because it is the combination yt-dlp maintains.
_CLIENT_ROUNDS: tuple[tuple[str, ...], ...] = ((), ("tv",), ("ios",), ("web_safari",), ("android",))

OEMBED_URL = "https://www.youtube.com/oembed"
TIMEOUT = 12.0


class SourceError(Exception):
    """Raised with an actionable message when a song cannot be loaded."""


# yt-dlp reports every failure as one long DownloadError, and its advice
# ("report this issue on github") is wrong for most of them. Match the cause and
# say something the person reading it can act on.
_FAILURE_HINTS = (
    (("unable to connect to proxy", "tunnel connection failed", "connection refused",
      "temporary failure in name resolution", "network is unreachable",
      "failed to resolve", "timed out"),
     "Could not reach YouTube. Check your internet connection, or whether a proxy or "
     "firewall is blocking it."),
    (("private video", "video is private"),
     "That video is private, so nothing can be read from it. Try another upload."),
    (("video unavailable", "removed by the uploader", "no longer available",
      "account associated with this video has been terminated"),
     "That video is unavailable. Try another upload of the song."),
    (("sign in to confirm your age", "age-restricted", "age restricted",
      "inappropriate for some users"),
     "That video is age-restricted. Sign in by passing browser cookies "
     "(RHYMEMAP_COOKIES_FROM_BROWSER=chrome), or try another upload."),
    (("sign in to confirm", "not a bot", "confirm you're not a bot"),
     "YouTube asked this machine to prove it is not a bot -- it does that to "
     "datacentre addresses, and sometimes to home ones. Pass browser cookies with "
     "RHYMEMAP_COOKIES_FROM_BROWSER=chrome (or firefox, edge, brave), or paste the "
     "lyrics in directly."),
    (("available in your country", "blocked it in your country", "geo restricted",
      "not available from your location"),
     "That video is blocked in your region. Try another upload."),
    (("unsupported url", "is not a valid url"),
     "That link could not be read as a YouTube video."),
)


def explain_failure(message: str) -> str:
    """Turn a yt-dlp error into something worth showing a person."""
    lowered = message.lower()
    for needles, hint in _FAILURE_HINTS:
        if any(needle in lowered for needle in needles):
            return hint
    first = message.split("\n")[0].strip()
    first = first.split("; please report this issue")[0].strip()
    return f"Could not read that video. {first}"


def parse_youtube_id(url: str) -> str | None:
    """Extract the 11-character video id from any YouTube URL shape."""
    if not url:
        return None
    candidate = url.strip()

    if _ID_RE.match(candidate):
        return candidate

    if "://" not in candidate:
        candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")

    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id if _ID_RE.match(video_id) else None

    if host not in {"youtube.com", "music.youtube.com", "youtube-nocookie.com"}:
        return None

    if parsed.path == "/watch":
        values = parse_qs(parsed.query).get("v") or []
        return values[0] if values and _ID_RE.match(values[0]) else None

    for prefix in _PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            video_id = parsed.path[len(prefix):].split("/")[0]
            return video_id if _ID_RE.match(video_id) else None

    return None


def is_youtube_url(url: str) -> bool:
    return parse_youtube_id(url) is not None


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def available_clients() -> set[str]:
    """The player clients the installed yt-dlp knows about."""
    try:
        from yt_dlp.extractor.youtube._base import INNERTUBE_CLIENTS
    except Exception:
        try:
            from yt_dlp.extractor.youtube import INNERTUBE_CLIENTS  # type: ignore[attr-defined]
        except Exception:
            return set()
    return set(INNERTUBE_CLIENTS)


def client_rounds(known: set[str] | None = None) -> list[tuple[str, ...]]:
    """The rotation to try, with clients this yt-dlp does not have removed."""
    if known is None:
        known = available_clients()

    rounds: list[tuple[str, ...]] = []
    for attempt in _CLIENT_ROUNDS:
        # No filtering possible (or needed) for the default round.
        if not attempt:
            rounds.append(attempt)
            continue
        if not known:
            continue
        kept = tuple(client for client in attempt if client in known)
        if kept and kept not in rounds:
            rounds.append(kept)
    return rounds


def cookie_options(environ=None) -> dict:
    """Cookie settings from the environment.

    This is the documented fix for "Sign in to confirm you're not a bot": the
    request is refused for being anonymous, and a signed-in cookie jar settles
    it. It cannot be defaulted on -- reading a browser's cookie store is the
    user's decision to make, not ours.
    """
    environ = os.environ if environ is None else environ
    options: dict = {}

    browser = (environ.get("RHYMEMAP_COOKIES_FROM_BROWSER") or "").strip()
    if browser:
        # yt-dlp's tuple form: (browser, profile, keyring, container).
        options["cookiesfrombrowser"] = (browser, None, None, None)

    cookie_file = (environ.get("RHYMEMAP_COOKIES") or "").strip()
    if cookie_file:
        options["cookiefile"] = cookie_file

    return options


def _ydl_options(clients: tuple[str, ...], environ=None) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "extract_flat": False,
        "noplaylist": True,
    }
    options.update(cookie_options(environ))
    if clients:
        options["extractor_args"] = {"youtube": {"player_client": list(clients)}}
    return options


def pick_caption_track(info: dict, languages=("en",)) -> tuple[dict | None, str, str]:
    """Choose the best caption track from a yt-dlp info dict.

    Manual subtitles beat automatic ones (they are the real lyrics rather than a
    transcription), and json3 beats everything else because it carries per-word
    timing. Returns (track, kind, language).
    """
    wanted = list(languages) + ["en"]

    for kind, key in (("manual", "subtitles"), ("automatic", "automatic_captions")):
        tracks = info.get(key) or {}
        if not tracks:
            continue

        # Exact language, then any regional variant (en-US, en-GB...), then anything.
        ordered: list[str] = []
        for language in wanted:
            if language in tracks:
                ordered.append(language)
        for language in tracks:
            if any(language.startswith(f"{w}-") for w in wanted) and language not in ordered:
                ordered.append(language)
        for language in tracks:
            if language not in ordered:
                ordered.append(language)

        for language in ordered:
            options = tracks[language] or []
            for preferred in _FORMAT_PREFERENCE:
                for option in options:
                    if option.get("ext") == preferred and option.get("url"):
                        return option, kind, language

    return None, "", ""


def caption_tracks_of_kind(info: dict, kind: str, languages=("en",)) -> tuple[dict | None, str]:
    """Like pick_caption_track, restricted to manual *or* automatic captions.

    The resolver needs these separately: a manual track outranks a lyrics-database
    lookup, and an automatic one does not.
    """
    key = "subtitles" if kind == "manual" else "automatic_captions"
    isolated = {key: info.get(key) or {}}
    track, _, language = pick_caption_track(isolated, languages)
    return track, language


def parse_caption_payload(payload: str, ext: str):
    """Parse a downloaded caption track into cues."""
    from ..captions import parse_json3, parse_vtt_captions

    if ext in {"json3", "srv3"}:
        try:
            return parse_json3(payload)
        except ValueError:
            pass
    return parse_vtt_captions(payload)


def probe_oembed(video_id: str, opener=None) -> dict:
    """Title and channel from YouTube's public oEmbed endpoint.

    No API key, no extraction, and it answers when the full extractor is being
    refused -- which is precisely when something is needed to fall back on.
    """
    query = urllib.parse.urlencode({"url": watch_url(video_id), "format": "json"})
    request = urllib.request.Request(
        f"{OEMBED_URL}?{query}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; RhymeMapper/2.1)"},
    )
    try:
        if opener is None:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                body = response.read().decode("utf-8", errors="replace")
        else:
            body = opener(request)
        payload = json.loads(body)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return {}

    if not isinstance(payload, dict):
        return {}
    return {
        "title": str(payload.get("title") or ""),
        "uploader": str(payload.get("author_name") or ""),
        "thumbnail": str(payload.get("thumbnail_url") or ""),
    }


def _import_yt_dlp():
    """Import yt-dlp. A function so it can be substituted in tests.

    The obvious alternative -- patching ``sys.modules["yt_dlp"]`` -- is a trap.
    ``patch.dict`` restores by clearing the dict and refilling it, which evicts
    every module imported inside the patched window. The analysis pipeline
    imports numpy, scipy and g2p_en lazily, so the next request re-imports their
    C extensions and dies with "cannot load module more than once per process".
    One narrow seam avoids all of that.
    """
    import yt_dlp

    return yt_dlp


class YouTubeReader:
    """One extraction, reusable for the caption downloads that follow it.

    yt-dlp's handle has to stay open to fetch a caption track, because the track
    URLs are signed and short-lived, so metadata and captions cannot be split
    into two independent calls.
    """

    def __init__(self, video_id: str, environ=None):
        self.video_id = video_id
        self.environ = environ
        self.info: dict = {}
        self._ydl = None
        self.client_used: str = ""
        self.errors: list[str] = []

    def open(self) -> dict:
        """Extract metadata, rotating player clients until one answers."""
        try:
            yt_dlp = _import_yt_dlp()
        except ImportError as exc:
            raise SourceError(
                "yt-dlp is needed to read YouTube.\n    pip install yt-dlp"
            ) from exc

        rounds = client_rounds()
        for clients in rounds:
            ydl = yt_dlp.YoutubeDL(_ydl_options(clients, self.environ))
            try:
                info = ydl.extract_info(watch_url(self.video_id), download=False)
            except Exception as exc:                        # noqa: BLE001 - yt-dlp raises broadly
                self.errors.append(f"{clients or 'default'}: {exc}")
                ydl.close()
                continue

            if not isinstance(info, dict):
                self.errors.append(f"{clients or 'default'}: no metadata returned")
                ydl.close()
                continue

            self.info = info
            self._ydl = ydl
            self.client_used = ",".join(clients) if clients else "default"
            return info

        raise SourceError(explain_failure(self.errors[-1] if self.errors else "extraction failed"))

    def download_caption(self, track: dict) -> str:
        if self._ydl is None:
            raise SourceError("caption download attempted before extraction")
        return self._ydl.urlopen(track["url"]).read().decode("utf-8", errors="replace")

    def close(self):
        if self._ydl is not None:
            self._ydl.close()
            self._ydl = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False
