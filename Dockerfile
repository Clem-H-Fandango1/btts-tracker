FROM python:3.11-slim

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source code
COPY . .

# Expose the port (Railway will set PORT env var)
EXPOSE 8094

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Use gunicorn for production, but fall back to flask run if preferred
# Railway automatically sets PORT env var, we'll use that or default to 8094
CMD gunicorn --bind 0.0.0.0:${PORT:-8094} --workers 2 --threads 2 --timeout 60 app:app