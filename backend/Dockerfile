FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Render sets the PORT env var; default to 8000
ENV PORT=8000

# Run with Uvicorn, binding to 0.0.0.0 on the PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
