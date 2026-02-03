#!/bin/bash
set -e

echo "Setting up Voice Mode with Rev.ai integration..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "IMPORTANT: Please edit .env file and add your Rev.ai API token"
    echo "You can get a Rev.ai API token from: https://www.rev.ai/access_token"
fi

# Create logs directory
mkdir -p logs

# Make scripts executable
chmod +x scripts/*.sh

# Check audio devices
echo "Checking audio devices..."
if [ -e /dev/snd ]; then
    echo "Audio devices found:"
    ls -la /dev/snd/
else
    echo "WARNING: No audio devices found at /dev/snd"
    echo "You may need to install ALSA utils: sudo apt-get install alsa-utils"
fi

# Check user is in audio group
if ! groups | grep -q audio; then
    echo "WARNING: Current user is not in 'audio' group"
    echo "Run: sudo usermod -a -G audio $USER"
    echo "Then log out and log back in"
fi

# Test Docker permissions
if ! docker ps &> /dev/null; then
    echo "WARNING: Cannot run Docker commands without sudo"
    echo "Add user to docker group: sudo usermod -a -G docker $USER"
    echo "Then log out and log back in"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your Rev.ai API token"
echo "2. Run: ./scripts/build.sh"
echo "3. Run: ./scripts/run.sh"
echo ""
echo "For Claude Code integration, run after container is running:"
echo "claude mcp add voice-mode-docker -- docker exec voicemode-revai uvx voice-mode"