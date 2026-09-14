"""Serve the viewer with a live analysis endpoint.

    python -m scripts.serve_web [--port 8000] [--no-browser]

The static page works on its own: `make web` pre-exports the bundled verses into
`web/data.js` and `web/index.html` opens straight from disk. This server adds one
thing the static page cannot do — analysing lyrics the user pastes in.

Why a server rather than porting the engine to JavaScript:

* CMUdict is several megabytes, and the syllabifier, the articulatory feature
  tables and the clustering would all have to be reimplemented in JS;
* two implementations of a phonetic engine drift, and then the browser and the
  terminal disagree about what rhymes, which is the one thing this project
  cannot afford.

Only the standard library is used, so there is nothing extra to install.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import webbrowser
from collections import OrderedDict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"

MAX_BODY_BYTES = 256 * 1024      # a very long verse is still only a few KB

# Resolving a link costs a network round trip to YouTube, possibly another to a
# lyrics database, and then the full phonetic analysis. Asking for the same song
# twice - switching engines, reloading, a second person opening the same link -
# should not pay that again. Bounded, because a long-running server should not
# grow without limit.
ANALYSIS_CACHE_SIZE = 24
_analysis_cache: OrderedDict = OrderedDict()
_cache_lock = threading.Lock()


def cache_get(key):
    with _cache_lock:
        if key not in _analysis_cache:
            return None
        _analysis_cache.move_to_end(key)
        return _analysis_cache[key]


def cache_put(key, payload):
    with _cache_lock:
        _analysis_cache[key] = payload
        _analysis_cache.move_to_end(key)
        while len(_analysis_cache) > ANALYSIS_CACHE_SIZE:
            _analysis_cache.popitem(last=False)


def cache_clear():
    with _cache_lock:
        _analysis_cache.clear()


_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class _RangeReader:
    """A file wrapper that stops after `remaining` bytes, for copyfile()."""

    def __init__(self, handle, remaining: int):
        self._handle = handle
        self._remaining = remaining

    def read(self, amount: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        if amount is None or amount < 0:
            amount = self._remaining
        chunk = self._handle.read(min(amount, self._remaining))
        self._remaining -= len(chunk)
        return chunk

    def close(self):
        self._handle.close()


class Handler(SimpleHTTPRequestHandler):
    """Static files from web/, plus POST /api/analyze.

    Adds HTTP Range support, which SimpleHTTPRequestHandler does not implement.
    Browsers refuse to seek within media served without it: setting
    ``audio.currentTime`` silently snaps back to 0, so the karaoke view could be
    played from the start but never scrubbed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, fmt, *args):
        if "/api/" in str(args):
            super().log_message(fmt, *args)

    def send_head(self):
        """Serve a byte range when one is requested, else defer to the base class."""
        range_header = self.headers.get("Range")
        if not range_header:
            return super().send_head()

        match = _RANGE_RE.match(range_header.strip())
        if not match:
            return super().send_head()

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()

        try:
            handle = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        try:
            size = os.fstat(handle.fileno()).st_size
            first, last = match.group(1), match.group(2)

            if first:
                start = int(first)
                end = int(last) if last else size - 1
            else:
                # "bytes=-N" means the final N bytes.
                if not last:
                    handle.close()
                    self.send_error(400, "Invalid Range header")
                    return None
                start = max(0, size - int(last))
                end = size - 1

            if start >= size or start > end:
                handle.close()
                self.send_response(416, "Requested Range Not Satisfiable")
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None

            end = min(end, size - 1)
            handle.seek(start)

            self.send_response(206, "Partial Content")
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            return _RangeReader(handle, end - start + 1)
        except (ValueError, OSError):
            handle.close()
            self.send_error(400, "Invalid Range header")
            return None

    def end_headers(self):
        # Advertise range support so the browser enables seeking at all.
        if not self._headers_buffer or not any(
            b"Accept-Ranges" in chunk for chunk in self._headers_buffer
        ):
            self.send_header("Accept-Ranges", "bytes")

        # Without a Cache-Control header the browser is free to invent one, and
        # it does: the usual heuristic is a tenth of the file's age, during which
        # it will not even ask the server. Deploy a new app.js and returning
        # visitors keep the old one with nothing to suggest why.
        #
        # `no-cache` does not mean "do not store" - it means "always revalidate".
        # The conditional request still answers 304 from Last-Modified, so this
        # costs a round trip and no bytes.
        if not any(b"Cache-Control" in chunk for chunk in (self._headers_buffer or [])):
            self.send_header("Cache-Control", "no-cache")

        super().end_headers()


    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        route = self.path.rstrip("/")
        if route not in {"/api/analyze", "/api/song"}:
            self._send_json({"error": "unknown endpoint"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._send_json({"error": "bad Content-Length"}, 400)
            return
        if length <= 0:
            self._send_json({"error": "empty request"}, 400)
            return
        if length > MAX_BODY_BYTES:
            self._send_json({"error": f"lyrics too long (limit {MAX_BODY_BYTES // 1024} KB)"}, 413)
            return

        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self._send_json({"error": f"invalid JSON: {exc}"}, 400)
            return

        from rhymemap.labeling import ENGINE_CHOICES
        engine = request.get("engine") or "similarity"
        if engine not in ENGINE_CHOICES:
            self._send_json({"error": f"unknown engine {engine!r}"}, 400)
            return

        if route == "/api/song":
            self._handle_song(request, engine)
            return

        lyrics = (request.get("lyrics") or "").strip()
        if not lyrics:
            self._send_json({"error": "no lyrics supplied"}, 400)
            return

        try:
            from rhymemap.webexport import analyse_text

            payload = analyse_text(
                lyrics,
                artist=str(request.get("artist") or "You"),
                track=str(request.get("track") or "Pasted lyrics"),
                engine=engine,
                min_occurrences=max(2, int(request.get("min_occurrences") or 2)),
            )
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
            return

        self._send_json(payload)

    def _handle_song(self, request, engine):
        """Load a song from a link (or raw lyrics) and analyse it."""
        from rhymemap.sources import SourceError, load, parse_youtube_id

        query = (request.get("url") or request.get("query") or "").strip()
        if not query:
            self._send_json({"error": "no link or lyrics supplied"}, 400)
            return

        minimum = max(2, int(request.get("min_occurrences") or 2))

        if request.get("stream"):
            self._stream_song(query, engine, minimum)
            return

        video_id = parse_youtube_id(query)
        key = (video_id, engine, minimum) if video_id else None
        if key is not None:
            cached = cache_get(key)
            if cached is not None:
                self._send_json(dict(cached, cached=True))
                return

        try:
            song = load(query)
        except SourceError as exc:
            # 422 rather than 500: the request was well-formed, the song was not
            # findable. The message lists every source that was tried.
            self._send_json({"error": str(exc)}, 422)
            return
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
            return

        try:
            from rhymemap.webexport import analyse_song

            payload = analyse_song(song, engine=engine, min_occurrences=minimum)
        except Exception as exc:
            self._send_json({"error": f"analysis failed: {type(exc).__name__}: {exc}"}, 500)
            return

        if key is not None:
            cache_put(key, payload)
        self._send_json(payload)


    def _stream_song(self, query, engine, minimum):
        """Resolve and analyse, reporting progress as it goes.

        Newline-delimited JSON, one object per event, ending with the payload.
        Chosen over server-sent events because the client only reads forwards
        and never reconnects, which is all SSE would have added.

        Every number here is work actually completed. Resolving a link is a
        network round trip whose duration cannot be known, so it moves the bar
        only when a step finishes; the analysis is measured per line, which is
        where the time actually goes.
        """
        from rhymemap.sources import SourceError, load, parse_youtube_id
        from rhymemap.webexport import analyse_song

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")   # tells a proxy not to hold it
        self.end_headers()

        def emit(event) -> bool:
            try:
                self.wfile.write((json.dumps(event) + "\n").encode("utf-8"))
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False        # the tab was closed; stop working

        video_id = parse_youtube_id(query)
        key = (video_id, engine, minimum) if video_id else None
        if key is not None:
            cached = cache_get(key)
            if cached is not None:
                emit({"stage": "cached", "progress": 1.0})
                emit({"done": True, "payload": dict(cached, cached=True)})
                return

        emit({"stage": "reading the link" if video_id else "reading the lyrics",
              "progress": 0.02})

        try:
            song = load(query)
        except SourceError as exc:
            emit({"error": str(exc)})
            return
        except Exception as exc:
            emit({"error": f"{type(exc).__name__}: {exc}"})
            return

        found = f"{song.artist} - {song.title}" if song.artist else song.title
        emit({"stage": f"found {found}", "progress": 0.12, "provider": song.provider})

        alive = [True]

        def on_progress(fraction, stage):
            # The analysis owns 12% to 100%.
            if alive[0]:
                alive[0] = emit({"stage": stage, "progress": 0.12 + fraction * 0.88})

        try:
            payload = analyse_song(song, engine=engine, min_occurrences=minimum,
                                   on_progress=on_progress)
        except Exception as exc:
            emit({"error": f"analysis failed: {type(exc).__name__}: {exc}"})
            return

        if key is not None:
            cache_put(key, payload)
        emit({"done": True, "payload": payload})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # PORT and HOST come from the environment when deployed: every container
    # host (Hugging Face Spaces, Render, Fly, Railway) assigns the port and
    # expects the process to listen on all interfaces, not loopback.
    parser.add_argument("--port", "-p", type=int, default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    if not (WEB_DIR / "data.js").exists():
        print("note: web/data.js is missing; run `make web` to pre-export the bundled verses.")
        print("      The paste box will still work.")

    url = f"http://{args.host}:{args.port}/"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"RhymeMapper viewer on {url}  (Ctrl-C to stop)", flush=True)
    if not args.no_browser and args.host in {"127.0.0.1", "localhost"}:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
