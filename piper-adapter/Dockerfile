# Lightweight Piper TTS with OpenAI-compatible API
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install piper-tts and dependencies
RUN pip install --no-cache-dir piper-tts fastapi uvicorn pydantic pathvalidate httpx

# Create app directory and voices directory
RUN mkdir -p /app/voices
WORKDIR /app

# Pre-download default voice (lessac medium - good quality, reasonable size ~60MB)
RUN wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
    -O /app/voices/en_US-lessac-medium.onnx && \
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
    -O /app/voices/en_US-lessac-medium.onnx.json

# Copy adapter code
COPY main.py /app/

# Environment
ENV PIPER_VOICES_DIR=/app/voices
ENV PIPER_DEFAULT_VOICE=en_US-lessac-medium

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
