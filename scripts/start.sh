#!/bin/bash
set -e

echo "Starting Voice Mode with Rev.ai STT..."

# Check for required environment variables
if [ -z "$REV_AI_ACCESS_TOKEN" ]; then
    echo "ERROR: REV_AI_ACCESS_TOKEN environment variable is required"
    exit 1
fi

# Create logs directory
mkdir -p /home/appuser/logs

# Configure voice mode to use our adapters
export STT_BASE_URL="http://localhost:8081/v1"
# TTS_BASE_URL should be set via environment (points to host Pico adapter)

echo "Rev.ai STT adapter: http://localhost:8081"
echo "Pico TTS adapter: ${TTS_BASE_URL:-not configured}"
echo "Voice Mode available via: docker exec voicemode-revai uvx voice-mode"
echo ""
echo "To use with Claude Code MCP:"
echo "  claude mcp add voice-mode-docker -- docker exec -i voicemode-revai uvx voice-mode"

# Run Rev.ai adapter in foreground (keeps container alive)
echo "Starting Rev.ai STT adapter..."
cd /home/appuser/revai-adapter
exec /home/appuser/revai-adapter/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8081 --log-level info
