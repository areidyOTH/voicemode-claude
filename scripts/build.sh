#!/bin/bash
set -e

echo "Building Voice Mode with Rev.ai integration..."

# Build the Docker image
docker build -t voicemode-revai .

echo "Build complete!"
echo ""
echo "Image: voicemode-revai"
echo "Next: Run ./scripts/run.sh to start the container"