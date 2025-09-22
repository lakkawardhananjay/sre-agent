# SRE-Agent Dockerfile
# GKE Turns 10 Hackathon - Day 2 MVP

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY sre-agent.py .

# Create non-root user for security
RUN groupadd -r sreagent && useradd -r -g sreagent sreagent
RUN chown -R sreagent:sreagent /app
USER sreagent

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import sys, http.client; conn = http.client.HTTPConnection('localhost:8000'); conn.request('GET', '/health'); sys.exit(0) if conn.getresponse().status == 200 else sys.exit(1)"]

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "sre-agent.py"]