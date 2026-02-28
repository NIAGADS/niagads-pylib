# Multi-stage Dockerfile for genomicsdb-schema-manager
# Requires Python 3.11+
# Stage 1: Builder - handles dependency installation and project setup
FROM python:3.12-slim as builder

WORKDIR /build

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy monorepo structure
COPY pyproject.toml poetry.lock* ./
COPY components/ ./components/
COPY bases/ ./bases/

# Copy project-specific files
COPY projects/genomicsdb-schema-manager/ ./project/

WORKDIR /build/project

# Install project dependencies (without dev dependencies in production)
RUN poetry install --no-dev --no-directory && \
    poetry run pip install --no-cache-dir .

# Stage 2: Runtime - minimal final image
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code and scripts
COPY --from=builder --chown=appuser:appuser /build/project/ /app/

# Copy monorepo components (for runtime imports)
COPY --chown=appuser:appuser components/ /app/components/
COPY --chown=appuser:appuser bases/ /app/bases/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:$PATH"

# Switch to non-root user
USER appuser

# Default command: print help
CMD ["alembic", "--help"]
