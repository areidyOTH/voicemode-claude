"""
Multi-provider TTS Adapter - OpenAI-compatible Text-to-Speech endpoint
Supports multiple backends: Piper (local), Replicate Kokoro, etc.
"""

import os
import subprocess
import tempfile
import logging
import time
import httpx
from abc import ABC, abstractmethod
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# TTS Provider Abstract Base Class
# =============================================================================

class TTSProvider(ABC):
    """Abstract base class for TTS providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider has required configuration"""
        pass

    @abstractmethod
    def get_voices(self) -> list[dict]:
        """Return list of available voices"""
        pass

    @abstractmethod
    async def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize speech and return audio bytes (WAV format)"""
        pass


# =============================================================================
# Piper Provider (Local)
# =============================================================================

class PiperProvider(TTSProvider):
    """Piper TTS - local neural TTS"""

    def __init__(self):
        self.voices_dir = Path(os.getenv("PIPER_VOICES_DIR", "/app/voices"))
        self.default_voice = os.getenv("PIPER_DEFAULT_VOICE", "en_US-lessac-medium")
        # Map OpenAI voices to Piper voices
        self.voice_map = {
            "alloy": "en_US-lessac-medium",
            "echo": "en_US-lessac-medium",
            "fable": "en_US-lessac-medium",
            "onyx": "en_US-lessac-medium",
            "nova": "en_US-lessac-medium",
            "shimmer": "en_US-lessac-medium",
        }

    @property
    def name(self) -> str:
        return "Piper"

    @property
    def is_configured(self) -> bool:
        try:
            result = subprocess.run(["which", "piper"], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    def get_voices(self) -> list[dict]:
        voices = []
        if self.voices_dir.exists():
            for f in self.voices_dir.glob("*.onnx"):
                voice_name = f.stem
                voices.append({"id": voice_name, "name": voice_name, "provider": "piper"})
        return voices

    def _get_voice_path(self, voice_name: str) -> tuple[Path, str]:
        """Get path to voice model"""
        piper_voice = self.voice_map.get(voice_name.lower(), voice_name)
        model_path = self.voices_dir / f"{piper_voice}.onnx"
        return model_path, piper_voice

    async def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        start_time = time.time()

        model_path, piper_voice = self._get_voice_path(voice)
        model_or_name = str(model_path) if model_path.exists() else piper_voice

        logger.info(f"[Piper] Synthesizing: voice={piper_voice}, text_len={len(text)}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = ["piper", "--model", model_or_name, "--output_file", tmp_path]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = process.communicate(
                input=text.encode('utf-8'),
                timeout=120
            )

            if process.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
                raise HTTPException(status_code=500, detail=f"TTS failed: {stderr.decode()}")

            with open(tmp_path, "rb") as f:
                audio_data = f.read()

            elapsed = time.time() - start_time
            logger.info(f"[TIMING] Piper synthesis: {elapsed:.2f}s")

            return audio_data

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# =============================================================================
# Replicate Kokoro Provider
# =============================================================================

class ReplicateKokoroProvider(TTSProvider):
    """Replicate Kokoro-82M - high quality neural TTS via Replicate API"""

    def __init__(self):
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        self.model = "jaaari/kokoro-82m"
        self.version = os.getenv("KOKORO_VERSION", "f559560eb822dc509045f3921a1921234918b91739db4bf3daab2169b71c7a13")
        self.default_voice = os.getenv("KOKORO_DEFAULT_VOICE", "af_bella")
        # Map OpenAI voices to Kokoro voices
        self.voice_map = {
            "alloy": "af_alloy",
            "echo": "am_echo",
            "fable": "bf_emma",
            "onyx": "am_onyx",
            "nova": "af_nova",
            "shimmer": "af_bella",
        }
        # Available Kokoro voices
        self.available_voices = [
            # American Female
            "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
            "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
            # American Male
            "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
            "am_michael", "am_onyx", "am_puck", "am_santa",
            # British Female
            "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
            # British Male
            "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
            # French Female
            "ff_siwis",
            # Hindi Female
            "hf_alpha", "hf_beta",
            # Hindi Male
            "hm_omega", "hm_psi",
            # Italian Female
            "if_sara",
            # Italian Male
            "im_nicola",
            # Japanese Female
            "jf_alpha", "jf_gongitsune",
            # Japanese Male
            "jm_kumo",
            # Portuguese Female
            "pf_dora",
            # Portuguese Male
            "pm_alex", "pm_santa",
            # Chinese Female
            "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
            # Chinese Male
            "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
        ]

    @property
    def name(self) -> str:
        return f"Replicate Kokoro ({self.default_voice})"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token)

    def get_voices(self) -> list[dict]:
        return [{"id": v, "name": v, "provider": "kokoro"} for v in self.available_voices]

    async def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        start_time = time.time()

        # Map OpenAI voice names to Kokoro voices
        kokoro_voice = self.voice_map.get(voice.lower(), voice)
        if kokoro_voice not in self.available_voices:
            kokoro_voice = self.default_voice

        logger.info(f"[Kokoro] Synthesizing: voice={kokoro_voice}, speed={speed}, text_len={len(text)}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create prediction using version
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": self.version,
                    "input": {
                        "text": text,
                        "voice": kokoro_voice,
                        "speed": speed,
                    },
                },
            )

            if response.status_code != 201:
                logger.error(f"Replicate error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)

            prediction = response.json()
            prediction_id = prediction["id"]
            logger.info(f"[Kokoro] Created prediction: {prediction_id}")

            # Poll for completion
            poll_count = 0
            while True:
                poll_response = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )
                poll_count += 1
                result = poll_response.json()
                status = result["status"]

                if status == "succeeded":
                    output_url = result["output"]
                    logger.info(f"[TIMING] Kokoro prediction: {time.time() - start_time:.2f}s ({poll_count} polls)")

                    # Download audio file
                    download_start = time.time()
                    audio_response = await client.get(output_url)
                    if audio_response.status_code != 200:
                        raise HTTPException(status_code=500, detail="Failed to download audio")

                    audio_data = audio_response.content
                    logger.info(f"[TIMING] Kokoro download: {time.time() - download_start:.2f}s")
                    logger.info(f"[TIMING] Kokoro total: {time.time() - start_time:.2f}s")

                    return audio_data

                elif status == "failed":
                    error = result.get("error", "Unknown error")
                    logger.error(f"Kokoro prediction failed: {error}")
                    raise HTTPException(status_code=500, detail=f"TTS failed: {error}")

                elif status == "canceled":
                    raise HTTPException(status_code=500, detail="TTS prediction was canceled")

                # Wait before polling again
                await asyncio.sleep(0.5)


# =============================================================================
# Provider Registry
# =============================================================================

PROVIDERS = {
    "piper": PiperProvider,
    "kokoro": ReplicateKokoroProvider,
}


def get_provider() -> TTSProvider:
    """Get the configured TTS provider"""
    provider_name = os.getenv("TTS_PROVIDER", "piper").lower()

    if provider_name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown TTS provider: {provider_name}. Available: {available}")

    provider = PROVIDERS[provider_name]()

    if not provider.is_configured:
        raise ValueError(f"TTS provider '{provider_name}' is not configured. Check requirements.")

    logger.info(f"Using TTS provider: {provider.name}")
    return provider


# =============================================================================
# FastAPI Application
# =============================================================================

import asyncio

app = FastAPI(
    title="Multi-Provider TTS Adapter",
    description="OpenAI-compatible TTS endpoint with multiple backend providers",
    version="2.0.0",
)

# Initialize provider on startup
provider: Optional[TTSProvider] = None


@app.on_event("startup")
async def startup():
    global provider
    try:
        provider = get_provider()
    except ValueError as e:
        logger.error(f"Failed to initialize TTS provider: {e}")


class SpeechRequest(BaseModel):
    model: str = "tts-1"
    input: str
    voice: str = "nova"
    response_format: Optional[str] = "wav"
    speed: Optional[float] = 1.0


@app.post("/v1/audio/speech")
async def create_speech(request: SpeechRequest):
    """OpenAI-compatible TTS endpoint"""
    if not provider:
        raise HTTPException(
            status_code=500,
            detail="No TTS provider configured. Set TTS_PROVIDER and required configuration.",
        )

    if not request.input or not request.input.strip():
        raise HTTPException(status_code=400, detail="Input text is required")

    try:
        start_time = time.time()

        logger.info(f"[TTS] Request: provider={provider.name}, voice={request.voice}, text_len={len(request.input)}")

        audio_data = await provider.synthesize(
            text=request.input,
            voice=request.voice,
            speed=request.speed or 1.0,
        )

        total_time = time.time() - start_time
        logger.info(f"[TIMING] Total TTS request: {total_time:.2f}s")

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if provider else "degraded",
        "provider": provider.name if provider else None,
        "provider_configured": provider.is_configured if provider else False,
    }


@app.get("/providers")
async def list_providers():
    """List available TTS providers and their configuration status"""
    result = {}
    for name, cls in PROVIDERS.items():
        instance = cls()
        result[name] = {
            "name": instance.name,
            "configured": instance.is_configured,
        }
    return {
        "current": provider.name if provider else None,
        "available": result,
    }


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI compatibility)"""
    return {
        "data": [
            {"id": "tts-1", "object": "model", "owned_by": provider.name if provider else "unknown"},
            {"id": "tts-1-hd", "object": "model", "owned_by": provider.name if provider else "unknown"},
        ]
    }


@app.get("/v1/voices")
async def list_voices():
    """List available voices"""
    if not provider:
        return {"voices": [], "provider": None}

    voices = provider.get_voices()
    return {
        "voices": voices,
        "provider": provider.name,
    }


if __name__ == "__main__":
    import uvicorn
    Path(os.getenv("PIPER_VOICES_DIR", "/app/voices")).mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
