FROM python:3.11-slim

# Install system dependencies including ffmpeg for video/audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pyTelegramBotAPI python-dotenv

# Copy application files
COPY . .

# Expose web server port
EXPOSE 5000

# Set default environment variables
ENV HOST=0.0.0.0
ENV PORT=5000

# Run the web server (or launcher script)
CMD ["python", "server.py"]
