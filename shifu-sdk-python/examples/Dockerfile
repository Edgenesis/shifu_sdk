FROM python:3.11-slim

LABEL maintainer="Shifu DeviceShifu Example"
LABEL description="Example DeviceShifu using Shifu Python SDK"

# Set working directory
WORKDIR /app

# Copy SDK source code
COPY src/ /app/src/
COPY pyproject.toml /app/

# Copy example application
COPY examples/deviceshifu_example.py /app/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Run as non-root user for security
RUN useradd -m -u 1000 deviceshifu && \
    chown -R deviceshifu:deviceshifu /app

USER deviceshifu

# Set environment variables (can be overridden in Kubernetes)
ENV PYTHONUNBUFFERED=1

# Run the example
CMD ["python", "/app/deviceshifu_example.py"]


