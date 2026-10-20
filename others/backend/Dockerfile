FROM python:3.14.6-slim
WORKDIR /opt/labconnect/others/backend
RUN pip install --no-cache-dir uv==0.13.1
COPY others/backend/pyproject.toml others/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY others/backend/app ./app
COPY others/backend/alembic.ini ./alembic.ini
COPY others/config/branding.json /opt/labconnect/others/config/branding.json
RUN uv sync --frozen --no-dev
EXPOSE 8000
CMD [".venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
