"""Persistent memoisation for the expensive phonetic lookups.

``g2p_en`` runs a POS tagger and, for out-of-vocabulary words, a small neural
network.  Measured on ``dataset/artists_sample.csv`` it costs ~0.8 ms per token
against ~0.1 ms for a CMUdict-backed syllabification, and 56% of the tokens in
that corpus are repeats.  Caching therefore removes most of the phonetic cost of
a batch run.

Two tiers:
  * an in-process dict, for repeats inside one run;
  * a JSON file under ``.cache/``, so a second run of ``make stats`` skips the
    work entirely.

The disk tier is best-effort: any I/O problem degrades to the memory tier rather
than failing the pipeline.
"""

from __future__ import annotations

import atexit
import json
import os
import tempfile
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("RHYMEMAP_CACHE_DIR", PROJECT_ROOT / ".cache"))

# Bump when the stored value format changes -- or when the same word starts
# resolving to different phonemes, as it did when Darija routing arrived and
# "3ndi" stopped being read as English.
CACHE_VERSION = 3


class JsonCache:
    """A dict-like string -> JSON-serialisable store backed by a JSON file."""

    def __init__(self, name: str):
        self.path = CACHE_DIR / f"{name}.v{CACHE_VERSION}.json"
        self._data: dict = {}
        self._dirty = False
        self._lock = threading.Lock()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            with open(self.path, encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                self._data = loaded
        except (OSError, ValueError):
            # Missing or corrupt cache is not an error; we just start empty.
            self._data = {}

    def get(self, key: str, default=None):
        self._ensure_loaded()
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        self._ensure_loaded()
        return key in self._data

    def set(self, key: str, value) -> None:
        self._ensure_loaded()
        with self._lock:
            self._data[key] = value
            self._dirty = True

    def flush(self) -> None:
        """Atomically write the cache out, if anything changed."""
        if not self._dirty:
            return
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(CACHE_DIR), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(self._data, handle)
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            self._dirty = False
        except OSError:
            # Read-only checkout or full disk: keep running from memory.
            pass

    def clear(self) -> None:
        with self._lock:
            self._data = {}
            self._dirty = True
        self._loaded = True

    def stats(self) -> dict:
        self._ensure_loaded()
        return {"entries": len(self._data), "path": str(self.path)}


PHONEME_CACHE = JsonCache("phonemes")
SYLLABLE_CACHE = JsonCache("syllables")

atexit.register(PHONEME_CACHE.flush)
atexit.register(SYLLABLE_CACHE.flush)


def flush_all() -> None:
    PHONEME_CACHE.flush()
    SYLLABLE_CACHE.flush()
