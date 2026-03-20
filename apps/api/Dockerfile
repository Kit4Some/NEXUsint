FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy project metadata and source for install
COPY pyproject.toml ./
COPY nexus/ ./nexus/

# Install dependencies from pyproject.toml
RUN uv pip install --system --no-cache .

# Download spaCy model
RUN python -m spacy download en_core_web_sm

EXPOSE 8000

CMD ["uvicorn", "nexus.main:sio_asgi_app", "--host", "0.0.0.0", "--port", "8000"]
