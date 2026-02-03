# Voice Mode Setup - Direct Installation

This document describes the **direct installation** setup for voice-mode with Rev.ai integration.

## Architecture

**Hybrid Approach:**
- **Voice-mode**: Installed directly via UV (`uv tool install voice-mode`)
- **Rev.ai Adapter**: Runs as a standalone systemd service
- **Claude Code**: Connects via MCP protocol

### Components

1. **Voice-mode v8.1.0**: Installed in `~/.local/bin/`
2. **Rev.ai Adapter Service**: Systemd service running on port 8081
3. **MCP Integration**: Configured in `.claude.json`

## Installation Summary

### 1. Voice-mode Installation
```bash
# UV package manager is installed
uv tool install voice-mode
```

### 2. Rev.ai Adapter Service
```bash
# Virtual environment created
cd /home/andrew/programs/voicemode_claude/revai-adapter
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Service installed and enabled
sudo systemctl enable revai-adapter.service
sudo systemctl start revai-adapter.service
```

### 3. Environment Configuration
Environment variables in `/home/andrew/programs/voicemode_claude/.env`:
- `STT_BASE_URL=http://localhost:8081/v1`
- `REV_AI_ACCESS_TOKEN=<your-token>`
- `OPENAI_API_KEY=dummy-for-tts`
- `VOICE_MODE_DEBUG=true`

### 4. Claude Code MCP
MCP server configured in `~/.claude.json` with environment variables.

## Service Management

### Check Rev.ai Adapter Status
```bash
sudo systemctl status revai-adapter
```

### View Adapter Logs
```bash
sudo journalctl -u revai-adapter -f
```

### Restart Adapter
```bash
sudo systemctl restart revai-adapter
```

### Stop Adapter
```bash
sudo systemctl stop revai-adapter
```

## Testing

### 1. Test Rev.ai Adapter Health
```bash
curl http://localhost:8081/health
# Expected: {"status":"healthy","rev_ai_configured":true}
```

### 2. Test MCP Connection
```bash
claude mcp list
# Should show: voice-mode: ✓ Connected
```

### 3. Use Voice Mode
From Claude Code, voice-mode tools should be available through MCP.

## Advantages of Direct Installation

1. **Latest Version**: Always get the newest voice-mode updates
2. **Simpler Setup**: No Docker configuration needed
3. **Native Performance**: Direct system integration
4. **Easy Updates**: `uv tool upgrade voice-mode`

## Troubleshooting

### Rev.ai Adapter Not Starting
```bash
# Check logs
sudo journalctl -u revai-adapter -n 50

# Test manually
cd /home/andrew/programs/voicemode_claude/revai-adapter
source venv/bin/activate
python main.py
```

### MCP Connection Issues
```bash
# Verify environment variables in ~/.claude.json
cat ~/.claude.json | jq '.projects["/home/andrew/programs/voicemode_claude/revai-adapter"].mcpServers["voice-mode"]'

# Test voice-mode directly
uvx voice-mode --help
```

### Rev.ai API Issues
- Check your Rev.ai token is valid
- Verify you have API quota remaining
- Check network connectivity to Rev.ai API

## Breaking Changes and Migration Notes

### From v6.x to v8.x
- Tool loading defaults to minimal set (only `converse` and `service`)
- Parameter renames:
  - `listen_duration` → `listen_duration_max`
  - `min_listen_duration` → `listen_duration_min`
  - `VOICEMODE_PIP_LEADING_SILENCE` → `VOICEMODE_CHIME_LEADING_SILENCE`

### New in v8.x
- **VoiceMode Connect**: Remote voice control via mobile/web apps
- **VoiceMode DJ**: Background music with automatic audio ducking
- **HTTP MCP server**: Works across Claude.ai, Desktop, Cowork, and Mobile
- **Multi-agent support**: Named agents with coordination via conch lock
- **Local service installers**: `voicemode whisper install`, `voicemode kokoro install`
- **Plugin marketplace**: `claude plugin marketplace add mbailey/plugins`

## Migration from Docker

The previous Docker-based setup has been replaced with this direct installation.

**Old approach:**
- Custom Dockerfile with voice-mode installation
- Docker Compose with audio device mapping
- Docker-based MCP integration

**New approach:**
- Direct UV installation
- Systemd service for Rev.ai adapter
- Native MCP integration

## Files Reference

- `/home/andrew/programs/voicemode_claude/.env` - Environment variables
- `/home/andrew/programs/voicemode_claude/revai-adapter/` - Adapter source
- `/etc/systemd/system/revai-adapter.service` - Systemd service
- `~/.claude.json` - MCP configuration
- `/home/andrew/programs/voicemode_claude/CLAUDE.md` - Project documentation

## Resources

- Voice-mode Documentation: https://voice-mode.readthedocs.io/
- Voice-mode GitHub: https://github.com/mbailey/voicemode
- Rev.ai API Docs: https://docs.rev.ai/
- Claude Code MCP: https://docs.claude.com/en/docs/claude-code/mcp
