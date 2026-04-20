FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Install system dependencies required by Python packages
# Including libraries for PDF/DOCX processing (PyPDF2, python-docx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev && rm -rf /var/lib/apt/lists/*

# Use uv for fast Python package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies from pyproject.toml
# Includes: FastAPI, ML models, file processing (PyPDF2, python-docx), etc.
COPY backend/pyproject.toml .
RUN uv pip install --system ".[dev]"

# Install ML pipeline dependencies
COPY ml /app/ml
RUN uv pip install --system /app/ml

# Copy application code
COPY backend/ .

# Expose API port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
