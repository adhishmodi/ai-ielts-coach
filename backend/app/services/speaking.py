import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.writing import validate_band


def calculate_speaking_band(
    fluency_band: float, lexical_band: float, grammar_band: float, pronunciation_band: float
) -> float:
    return round((fluency_band + lexical_band + grammar_band + pronunciation_band) / 4 * 2) / 2


def calculate_speaking_overall_band(part_bands: list[float]) -> float:
    if not part_bands:
        raise ValueError("At least one speaking part band is required")
    return round((sum(part_bands) / len(part_bands)) * 2) / 2


@dataclass
class DetailedSpeakingEvaluationResult:
    fluency_band: float
    lexical_band: float
    grammar_band: float
    pronunciation_band: float
    overall_band: float
    feedback: str
    strengths: list[str]
    improvements: list[str]
    evaluated_by: str = "ai"


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(line for line in lines if not line.strip().startswith("```"))
    return json.loads(cleaned)


class GeminiSpeakingEvaluator:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def evaluate(self, transcript: str, prompt: str, part_number: int) -> DetailedSpeakingEvaluationResult:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        instructions = f"""
You are an IELTS Speaking examiner.

Evaluate the candidate's transcript for Speaking Part {part_number}.
Use the IELTS Speaking criteria:
- Fluency and Coherence
- Lexical Resource
- Grammatical Range and Accuracy
- Pronunciation

Important limitation: this input is transcript-only. Do not pretend you can hear pronunciation.
For Pronunciation, provide a conservative provisional score based only on transcript evidence
and clearly state that pronunciation cannot be reliably assessed without audio.

Return ONLY valid JSON with this exact shape:
{{
  "fluency_band": 0.0,
  "lexical_band": 0.0,
  "grammar_band": 0.0,
  "pronunciation_band": 0.0,
  "feedback": "string",
  "strengths": ["string"],
  "improvements": ["string"]
}}

Candidate prompt:
{prompt}

Candidate transcript:
{transcript}
""".strip()
        payload = {
            "contents": [{"parts": [{"text": instructions}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _extract_json(text)
        bands = [
            validate_band(parsed["fluency_band"]),
            validate_band(parsed["lexical_band"]),
            validate_band(parsed["grammar_band"]),
            validate_band(parsed["pronunciation_band"]),
        ]
        return DetailedSpeakingEvaluationResult(
            fluency_band=bands[0],
            lexical_band=bands[1],
            grammar_band=bands[2],
            pronunciation_band=bands[3],
            overall_band=calculate_speaking_band(*bands),
            feedback=str(parsed.get("feedback", "")),
            strengths=[str(item) for item in parsed.get("strengths", [])],
            improvements=[str(item) for item in parsed.get("improvements", [])],
        )
