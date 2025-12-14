FROM python:3.14-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

COPY apps/data/pyproject.toml apps/data/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY packages/ ./packages/
COPY apps/data/ ./apps/data/

FROM python:3.14-slim-trixie AS development

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY apps/data/pyproject.toml apps/data/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

COPY packages/ ./packages/
COPY apps/data/ ./apps/data/

RUN useradd -m -u 1000 prefect && \
    chown -R prefect:prefect /app

USER prefect

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["python", "apps/data/main.py"]

FROM python:3.14-slim-trixie AS production

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/apps/data /app/apps/data

RUN useradd -m -u 1000 prefect && \
    chown -R prefect:prefect /app

USER prefect

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://prefect-server:4200/api/health', timeout=5)" || exit 1

CMD ["python", "apps/data/main.py"]
