"""Turn a link into something the analyser can read.

The goal is to analyse *any* song, not just the verses in the repository. A
YouTube URL is the most practical handle on one: it identifies the track, and it
is what a person actually has to hand.

The first version of this read captions and stopped. That works beautifully when
captions exist and fails totally when they do not -- which is the common case for
music, because captioning a music video is optional and most labels skip it. The
result was a feature that looked broken at random: the same code, the same link
shape, and "no captions, so there are no lyrics to read".

So lyrics are now resolved through a chain of sources, in descending order of
how much they can tell us:

  1. manual captions   lyrics + a time for every word; written by a person
  2. LRCLIB synced     lyrics + a time for every line; written by a person
  3. automatic captions lyrics + a time for every word; guessed by a machine
  4. LRCLIB plain      lyrics only

The order is about trust, not convenience. Machine transcription of singing is
the least reliable text here -- it mishears rhymes specifically, which is the one
thing this project measures -- so a human-written synced lyric beats it even
though it carries coarser timing.

Every attempt is recorded. When the whole chain comes up empty the error says
what each source answered, because "no lyrics found" without a reason is not
something anyone can act on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..captions import cues_to_verse
from ..timing import WordTiming
from . import lrclib
from .lrc import LyricLine, parse_lrc, to_text
from .titles import TrackName, from_metadata, parse_title
from .youtube import (
    SourceError,
    YouTubeReader,
    caption_tracks_of_kind,
    explain_failure,
    is_youtube_url,
    parse_caption_payload,
    parse_youtube_id,
    pick_caption_track,
    probe_oembed,
    watch_url,
)

__all__ = [
    "Attempt", "LyricLine", "Song", "SourceError", "TrackName",
    "explain_failure", "fetch_youtube", "from_text", "is_youtube_url", "load",
    "parse_caption_payload", "parse_title", "parse_youtube_id",
    "pick_caption_track", "resolve",
]


@dataclass
class Attempt:
    """One source's answer, kept whether it worked or not."""

    provider: str
    ok: bool
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.provider}: {self.detail}"


@dataclass
class Song:
    """A song ready to analyse."""

    title: str
    artist: str
    lyrics: str
    timings: list[WordTiming] = field(default_factory=list)
    lines: list[LyricLine] = field(default_factory=list)
    duration: float = 0.0
    video_id: str = ""
    thumbnail: str = ""
    url: str = ""
    source: str = "text"
    provider: str = ""
    caption_kind: str = ""     # "manual" or "automatic"
    language: str = ""
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return len([line for line in self.lyrics.split("\n") if line.strip()])

    @property
    def sync(self) -> str:
        """The finest timing available: per word, per line, or none."""
        if self.timings:
            return "word"
        if self.lines:
            return "line"
        return "none"


# -------------------------------------------------------------- providers --

def _from_captions(reader: YouTubeReader, kind: str, languages) -> tuple[str, list[WordTiming], str]:
    """Download and parse one kind of caption track. ('', [], '') when absent."""
    track, language = caption_tracks_of_kind(reader.info, kind, languages)
    if track is None:
        return "", [], ""

    payload = reader.download_caption(track)
    cues = parse_caption_payload(payload, track.get("ext", ""))
    lyrics, timings = cues_to_verse(cues)
    return lyrics, timings, language


def _from_lrclib(name: TrackName, duration: float, want_synced: bool,
                 fetcher=None) -> tuple[str, list[LyricLine], str]:
    """Look the song up. Returns (lyrics, timed lines, what matched)."""
    match = lrclib.lookup(name.track, name.artist, duration, fetcher=fetcher)
    if match is None:
        return "", [], ""

    label = f"{match.artist} - {match.track}".strip(" -")

    if want_synced:
        if not match.has_synced:
            return "", [], ""
        lines = parse_lrc(match.synced, duration)
        return to_text(lines), lines, label

    if not match.has_plain:
        return "", [], ""
    return match.plain.strip(), [], label


# ---------------------------------------------------------------- resolve --

def resolve(url: str, languages=("en",), fetcher=None) -> Song:
    """Find a song's lyrics from a YouTube link, trying every source in turn."""
    video_id = parse_youtube_id(url)
    if not video_id:
        raise SourceError(
            f"That does not look like a YouTube link: {url!r}\n"
            "Try a form such as https://www.youtube.com/watch?v=VIDEOID"
        )

    attempts: list[Attempt] = []
    reader = YouTubeReader(video_id)
    info: dict = {}
    extraction_error = ""

    try:
        info = reader.open()
    except SourceError as exc:
        # Blocked extraction is survivable: oEmbed still names the song, and a
        # lyrics database only needs the name.
        extraction_error = str(exc)
        attempts.append(Attempt("youtube", False, extraction_error))
        info = probe_oembed(video_id)
        if info:
            attempts.append(Attempt("youtube oEmbed", True, "recovered the title and channel"))

    try:
        name = from_metadata(info) if info else TrackName("", "")
        duration = float(info.get("duration") or 0)
        song = Song(
            title=name.track or str(info.get("title") or "Untitled"),
            artist=name.artist or "Unknown",
            lyrics="",
            duration=duration,
            video_id=video_id,
            thumbnail=str(info.get("thumbnail") or ""),
            url=watch_url(video_id),
            source="youtube",
        )

        if reader.info:
            lyrics, timings, language = _from_captions(reader, "manual", languages)
            if lyrics.strip():
                song.lyrics, song.timings = lyrics, timings
                song.provider, song.caption_kind, song.language = "captions", "manual", language
                attempts.append(Attempt("manual captions", True, f"{len(timings)} word timings"))
                song.attempts = attempts
                return song
            attempts.append(Attempt("manual captions", False, "none published"))

        if not song.lyrics and name.track:
            try:
                lyrics, lines, label = _from_lrclib(name, duration, want_synced=True, fetcher=fetcher)
            except lrclib.LookupError_ as exc:
                lyrics, lines, label = "", [], ""
                attempts.append(Attempt("lrclib synced", False, str(exc)))
            if lyrics.strip():
                song.lyrics, song.lines = lyrics, lines
                song.provider = "lrclib-synced"
                attempts.append(Attempt("lrclib synced", True, f"matched {label}, {len(lines)} lines"))
                song.attempts = attempts
                return song
            if not any(a.provider == "lrclib synced" for a in attempts):
                attempts.append(Attempt("lrclib synced", False, f"no synced match for {name.query!r}"))

        if reader.info:
            lyrics, timings, language = _from_captions(reader, "automatic", languages)
            if lyrics.strip():
                song.lyrics, song.timings = lyrics, timings
                song.provider, song.caption_kind, song.language = "captions", "automatic", language
                attempts.append(Attempt("automatic captions", True, f"{len(timings)} word timings"))
                song.attempts = attempts
                return song
            attempts.append(Attempt("automatic captions", False, "none published"))

        if name.track:
            try:
                lyrics, _, label = _from_lrclib(name, duration, want_synced=False, fetcher=fetcher)
            except lrclib.LookupError_ as exc:
                lyrics, label = "", ""
                attempts.append(Attempt("lrclib plain", False, str(exc)))
            if lyrics.strip():
                song.lyrics = lyrics
                song.provider = "lrclib-plain"
                attempts.append(Attempt("lrclib plain", True, f"matched {label}, no timing"))
                song.attempts = attempts
                return song
            if not any(a.provider == "lrclib plain" for a in attempts):
                attempts.append(Attempt("lrclib plain", False, f"no match for {name.query!r}"))
    finally:
        reader.close()

    raise SourceError(_exhausted_message(info, attempts, extraction_error))


def _exhausted_message(info: dict, attempts: list[Attempt], extraction_error: str) -> str:
    """Say what was tried, so the reader can tell a block from an absence."""
    title = str(info.get("title") or "That video")
    lines = [f"No lyrics found for {title}.", "", "Tried:"]
    lines += [f"  - {attempt}" for attempt in attempts] or ["  - nothing (no metadata)"]
    lines.append("")

    if extraction_error:
        lines.append(extraction_error)
    else:
        lines.append(
            "The song may be too obscure to be in a lyrics database, or its name "
            "may not have been read correctly from the video title. Pasting the "
            "lyrics in works regardless."
        )
    return "\n".join(lines)


# ---------------------------------------------------------- compatibility --

def fetch_youtube(url: str, languages=("en",), dedupe: bool = True) -> Song:
    """Resolve a YouTube link. Kept as the older name for this."""
    return resolve(url, languages)


def from_text(lyrics: str, title: str = "Pasted lyrics", artist: str = "You") -> Song:
    """Wrap pasted lyrics as a Song."""
    if not lyrics.strip():
        raise SourceError("No lyrics supplied.")
    return Song(title=title, artist=artist, lyrics=lyrics.strip(), source="text", provider="pasted")


def load(url_or_text: str, languages=("en",)) -> Song:
    """Load a song from a YouTube URL, or treat the input as raw lyrics."""
    if is_youtube_url(url_or_text):
        return resolve(url_or_text, languages)
    return from_text(url_or_text)
