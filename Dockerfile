# syntax=docker/dockerfile:1
#
# Dev image for the Xuanwu auth server.
# Everything (Python, uv, deps, tooling) lives INSIDE this image — nothing is
# installed on the host. Multi-stage prod split arrives in Phase 16.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# uv = fast resolver/installer (installed in the container, never the host).
RUN pip install --no-cache-dir "uv>=0.5,<0.6"

# --- dependency layer (cached until requirements.lock changes) ---
# uv is a build-time tool only: install deps, then remove uv so it is neither
# shipped nor flagged by pip-audit in the running image.
COPY requirements.lock ./
RUN uv pip install --system --no-cache -r requirements.lock \
    && pip uninstall -y uv

# --- non-root runtime user (freyno/Barong run as 'app') ---
RUN useradd --create-home --uid 1000 app

COPY --chown=app:app . .
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
