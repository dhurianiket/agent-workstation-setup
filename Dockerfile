# Dockerfile - Antigravity Autonomous AI Developer Workstation
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1

# Install system dependencies (Node.js 20, Git, Curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install Python requirements
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    boto3 \
    ggshield \
    aider-chat \
    mcp \
    pydantic

# Create app directory
WORKDIR /app

# Copy workstation code
COPY laptop_api_server.py /app/
COPY orchestrate.py /app/
COPY benchmark_models.py /app/
COPY agent_workstation_mcp.py /app/
COPY rules/ /app/rules/
COPY skills/ /app/skills/

# Expose gateway port
EXPOSE 8000

# Health check against unified gateway
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command starts the Unified AI Gateway
CMD ["python", "laptop_api_server.py"]
