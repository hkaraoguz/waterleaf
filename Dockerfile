FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    WATERLEAF_DATA_DIR=/data \
    WATERLEAF_DATABASE_DIR=/tmp/waterleaf-db

RUN pip install --no-cache-dir uv==0.11.8 \
    && useradd --create-home --uid 1000 user \
    && mkdir -p /data \
    && chown user:user /data

WORKDIR /app
COPY --chown=user:user pyproject.toml uv.lock README.md ./
COPY --chown=user:user waterleaf ./waterleaf
COPY --chown=user:user assets ./assets
COPY --chown=user:user app.py ./

RUN uv sync --frozen --no-dev

USER user
ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=3)"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
