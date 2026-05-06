FROM python:3.10
ENV APP_HOME=/app
WORKDIR $APP_HOME

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxshmfence1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*


# Install Python dependencies first (leverages Docker layer caching)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install  -r /app/requirements.txt \
    && pip install "uvicorn[standard]==0.30.*"


# Copy application code 
COPY src/ ./src/

# List all files and nested directories
RUN echo "Listing contents of /src:" && ls -R /src

# Start the FastAPI app; respect PORT if provided by platform
# CMD ["sh", "-c", "uvicorn app.main:app --host 127.0.0.1 --port ${PORT:-8000}"]
