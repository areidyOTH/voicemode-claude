#!/bin/bash
# Start Pico TTS adapter on host (run before docker container)
cd /home/andrew/programs/voicemode_claude/pico-adapter
./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8082 --log-level info
