# Rashid Agent API / worker — Chabokan mirrors (Iran-friendly builds)
# Use DOCKER_BUILDKIT=1 for pip cache mounts (do not pin docker/dockerfile from Docker Hub).
# Build context: repository root
# Docs: https://docs.chabokan.net/simple-hosting/python/more/
#
# Layer strategy: install deps from pyproject.toml first (cached), then copy
# application code. BuildKit pip cache avoids re-downloading wheels on rebuild.

ARG PYTHON_IMAGE=mirror2.chabokan.net/library/python:3.11-slim-bookworm
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_INDEX_URL=https://mirror2.chabokan.net/pypi/simple/ \
    PIP_TRUSTED_HOST="mirror2.chabokan.net pypi.org files.pythonhosted.org" \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1

COPY docker/apt-chabokan-bookworm.sh /tmp/apt-chabokan-bookworm.sh
RUN sed -i 's/\r$//' /tmp/apt-chabokan-bookworm.sh \
    && sh /tmp/apt-chabokan-bookworm.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libpq5 \
        dos2unix \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /tmp/apt-chabokan-bookworm.sh

WORKDIR /app

COPY docker/pip-chabokan.conf /etc/pip.conf
COPY pyproject.toml README.md ./

# Minimal package layout so `pip install -e .` can resolve without full source.
# When only app code changes, this layer + dependency install stay cached.
RUN mkdir -p backend/app backend/worker \
    && printf '# stub\n' > backend/app/__init__.py \
    && printf '# stub\n' > backend/worker/__init__.py

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel \
    && (python -m pip install -e . \
        || { echo ">>> Chabokan mirror missing packages; trying PyPI.org once..."; \
             PIP_INDEX_URL=https://pypi.org/simple/ \
             PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org" \
             python -m pip install --default-timeout=120 --retries=3 -e .; })

# Application source — invalidates only this layer + quick --no-deps reinstall
COPY backend ./backend

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-deps -e . \
    && dos2unix /app/backend/start.sh \
    && chmod +x /app/backend/start.sh \
    && mkdir -p /app/backend/data

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=10 \
    CMD curl -fsS "http://127.0.0.1:${RASHID_PORT:-8000}/api/v1/health" || exit 1

ENTRYPOINT ["/app/backend/start.sh"]
CMD []
