# Use Python 3.11 slim base
FROM python:3.11-slim

# Install compilers and JDK
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-jdk \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY server.py .

# Expose Flask port
EXPOSE 10000

# Run Flask server
CMD ["python3", "server.py"]