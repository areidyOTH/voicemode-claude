"""
Multi-provider STT Adapter for OpenAI-compatible Speech-to-Text
Supports multiple backends: Groq, Rev.ai, Deepgram, etc.
"""

import asyncio
import os
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, File, UploadFile
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# STT Provider Abstract Base Class
# =============================================================================

class STTProvider(ABC):
    """Abstract base class for STT providers"""

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
    async def transcribe(self, audio_content: bytes, filename: str, content_type: str) -> str:
        """Transcribe audio and return text"""
        pass


# =============================================================================
# Groq Provider (Default)
# =============================================================================

class GroqProvider(STTProvider):
    """Groq Distil-Whisper provider - fast and cheap"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
        self.base_url = "https://api.groq.com/openai/v1"

    @property
    def name(self) -> str:
        return f"Groq ({self.model})"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, audio_content: bytes, filename: str, content_type: str) -> str:
        start_time = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (filename, audio_content, content_type)},
                data={
                    "model": self.model,
                    "language": "en",
                    "response_format": "json",
                },
            )

            elapsed = time.time() - start_time
            logger.info(f"[TIMING] Groq transcription: {elapsed:.2f}s")

            if response.status_code != 200:
                logger.error(f"Groq error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)

            result = response.json()
            return result.get("text", "")


# =============================================================================
# Rev.ai Provider
# =============================================================================

class RevAIProvider(STTProvider):
    """Rev.ai provider - batch transcription (slower, but established)"""

    def __init__(self):
        self.api_key = os.getenv("REV_AI_ACCESS_TOKEN")
        self.base_url = "https://api.rev.ai/speechtotext/v1"

    @property
    def name(self) -> str:
        return "Rev.ai"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, audio_content: bytes, filename: str, content_type: str) -> str:
        start_time = time.time()

        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"media": (filename, audio_content, content_type)}
        data = {
            "transcriber": "low_cost",
            "language": "en",
            "skip_punctuation": False,
            "filter_profanity": False,
            "remove_disfluencies": True,
            "remove_atmospherics": True,
            "speakers_count": 1,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create job
            upload_start = time.time()
            response = await client.post(
                f"{self.base_url}/jobs",
                headers=headers,
                files=files,
                data=data,
            )
            logger.info(f"[TIMING] Rev.ai job upload: {time.time() - upload_start:.2f}s")

            if response.status_code != 200:
                logger.error(f"Rev.ai error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)

            job_id = response.json()["id"]

            # Poll for completion
            poll_start = time.time()
            poll_count = 0
            while True:
                status_response = await client.get(
                    f"{self.base_url}/jobs/{job_id}",
                    headers=headers,
                )
                poll_count += 1
                status_data = status_response.json()

                if status_data["status"] == "transcribed":
                    logger.info(f"[TIMING] Rev.ai polling: {time.time() - poll_start:.2f}s ({poll_count} polls)")

                    # Get transcript
                    transcript_response = await client.get(
                        f"{self.base_url}/jobs/{job_id}/transcript",
                        headers={**headers, "Accept": "application/vnd.rev.transcript.v1.0+json"},
                    )

                    transcript_data = transcript_response.json()
                    logger.info(f"[TIMING] Rev.ai total: {time.time() - start_time:.2f}s")

                    # Extract text from monologues
                    text = " ".join([
                        element["value"]
                        for monolog in transcript_data.get("monologues", [])
                        for element in monolog.get("elements", [])
                        if element.get("type") == "text"
                    ])
                    return text

                elif status_data["status"] == "failed":
                    raise HTTPException(status_code=500, detail="Rev.ai transcription failed")

                await asyncio.sleep(1)


# =============================================================================
# Deepgram Provider (placeholder for future)
# =============================================================================

class DeepgramProvider(STTProvider):
    """Deepgram provider - real-time streaming capable"""

    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.base_url = "https://api.deepgram.com/v1"

    @property
    def name(self) -> str:
        return "Deepgram"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, audio_content: bytes, filename: str, content_type: str) -> str:
        start_time = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/listen?model=nova-2&language=en",
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": content_type or "audio/wav",
                },
                content=audio_content,
            )

            elapsed = time.time() - start_time
            logger.info(f"[TIMING] Deepgram transcription: {elapsed:.2f}s")

            if response.status_code != 200:
                logger.error(f"Deepgram error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)

            result = response.json()
            # Extract transcript from Deepgram response
            channels = result.get("results", {}).get("channels", [])
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    return alternatives[0].get("transcript", "")
            return ""


# =============================================================================
# Provider Registry
# =============================================================================

PROVIDERS = {
    "groq": GroqProvider,
    "revai": RevAIProvider,
    "deepgram": DeepgramProvider,
}

def get_provider() -> STTProvider:
    """Get the configured STT provider"""
    provider_name = os.getenv("STT_PROVIDER", "groq").lower()

    if provider_name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown STT provider: {provider_name}. Available: {available}")

    provider = PROVIDERS[provider_name]()

    if not provider.is_configured:
        raise ValueError(f"STT provider '{provider_name}' is not configured. Check API key.")

    logger.info(f"Using STT provider: {provider.name}")
    return provider


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Multi-Provider STT Adapter",
    description="OpenAI-compatible STT endpoint with multiple backend providers",
    version="2.0.0",
)

# Initialize provider on startup
provider: Optional[STTProvider] = None

@app.on_event("startup")
async def startup():
    global provider
    try:
        provider = get_provider()
    except ValueError as e:
        logger.error(f"Failed to initialize STT provider: {e}")


@app.post("/v1/audio/transcriptions")
async def create_transcription(file: UploadFile = File(...)):
    """OpenAI-compatible transcription endpoint"""
    if not provider:
        raise HTTPException(
            status_code=500,
            detail="No STT provider configured. Set STT_PROVIDER and required API key.",
        )

    try:
        start_time = time.time()

        audio_content = await file.read()
        logger.info(f"[TIMING] Audio size: {len(audio_content)} bytes, provider: {provider.name}")

        text = await provider.transcribe(
            audio_content=audio_content,
            filename=file.filename or "audio.wav",
            content_type=file.content_type or "audio/wav",
        )

        total_time = time.time() - start_time
        logger.info(f"[TIMING] Total request time: {total_time:.2f}s")

        return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "provider": provider.name if provider else None,
        "provider_configured": provider.is_configured if provider else False,
    }


@app.get("/providers")
async def list_providers():
    """List available STT providers and their configuration status"""
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")
