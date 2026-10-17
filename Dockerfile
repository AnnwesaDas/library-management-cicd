FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is reused when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY library ./library

# Run as a normal user. The instance folder holds the SQLite file when no DATABASE_URL is set.
RUN useradd --create-home appuser && mkdir instance && chown appuser instance
USER appuser

# The pipeline passes the commit SHA so the page footer and /health show which version is running.
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--threads", "4", "library:create_app()"]
