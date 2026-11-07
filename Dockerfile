FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
RUN pip install --no-cache-dir uv==0.13.5 && groupadd --system ains && useradd --system --gid ains --home /app ains
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY --chown=ains:ains app ./app
COPY --chown=ains:ains migrations ./migrations
COPY --chown=ains:ains data/checklist ./data/checklist
COPY --chown=ains:ains templates ./templates
COPY alembic.ini ./
COPY --chmod=755 scripts/docker-entrypoint.sh /usr/local/bin/ains-entrypoint
USER ains
EXPOSE 8000
ENTRYPOINT ["ains-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
