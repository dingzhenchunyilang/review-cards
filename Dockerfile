# syntax=docker/dockerfile:1

# ---------- stage 1: build the frontend ----------
FROM node:22-alpine AS frontend
WORKDIR /build
# Copy manifests first so the npm layer is cached across source-only changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- stage 2: runtime ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# app/database.py derives PROJECT_ROOT as parents[2] of its own path, so the
# built UI has to land at /app/frontend/dist for main.py to serve it.
COPY --from=frontend /build/dist /app/frontend/dist

# The SQLite database lives here. Mount a volume so it survives image upgrades.
VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health').read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
