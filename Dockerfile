# Voice Mode with Rev.ai Integration
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    alsa-utils \
    pulseaudio \
    ffmpeg \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user with audio group access
RUN useradd -m -s /bin/bash -G audio appuser
USER appuser
WORKDIR /home/appuser

# Install uv package manager and voicemode
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/home/appuser/.local/bin:$PATH" && \
    uv tool install voice-mode

ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy Rev.ai adapter
COPY --chown=appuser:appuser revai-adapter/ /home/appuser/revai-adapter/
WORKDIR /home/appuser/revai-adapter

# Create virtual environment and install dependencies for Rev.ai adapter
RUN /home/appuser/.local/bin/uv venv /home/appuser/revai-adapter/venv && \
    /home/appuser/.local/bin/uv pip install --python /home/appuser/revai-adapter/venv/bin/python \
    fastapi uvicorn websockets httpx python-dotenv python-multipart

# Set environment variables
ENV PYTHONPATH=/home/appuser/revai-adapter:$PYTHONPATH
ENV REV_AI_ACCESS_TOKEN=""
ENV OPENAI_API_KEY="dummy-for-tts"
ENV VOICE_MODE_DEBUG="true"
ENV PATH="/home/appuser/.local/bin:$PATH"

# Expose ports (8080=voicemode, 8081=revai-stt)
EXPOSE 8080 8081

# Copy startup script
COPY --chown=appuser:appuser scripts/start.sh /home/appuser/start.sh
RUN chmod +x /home/appuser/start.sh

# Start both Rev.ai adapter and voice mode
CMD ["/home/appuser/start.sh"]
