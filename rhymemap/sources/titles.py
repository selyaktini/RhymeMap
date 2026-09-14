"""Recover an artist and a track name from a YouTube title.

Needed because the lyrics databases are keyed on "Eminem" / "Rap God", and
YouTube titles look like:

    Eminem - Rap God (Explicit) [Official Video] (4K) | Aftermath

Getting this wrong is not a cosmetic failure. A lookup for a track called
``Rap God (Explicit) [Official Video] (4K)`` matches nothing, so the song
appears to have no lyrics anywhere when in fact the query was malformed.

Everything here is pure, which is the point: the lookup itself needs the
network, but deciding *what* to look up does not, so it can be tested properly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Tokens that mark a bracketed group as packaging rather than part of the name.
# A group is dropped only when *every* word in it is noise, so "(Remix)",
# "(Interlude)" and "(Album Version)" survive - they belong to the title.
_NOISE_WORDS = {
    "official", "video", "videos", "vid", "music", "mv", "m/v",
    "lyric", "lyrics", "lyrical", "lyricvideo",
    "audio", "sound", "visualizer", "visualiser", "visual",
    "explicit", "clean", "dirty", "uncensored", "censored",
    "hd", "hq", "uhd", "sd", "4k", "8k", "1080p", "720p", "60fps",
    "remaster", "remastered", "remasterizado",
    "live", "performance", "session", "sessions",
    "full", "complete", "stream", "streaming", "download", "free",
    "new", "out", "now", "exclusive", "premiere", "teaser", "trailer",
    "closed", "captions", "caption", "cc", "subtitles", "subtitled", "subs",
    "color", "colour", "coded", "eng", "english",
    "reupload", "reuploaded", "extended", "radio", "edit",
    "hq_audio", "highquality", "quality",
}

# Words that are too weak to make a group noise on their own, but do not
# disqualify one either: "(with lyrics)" should go, "(with Rihanna)" should not.
_FILLER_WORDS = {"the", "a", "an", "of", "in", "on", "with", "and", "or", "by", "&", "+", "/", "-", "|"}

_FEATURE_RE = re.compile(
    r"[\(\[\{]?\s*\b(?:feat|ft|featuring|featurin|w/)\b\.?\s*(?P<who>[^\)\]\}\|]*)[\)\]\}]?",
    re.IGNORECASE,
)

# " - " with real spaces, plus the typographic dashes people use instead.
_ARTIST_SPLIT = re.compile(r"\s+[-–—―~|]\s+")

_BRACKET_GROUP = re.compile(r"[\(\[\{]([^\(\)\[\]\{\}]*)[\)\]\}]")

_YEAR = re.compile(r"^(19|20)\d{2}$")

_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def _is_bare_year(text: str) -> bool:
    """"1999" is a plausible song title; "Official Video" is not."""
    words = _tokens(text)
    return len(words) == 1 and bool(_YEAR.match(words[0]))


@dataclass(frozen=True)
class TrackName:
    """What to search a lyrics database for."""

    artist: str
    track: str
    featured: str = ""

    @property
    def query(self) -> str:
        return f"{self.artist} {self.track}".strip()

    def __bool__(self) -> bool:
        return bool(self.track)


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD.finditer(text)]


def is_noise_group(inner: str) -> bool:
    """True when a bracketed group is packaging, not part of the song's name."""
    words = _tokens(inner)
    if not words:
        return True

    meaningful = [word for word in words if word not in _FILLER_WORDS]
    if not meaningful:
        return False    # "(the)" on its own is odd; leave it rather than guess

    # A bare year, or a year alongside other noise, is packaging.
    if all(_YEAR.match(word) or word in _NOISE_WORDS for word in meaningful):
        return True

    return False


def _trim_trailing_year(segment: str) -> str:
    """Drop a bare year glued to the end of a name, keeping the name itself."""
    words = segment.split()
    while len(words) > 1 and _YEAR.match(words[-1].strip("()[]{}")):
        words.pop()
    return " ".join(words)


def strip_noise(title: str) -> str:
    """Remove bracketed packaging, trailing label credits and upload years."""
    previous = None
    current = title
    # Repeat: removing one group can leave two adjacent ones touching.
    while previous != current:
        previous = current
        current = _BRACKET_GROUP.sub(
            lambda m: "" if is_noise_group(m.group(1)) else m.group(0), current
        )

    parts = _ARTIST_SPLIT.split(current)

    # A trailing dash-separated segment that is entirely noise: the unbracketed
    # form of the same thing, as in "Lose Yourself - Official Video". With more
    # than two segments the tail is certainly packaging; with exactly two it is
    # the track itself, so keep it when it could be a real name -- a bare year
    # can be (Joey Bada$$ - 1999).
    while len(parts) > 1 and is_noise_group(parts[-1]):
        if len(parts) == 2 and _is_bare_year(parts[-1]):
            break
        parts.pop()

    # "MIDDLE CHILD 2019" -> "MIDDLE CHILD", applied per segment so it can never
    # consume a segment whole.
    parts = [_trim_trailing_year(part) for part in parts]

    current = " - ".join(part for part in parts if part.strip())
    return re.sub(r"\s{2,}", " ", current).strip(" -\u2013\u2014|/,")



def split_featured(title: str) -> tuple[str, str]:
    """Separate "Sicko Mode ft. Drake" into the track and the guests."""
    match = _FEATURE_RE.search(title)
    if not match:
        return title.strip(), ""

    who = (match.group("who") or "").strip(" .,-–—")
    cleaned = (title[: match.start()] + " " + title[match.end():])
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ([{-–—,")
    return cleaned.strip(" )]}"), who


def clean_channel(channel: str) -> str:
    """YouTube's auto-generated music channels are named "<Artist> - Topic".

    Suffixes are only stripped when something separates them from the name.
    "VEVO" is the exception: it is a brand, always upper-case, and always glued
    on ("EminemVEVO"). Without that distinction "NFrealmusic" loses its ending
    and becomes "NFreal", which matches no artist anywhere.
    """
    name = (channel or "").strip()
    name = re.sub(r"\s*-\s*Topic$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"VEVO$", "", name)
    name = re.sub(r"[\s\-_]+(Official|Music|Records|TV|Channel)$", "", name, flags=re.IGNORECASE)
    return name.strip()


def parse_title(raw_title: str, channel: str = "") -> TrackName:
    """Split a YouTube title into an artist and a track worth searching for.

    Falls back to the channel name for the artist, which is right far more often
    than it looks: a song uploaded without "Artist - " in front of it is usually
    on the artist's own channel.
    """
    cleaned = strip_noise(raw_title or "")
    cleaned, featured = split_featured(cleaned)

    parts = [part.strip() for part in _ARTIST_SPLIT.split(cleaned) if part.strip()]

    if len(parts) >= 2:
        artist, track = parts[0], " - ".join(parts[1:])
    else:
        artist, track = clean_channel(channel), (parts[0] if parts else "")

    # Quoted track names: Artist - "Track"
    track = track.strip().strip('"“”‘’')
    artist = artist.strip().strip('"“”‘’')

    if not track:
        track, artist = artist, clean_channel(channel)

    return TrackName(artist=artist, track=track, featured=featured)


def from_metadata(info: dict) -> TrackName:
    """Prefer YouTube's own music metadata, which needs no guessing at all.

    Videos matched to a release carry ``track`` and ``artist`` fields. When they
    are present they are authoritative; the title parser is the fallback.
    """
    track = str(info.get("track") or "").strip()
    artist = str(info.get("artist") or info.get("creator") or "").strip()

    if track and artist:
        # Multi-artist releases arrive comma- or semicolon-separated.
        primary = re.split(r"\s*[,;]\s*|\s+(?:feat|ft|featuring)\.?\s+", artist, flags=re.IGNORECASE)[0]
        return TrackName(artist=primary.strip(), track=track,
                         featured=artist[len(primary):].strip(" ,;"))

    return parse_title(
        str(info.get("title") or ""),
        str(info.get("uploader") or info.get("channel") or ""),
    )
