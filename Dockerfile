FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY crawler.py .

CMD ["python", "crawler.py"]
