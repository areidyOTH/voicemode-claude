#!/bin/bash
# Status check script for voice-mode setup

echo "=== Voice Mode Setup Status ==="
echo ""

# Check UV installation
echo "1. UV Package Manager:"
if command -v uv &> /dev/null; then
    echo "   ✓ UV installed: $(uv --version)"
else
    echo "   ✗ UV not found"
fi
echo ""

# Check voice-mode installation
echo "2. Voice Mode:"
if command -v voice-mode &> /dev/null; then
    echo "   ✓ voice-mode installed"
    voice-mode --version 2>&1 | head -1
else
    echo "   ✗ voice-mode not found"
fi
echo ""

# Check Rev.ai adapter service
echo "3. Rev.ai Adapter Service:"
if systemctl is-active --quiet revai-adapter; then
    echo "   ✓ Service is running"
    systemctl status revai-adapter --no-pager -l | grep -E "(Active|Main PID)" | head -2
else
    echo "   ✗ Service is not running"
    echo "   Run: sudo systemctl start revai-adapter"
fi
echo ""

# Check adapter health endpoint
echo "4. Rev.ai Adapter Health:"
if curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    echo "   ✓ Adapter is healthy:"
    curl -s http://localhost:8081/health | python3 -m json.tool
else
    echo "   ✗ Adapter health check failed"
    echo "   Check: sudo journalctl -u revai-adapter -n 20"
fi
echo ""

# Check MCP configuration
echo "5. Claude Code MCP:"
if command -v claude &> /dev/null; then
    echo "   ✓ Claude Code installed"
    claude mcp list 2>&1 | grep -A 1 "voice-mode"
else
    echo "   ✗ Claude Code not found"
fi
echo ""

# Check environment file
echo "6. Environment Configuration:"
if [ -f "/home/andrew/programs/voicemode_claude/.env" ]; then
    echo "   ✓ .env file exists"
    echo "   STT_BASE_URL: $(grep STT_BASE_URL /home/andrew/programs/voicemode_claude/.env | cut -d= -f2)"
    echo "   REV_AI configured: $(grep -q REV_AI_ACCESS_TOKEN /home/andrew/programs/voicemode_claude/.env && echo "Yes" || echo "No")"
else
    echo "   ✗ .env file not found"
fi
echo ""

echo "=== Setup Complete ==="
echo "For more information, see /home/andrew/programs/voicemode_claude/SETUP.md"
