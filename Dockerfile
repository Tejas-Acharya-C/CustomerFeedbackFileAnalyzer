FROM python:3.11-slim

WORKDIR /app

# Create non-root user for production safety
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure non-root user owns app files
RUN chown -R appuser:appuser /app

# Production-safe defaults
ENV FLASK_DEBUG=0
ENV MAX_UPLOAD_MB=5
ENV RATE_LIMIT_PER_MIN=60
ENV SESSION_TTL_MINUTES=30
ENV LOG_LEVEL=INFO

EXPOSE 8000

USER appuser

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "wsgi:app", "--timeout", "60"]
