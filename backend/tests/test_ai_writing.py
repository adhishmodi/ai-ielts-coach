import pytest
from unittest.mock import AsyncMock, patch
from app.services.writing import GeminiWritingEvaluator

def fake_response(payload):
    r=AsyncMock()
    r.raise_for_status=AsyncMock()
    r.json.return_value=payload
    return r

@pytest.mark.asyncio
async def test_gemini_essay_evaluation():
    payload={"candidates":[{"content":{"parts":[{"text":"{\"task_band\":7,\"coherence_band\":6.5,\"lexical_band\":7,\"grammar_band\":6.5,\"feedback\":\"Good\",\"strengths\":[\"clear\"],\"improvements\":[\"develop\"]}"}]}}]}
    with patch("httpx.AsyncClient.post",new_callable=AsyncMock,return_value=fake_response(payload)):
        result=await GeminiWritingEvaluator("key").evaluate("response","prompt","essay")
    assert result.task_response_band==7
    assert result.task_achievement_band is None
    assert result.overall_band==7
    assert result.evaluated_by=="ai"

@pytest.mark.asyncio
async def test_gemini_task1_evaluation():
    payload={"candidates":[{"content":{"parts":[{"text":"{\"task_band\":6,\"coherence_band\":6,\"lexical_band\":6,\"grammar_band\":6,\"feedback\":\"ok\",\"strengths\":[],\"improvements\":[]}"}]}}]}
    with patch("httpx.AsyncClient.post",new_callable=AsyncMock,return_value=fake_response(payload)):
        result=await GeminiWritingEvaluator("key").evaluate("response","prompt","graph")
    assert result.task_achievement_band==6
    assert result.task_response_band is None

@pytest.mark.asyncio
async def test_gemini_invalid_payload():
    with patch("httpx.AsyncClient.post",new_callable=AsyncMock,return_value=fake_response({"candidates":[]})):
        with pytest.raises(ValueError): await GeminiWritingEvaluator("key").evaluate("response","prompt","essay")

@pytest.mark.asyncio
async def test_gemini_http_error():
    response=AsyncMock()
    response.raise_for_status.side_effect=RuntimeError("boom")
    with patch("httpx.AsyncClient.post",new_callable=AsyncMock,return_value=response):
        with pytest.raises(RuntimeError): await GeminiWritingEvaluator("key").evaluate("response","prompt","essay")
