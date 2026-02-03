#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Starting Voice Mode with Rev.ai integration..."

# Check for required environment variables
if [ -z "$REV_AI_ACCESS_TOKEN" ]; then
    echo "ERROR: REV_AI_ACCESS_TOKEN not set in .env file"
    exit 1
fi

# Stop existing container if running
docker stop voicemode-revai 2>/dev/null || true
docker rm voicemode-revai 2>/dev/null || true

# Run the container
docker run -d --name voicemode-revai \
  -e REV_AI_ACCESS_TOKEN="$REV_AI_ACCESS_TOKEN" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY:-dummy-for-tts}" \
  -e VOICE_MODE_DEBUG="${VOICE_MODE_DEBUG:-true}" \
  -e DISPLAY="${DISPLAY:-:0}" \
  --device /dev/snd \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/logs:/app/logs \
  -p 8080:8080 \
  -p 8081:8081 \
  --restart unless-stopped \
  voicemode-revai:latest

echo "Container started successfully!"
echo ""
echo "Services:"
echo "- Voice Mode: http://localhost:8080"
echo "- Rev.ai Adapter: http://localhost:8081"
echo ""
echo "Checking container status..."
sleep 5

docker logs --tail 20 voicemode-revai

echo ""
echo "To add to Claude Code:"
echo "claude mcp add voice-mode-docker -- docker exec voicemode-revai uvx voice-mode"
echo ""
echo "To view logs: docker logs -f voicemode-revai"
echo "To stop: docker stop voicemode-revai"