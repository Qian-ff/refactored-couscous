FROM python:3.14.6-slim@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144
WORKDIR /opt/labconnect/others/backend
RUN pip install --no-cache-dir uv==0.13.1
COPY others/backend/pyproject.toml others/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY others/backend/app ./app
COPY others/backend/alembic.ini ./alembic.ini
COPY others/config/branding.json /opt/labconnect/others/config/branding.json
COPY others/config/application.json /opt/labconnect/others/config/application.json
COPY others/licenses/fastapi-template-MIT.txt /opt/labconnect/licenses/fastapi-template-MIT.txt
RUN uv sync --frozen --no-dev
RUN useradd --uid 10001 --create-home labconnect \
    && mkdir -p /opt/labconnect/others/runtime/files \
    && chown -R 10001:10001 /opt/labconnect/others/runtime
ARG SOURCE_SHA=unrecorded
LABEL org.opencontainers.image.revision=$SOURCE_SHA
ENV APP_ENV=production LABCONNECT_SOURCE_SHA=$SOURCE_SHA PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
CMD [".venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
