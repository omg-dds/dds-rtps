# Dockerfile for OMG DDS-RTPS Interoperability Testing Suite
# Provides an isolated, reproducible environment (IPv4 only, contained multicast discovery)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp

# Install core runtime dependencies: Python 3, Node.js (via NodeSource 20 LTS), and network tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ca-certificates \
    curl \
    unzip \
    zip \
    iproute2 \
    procps \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g xunit-viewer \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy and install python dependencies first to leverage Docker layer caching
COPY requirements.txt /workspace/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt || \
    pip3 install --no-cache-dir -r requirements.txt

# Copy all repository files into container
COPY . /workspace

# Default command: launch test suite
CMD ["/bin/bash", "./run_tests.sh"]
