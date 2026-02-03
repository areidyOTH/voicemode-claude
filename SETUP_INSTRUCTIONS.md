# Voice Mode with Rev.ai Integration - Setup Instructions

## Prerequisites

Before you begin, make sure you have:

1. **Docker installed** on your system
2. **Rev.ai API access token** - Get one from [Rev.ai](https://www.rev.ai/access_token)
3. **Claude Code CLI** installed - Get it from [claude.ai/code](https://claude.ai/code)
4. **Audio permissions** - Your user should be in the `audio` group

## Quick Start

1. **Run the setup script**:
   ```bash
   ./scripts/setup.sh
   ```

2. **Configure your Rev.ai API token**:
   - Edit the `.env` file created by setup
   - Add your Rev.ai API token:
     ```
     REV_AI_ACCESS_TOKEN=your_actual_token_here
     ```

3. **Build the Docker image**:
   ```bash
   ./scripts/build.sh
   ```

4. **Start the container**:
   ```bash
   ./scripts/run.sh
   ```

5. **Set up Claude Code integration**:
   ```bash
   ./scripts/mcp-setup.sh
   ```

## Manual Setup Steps

### 1. Get Rev.ai API Token

1. Go to [https://www.rev.ai/access_token](https://www.rev.ai/access_token)
2. Sign up or log in
3. Generate an access token
4. Copy the token for use in step 2

### 2. Configure Environment

Edit the `.env` file:
```env
REV_AI_ACCESS_TOKEN=your_revai_access_token_here
OPENAI_API_KEY=dummy-for-tts
VOICE_MODE_DEBUG=true
DISPLAY=:0
```

### 3. Audio Permissions (Linux)

Add your user to the audio group:
```bash
sudo usermod -a -G audio $USER
```

Then log out and log back in.

### 4. Docker Permissions

Add your user to the docker group:
```bash
sudo usermod -a -G docker $USER
```

Then log out and log back in.

## Testing the Installation

### 1. Test Audio Devices
```bash
# List audio input devices
arecord -l

# Test microphone recording (5 seconds)
arecord -d 5 -f cd -t wav test-mic.wav

# Play back the recording
aplay test-mic.wav
```

### 2. Test Rev.ai Adapter
After starting the container:
```bash
curl http://localhost:8081/health
```

Should return: `{"status":"healthy","rev_ai_configured":true}`

### 3. Test MCP Integration
```bash
claude mcp list
```

Should show `voice-mode-docker` in the list.

## Troubleshooting

### Audio Issues
- Ensure your user is in the `audio` group
- Check that `/dev/snd` exists and has proper permissions
- Test microphone with `arecord` before running the container

### Docker Issues
- Ensure Docker daemon is running: `sudo systemctl start docker`
- Check container logs: `docker logs voicemode-revai`
- Verify audio device mapping: `docker exec voicemode-revai ls -la /dev/snd`

### Rev.ai Issues
- Verify your API token is correct in `.env`
- Check Rev.ai adapter logs: `docker logs voicemode-revai | grep revai`
- Test API token with curl:
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" https://api.rev.ai/speechtotext/v1/account
  ```

### MCP Integration Issues
- Ensure container is running: `docker ps | grep voicemode-revai`
- Check Claude Code CLI is installed: `claude --version`
- Restart Claude Code after adding MCP server

## Container Management

### Start/Stop Container
```bash
# Start
./scripts/run.sh

# Stop
docker stop voicemode-revai

# View logs
docker logs -f voicemode-revai

# Remove container
docker stop voicemode-revai && docker rm voicemode-revai
```

### Update Container
```bash
# Rebuild after code changes
./scripts/build.sh
./scripts/run.sh
```

## Using Voice Mode

Once everything is set up:

1. Open Claude Code
2. Voice mode tools should now be available
3. Start a voice conversation using the voice mode interface
4. Speak into your microphone - Rev.ai will transcribe your speech
5. Claude will process and respond through text-to-speech

## Architecture

The system works as follows:

1. **Audio Input**: Your microphone → Docker container via `/dev/snd`
2. **Speech-to-Text**: Voice Mode → Rev.ai Adapter → Rev.ai API → Transcribed text
3. **AI Processing**: Text → Claude Code via MCP → AI response
4. **Speech Output**: AI response → Voice Mode TTS → Audio output

## Support

If you encounter issues:

1. Check the container logs: `docker logs voicemode-revai`
2. Verify all prerequisites are met
3. Test each component individually (audio, Docker, Rev.ai, MCP)
4. Ensure all environment variables are set correctly