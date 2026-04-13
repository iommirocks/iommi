FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

WORKDIR /app

# Install deps first for layer caching — source is bind-mounted at runtime
COPY pyproject.toml uv.lock ./
RUN uv sync --dev --frozen
