# The full application: live analysis of pasted lyrics and YouTube links.
#
# Two stages. The builder installs everything and bakes the artefacts that are
# expensive to produce at runtime (NLTK corpora, the pre-analysed songs, the
# phonetic caches); the runtime stage installs only what the web server needs.
#
# That split matters on a free tier. pandas, matplotlib, seaborn and
# scikit-learn are ~157 MB and belong to the corpus tooling, plotting and
# evaluation - none of which runs behind the server. Leaving them out roughly
# halves the image, and a smaller image is a shorter cold start on a host that
# sleeps when idle.
#
# For the read-only demo, which needs no container at all, see
# scripts/build_static.py and .github/workflows/pages.yml.

# ---------------------------------------------------------------- builder ---
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NLTK_DATA=/artefacts/nltk_data \
    RHYMEMAP_CACHE_DIR=/artefacts/cache

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    # g2p_en declares `distance`, whose setup.py uses an attribute setuptools
    # removed in v60. It never imports it.
    && pip install --no-cache-dir --no-deps g2p_en

COPY . .

RUN mkdir -p /artefacts/nltk_data /artefacts/cache \
    && python -m scripts.fetch_nltk_data \
    # Bake the bundled songs and warm the phonetic caches, so the first request
    # does not pay for a 4s model load or a corpus read.
    && python -m rhymemap.webexport --demo --engine chains

# ---------------------------------------------------------------- runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NLTK_DATA=/app/nltk_data \
    RHYMEMAP_CACHE_DIR=/app/.cache \
    HOST=0.0.0.0 \
    PORT=7860

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt \
    && pip install --no-cache-dir --no-deps g2p_en

COPY --from=builder /build/rhymemap ./rhymemap
COPY --from=builder /build/scripts ./scripts
COPY --from=builder /build/web ./web
COPY --from=builder /build/dataset ./dataset
COPY --from=builder /artefacts/nltk_data ./nltk_data
COPY --from=builder /artefacts/cache ./.cache

# Run as a non-root user; Hugging Face Spaces requires it, others prefer it.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 7860
CMD ["python", "-m", "scripts.serve_web", "--no-browser"]
