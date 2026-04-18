FROM python:3.11-slim

WORKDIR /app

# Copy the entire project first
COPY . /app/

# Create data directory for Railway environment variables
RUN mkdir -p /app/data

# Install dependencies
RUN pip install --no-cache-dir -e .

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Run the application with shell form to support env vars
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
