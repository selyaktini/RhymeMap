# Putting RhymeMapper online

One deployment: the whole application, at a URL, with the link box working.

There used to be a second — a read-only static build for GitHub Pages, with no
engine behind it. It has been removed. It could show an analysis but never
produce one, so the first thing anyone did on it was paste a link into a box
that could not work, and the page spent its hero explaining why.

## Deploy it

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yahyabmo/RhymeMap)

That button reads `render.yaml` from the repository and builds the `Dockerfile`.
Free, and **no credit card** — the only host of its kind still true in 2026.

By hand, if you prefer: [dashboard.render.com](https://dashboard.render.com) →
**New → Blueprint** → pick the repository.

### What free costs you

The service **sleeps after 15 minutes idle**, and the next visitor waits around
50 seconds while it wakes. Fine for a link in a report. Awkward if you are
standing in front of an audience — open the page a minute before you need it.

[Koyeb](https://www.koyeb.com) is the alternative, on the same shape of free
tier, though some regions ask for a card. **Fly.io no longer has a free tier.**

This landscape moves. Hugging Face Spaces was the recommendation here until it
made Docker builds a paid feature; treat any of this as worth re-checking.

## YouTube from a datacentre

YouTube refuses a lot of datacentre traffic — `Sign in to confirm you're not a
bot`. Every yt-dlp-based tool has this problem and it is not fixable from here.

It matters much less than it used to. Since lyrics resolve through a chain, a
refused extraction falls back to the public oEmbed endpoint for the title, and
then to **LRCLIB**, which does not care what address you come from. So a hosted
instance usually still finds the song — it loses the per-word caption timing and
keeps per-line timing, which is enough to drive playback.

Pasting lyrics is unaffected either way.

If you want the word-level timing from a host, pass browser cookies:

```
RHYMEMAP_COOKIES_FROM_BROWSER=chrome    # or firefox, edge, brave
RHYMEMAP_COOKIES=/path/to/cookies.txt   # or an exported cookie file
```

Set either as an environment variable on the service. Nothing is read from any
browser unless you set one.

## Why not run it in the browser instead

It would remove the server entirely: Python compiled to WebAssembly (Pyodide),
everything client-side, hosted as static files.

It cannot work, for a reason that has nothing to do with the engine. **A browser
cannot fetch the lyrics.** YouTube does not allow cross-origin reads of its
caption tracks, and [LRCLIB's CORS policy rejects browser requests
too](https://github.com/monochrome-music/monochrome/issues/646) — it does not
even permit the `user-agent` header. That leaves about 20 MB of WebAssembly
download to analyse text you paste in by hand, which the server does already.

## Cost

Nothing, on the free tier. No card. The trade is the sleep, not money.

## What has and has not been tested

Verified: the exact file set the runtime stage copies, assembled into a
directory with the server bound to `0.0.0.0:7860` as the container binds it —
`GET /` and `/data.js` return 200 and `POST /api/analyze` returns a valid
analysis. The `.dockerignore` was verified the same way: the builder's own step
runs inside a context with the ignore rules applied.

**Not verified: `docker build` itself.** There is no container daemon in the
environment this was written in, so the build mechanics — the `COPY` paths, the
`useradd` step, the two-stage handover — have never actually run. If the first
build fails, that is where to look.
