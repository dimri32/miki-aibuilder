FROM python:3.10

ENV APP_HOME=/app
WORKDIR $APP_HOME

# ── Install dependencies ─────────────────────────
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install "uvicorn[standard]==0.30.*"

# ── Copy application code ────────────────────────
COPY src/ ./src/

# ── Copy required data/config files ──────────────
COPY *.npz ./
COPY *.md ./
COPY *.txt ./

# Start the FastAPI app; respect PORT if provided by platform
# CMD ["sh", "-c", "uvicorn app.main:app --host 127.0.0.1 --port ${PORT:-8000}"]
