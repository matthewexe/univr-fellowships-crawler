FROM python:3.12-slim

WORKDIR /app

# Install cron and clean up apt cache in the same layer
RUN apt-get update && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and entrypoint
COPY crawler.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Schedule crawler to run once a day at 08:00 UTC.
# Output is forwarded to Docker logs via /proc/1/fd/1 (cron is PID 1 in this container).
RUN echo "0 8 * * * root cd /app && python crawler.py >> /proc/1/fd/1 2>&1" \
    > /etc/cron.d/univr-crawler \
    && chmod 0644 /etc/cron.d/univr-crawler

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["cron", "-f"]
