import base64
from typing import Any

import httpx


class GeminiAudioTranscriber:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload: dict[str, Any] = {
            "contents": [{
                "parts": [
                    {"text": "Transcribe the spoken audio verbatim in English. Return only the words spoken. Do not summarize, explain, or add speaker labels."},
                    {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(audio).decode("ascii")}},
                ]
            }],
            "generationConfig": {"temperature": 0},
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            transcript = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ValueError("Speech transcription returned an invalid response") from exc
        if not transcript:
            raise ValueError("No speech could be transcribed from the recording")
        return transcript
