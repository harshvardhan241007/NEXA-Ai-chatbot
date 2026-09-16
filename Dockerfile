FROM python:3.12-slim

WORKDIR /app

# System deps for pypdf/numpy wheels build (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data uploads

ENV HOST=0.0.0.0
ENV PORT=10000

EXPOSE 10000

# Render provides PORT at runtime; fall back to 10000 for local/container runs.
CMD ["sh", "-c", "uvicorn app.api:app --host ${HOST:-0.0.0.0} --port ${PORT:-10000}"]
