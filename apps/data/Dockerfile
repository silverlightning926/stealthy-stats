FROM python:3.14-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY . .

FROM python:3.14-slim-trixie

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

RUN useradd -m -u 1000 prefect && \
    chown -R prefect:prefect /app

USER prefect

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]
