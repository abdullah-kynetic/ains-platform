# syntax=docker/dockerfile:1
FROM python:3.12-alpine@sha256:e064671ca452259bab50e8e2c7bd896e39e9a343bb06ca25234adf6fe18d0fc7
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir uv==0.13.5 && \
    addgroup -S ains && adduser -S -G ains -h /app ains
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    uv sync --frozen --no-dev
COPY --chown=ains:ains app ./app
COPY --chown=ains:ains ai_adapter ./ai_adapter
COPY --chown=ains:ains migrations ./migrations
COPY --chown=ains:ains data/checklist ./data/checklist
COPY --chown=ains:ains templates ./templates
COPY alembic.ini ./
COPY --chmod=755 scripts/docker-entrypoint.sh /usr/local/bin/ains-entrypoint
USER ains
EXPOSE 8000
ENTRYPOINT ["ains-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
