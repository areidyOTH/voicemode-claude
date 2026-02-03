#!/bin/bash
set -e

echo "Setting up Voice Mode MCP integration with Claude Code..."

# Check if container is running
if ! docker ps | grep -q voicemode-revai; then
    echo "ERROR: voicemode-revai container is not running"
    echo "Start it first with: ./scripts/run.sh"
    exit 1
fi

# Check if claude command is available
if ! command -v claude &> /dev/null; then
    echo "ERROR: Claude Code CLI is not installed"
    echo "Install it from: https://claude.ai/code"
    exit 1
fi

# Add voice-mode MCP server to Claude Code
echo "Adding voice-mode MCP server to Claude Code..."
claude mcp add --transport stdio voice-mode-docker -- docker exec voicemode-revai uvx --refresh voice-mode

echo "MCP integration setup complete!"
echo ""
echo "Available MCP servers:"
claude mcp list

echo ""
echo "Voice Mode is now available in all Claude Code instances!"
echo "You can start voice conversations by using the voice mode tools in Claude Code."