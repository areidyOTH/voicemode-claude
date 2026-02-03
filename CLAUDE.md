# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Voice mode integration for Claude Code using Docker containers:
- **VoiceMode**: Python-based voice interaction tool (installed via `uvx voice-mode`)
- **Multi-provider TTS**: Text-to-speech via custom OpenAI-compatible adapter
  - **Piper** (local): Fast, free, ~60MB voice model
  - **Replicate Kokoro** (cloud): High-quality, 44 voices, ~$0.0008/request
- **Multi-provider STT**: Speech-to-text via custom OpenAI-compatible adapter
  - **Groq Whisper Turbo** (default): Fast and cheap ($0.04/hr, 216x realtime)
  - **Rev.ai**: Batch transcription (slower, established)
  - **Deepgram**: Real-time streaming capable
- **MCP integration**: Model Context Protocol for Claude Code connectivity

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose                               │
├─────────────────────────────────────────────────────────────────────┤
│  voicemode-revai container (ports 8080, 8081)                       │
│  ├── voice-mode (uvx) - MCP server for Claude Code                  │
│  └── stt-adapter (port 8081) - OpenAI-compatible STT endpoint       │
│       └── Routes to: Groq (default), Rev.ai, or Deepgram            │
├─────────────────────────────────────────────────────────────────────┤
│  tts-adapter container (port 8082 external, 8000 internal)          │
│  └── tts-adapter - OpenAI-compatible TTS endpoint                   │
│       └── Routes to: Piper (local) or Replicate Kokoro (cloud)      │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow
1. **STT**: Microphone → voicemode container → stt-adapter → STT provider → transcribed text
2. **TTS**: Claude response → voice-mode → tts-adapter → TTS provider → audio output

### Key Files
- `docker-compose.yml`: Defines both containers with networking and health checks
- `Dockerfile`: Main container with voice-mode and STT adapter
- `piper-adapter/Dockerfile`: TTS container with Piper pre-installed
- `piper-adapter/main.py`: Multi-provider TTS adapter (Piper, Replicate Kokoro)
- `revai-adapter/main.py`: Multi-provider STT adapter (Groq, Rev.ai, Deepgram)
- `scripts/start.sh`: Container entrypoint starting the STT adapter

## Development Commands

### Docker Operations
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f
docker logs piper-tts --tail 50
docker logs voicemode-revai --tail 50

# Rebuild after changes
docker compose down && docker compose build && docker compose up -d

# Stop services
docker compose down
```

### MCP Integration
```bash
# Add MCP server to Claude Code (run once)
claude mcp add --transport stdio voice-mode-docker -- docker exec -i voicemode-revai uvx voice-mode

# Verify MCP connection
claude mcp list

# Remove if needed
claude mcp remove voice-mode-docker
```

### Testing
```bash
# Test STT endpoint
arecord -d 3 -f cd -t wav test.wav
curl -X POST http://localhost:8081/v1/audio/transcriptions -F "file=@test.wav"

# Test TTS endpoint
curl -X POST http://localhost:8082/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "voice": "nova"}' \
  --output test.wav && aplay test.wav

# Check health and current providers
curl http://localhost:8081/health      # STT health
curl http://localhost:8081/providers   # STT providers
curl http://localhost:8082/health      # TTS health
curl http://localhost:8082/providers   # TTS providers

# Test microphone
arecord -d 5 -f cd -t wav test-mic.wav && aplay test-mic.wav
```

## Environment Variables

### STT Provider Configuration

Set in `.env`:
```bash
# Provider selection: groq (default), revai, deepgram
STT_PROVIDER=groq

# Groq (default - fast and cheap)
GROQ_API_KEY=your_groq_api_key
GROQ_STT_MODEL=whisper-large-v3-turbo

# Rev.ai (backup - slower batch processing)
REV_AI_ACCESS_TOKEN=your_token

# Deepgram (optional)
DEEPGRAM_API_KEY=your_key
```

### TTS Provider Configuration

Set in `.env`:
```bash
# Provider selection: piper (default, local), kokoro (Replicate cloud)
TTS_PROVIDER=kokoro

# Replicate API (for Kokoro TTS)
REPLICATE_API_TOKEN=your_replicate_api_token
KOKORO_DEFAULT_VOICE=af_bella
```

### Provider Comparison

**STT Providers:**

| Provider | Price/min | Speed | Notes |
|----------|-----------|-------|-------|
| Groq Whisper Turbo | $0.00067 | 216x realtime | Default, multilingual |
| Rev.ai | $0.003 | ~55s latency | Batch processing |
| Deepgram | $0.0077 | Real-time | Streaming capable |

**TTS Providers:**

| Provider | Price | Speed | Notes |
|----------|-------|-------|-------|
| Piper | Free | ~1s | Local, single voice |
| Replicate Kokoro | ~$0.0008/req | ~2s (warm) / ~10s (cold) | 44 voices, high quality, cold start is slow |

### Kokoro Voice Options

American Female: `af_alloy`, `af_bella`, `af_heart`, `af_nova`, `af_sky`, etc.
American Male: `am_adam`, `am_echo`, `am_michael`, `am_onyx`, etc.
British: `bf_emma`, `bf_lily`, `bm_daniel`, `bm_george`, etc.
Other: French (`ff_siwis`), Japanese (`jf_gongitsune`), Chinese (`zf_xiaoxiao`), etc.

### Other Configuration

```bash
OPENAI_API_KEY=dummy-for-tts    # Not used, but voice-mode expects it
```

Container-internal (set in docker-compose.yml):
- `STT_BASE_URL=http://localhost:8081/v1` - Points to STT adapter
- `TTS_BASE_URL=http://piper-tts:8000/v1` - Points to TTS adapter

## Troubleshooting

### TTS speaks error messages instead of text
VoiceMode defaults to Kokoro TTS which isn't installed. Fix by configuring voice-mode to use the TTS adapter:
```bash
docker exec voicemode-revai sh -c 'cat >> /home/appuser/.voicemode/voicemode.env << EOF
VOICEMODE_TTS_BASE_URLS=http://piper-tts:8000/v1
VOICEMODE_PREFER_LOCAL=false
VOICEMODE_VOICES=af_bella
EOF'
```

### STT returns empty transcriptions
Check adapter logs and provider configuration:
```bash
docker logs voicemode-revai --tail 50 | grep -i error
curl http://localhost:8081/providers  # Check which providers are configured
```

### Switching providers
Edit `.env` and restart:
```bash
# Edit .env to change STT_PROVIDER or TTS_PROVIDER
docker compose down && docker compose up -d
```

### Audio device issues
Ensure PulseAudio socket is mounted and user is in audio group:
```bash
# On host
sudo usermod -aG audio $USER
# Then re-login
```
