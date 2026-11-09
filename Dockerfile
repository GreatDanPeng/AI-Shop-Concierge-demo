# Stage 1: build the shop page and the widget (web/dist).
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: the API server, which also serves the built page from /app/web/dist.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Not root. /app belongs to this user so `pytest` can write its cache and evals can write reports.
RUN useradd --create-home --uid 10001 app && mkdir /app && chown app:app /app
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# The app and its data, plus what the tests read: the tests, pytest.ini, the README (disclaimer test),
# the drawing list in StoreArt.tsx and the brand logos.
COPY --chown=app:app app/ app/
COPY --chown=app:app data/ data/
COPY --chown=app:app evals/ evals/
COPY --chown=app:app tests/ tests/
COPY --chown=app:app pytest.ini README.md ./
COPY --chown=app:app web/src/design/StoreArt.tsx web/src/design/StoreArt.tsx
COPY --chown=app:app web/public/brands/ web/public/brands/
COPY --chown=app:app --from=web /web/dist web/dist

USER app
EXPOSE 8000

# /health answers 200 even without a key (it reports whether the assistant is configured).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
