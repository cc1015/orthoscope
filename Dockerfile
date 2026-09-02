# OrthoScope backend (FastAPI + PyMOL + MAFFT).
#
# Pinned to linux/amd64 because open-source PyMOL publishes no linux/arm64
# wheel. On Apple Silicon this builds and runs under emulation, which is slower
# but correct.
FROM --platform=linux/amd64 python:3.10-slim

# MAFFT for sequence alignment; the GL/X libraries are PyMOL's runtime
# dependencies, needed even though rendering happens offscreen.
RUN apt-get update && apt-get install -y --no-install-recommends \
        mafft \
        libgl1 \
        libglu1-mesa \
        libxrender1 \
        libxext6 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Pipeline artefacts land here. Mount a volume at /data so results survive a
# container restart, and so the static /files mount never exposes /app.
ENV ORTHOSCOPE_DATA_DIR=/data \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 orthoscope \
    && mkdir -p /data \
    && chown -R orthoscope:orthoscope /data /app
USER orthoscope

WORKDIR /app/src
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# A single worker on purpose: the pipeline is synchronous, CPU-heavy and writes
# to shared paths under /data. Scale by adding a job queue, not workers.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
