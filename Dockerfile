# Use official Python slim image
FROM python:3.11-slim

# Install system dependencies for Tableau Hyper API
# See: https://help.tableau.com/current/api/hyper_api/en-us/reference/sqlapi.html#system-requirements
RUN apt-get update && apt-get install -y \
    libxml2 \
    libkrb5-3 \
    libicu-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create output and logs directories
RUN mkdir -p output logs

# Standard command (to be overridden by Cloud Run Jobs arguments)
ENTRYPOINT ["python", "main.py"]
