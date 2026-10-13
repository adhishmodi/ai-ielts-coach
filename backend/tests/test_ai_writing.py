import httpx
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.writing import GeminiWritingEvaluator


def fake_response(payload, status_code=200):
    r = Mock()
    r.status_code = status_code
    r.raise_for_status = Mock()
    r.json = Mock(return_value=payload)
    return r


def valid_payload():
    return {"candidates": [{"content": {"parts": [{"text": '{"task_band":7,"coherence_band":6.5,"lexical_band":7,"grammar_band":6.5,"feedback":"Good","strengths":["clear"],"improvements":["develop"]}'}]}}]}


@pytest.mark.asyncio
async def test_gemini_essay_evaluation():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response(valid_payload())) as post:
        result = await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")
    assert result.task_response_band == 7
    assert result.task_achievement_band is None
    assert result.overall_band == 7
    assert result.evaluated_by == "ai"
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "key"
    assert "key" not in post.call_args.args[0]


@pytest.mark.asyncio
async def test_gemini_task1_evaluation():
    payload = valid_payload()
    payload["candidates"][0]["content"]["parts"][0]["text"] = '{"task_band":6,"coherence_band":6,"lexical_band":6,"grammar_band":6,"feedback":"ok","strengths":[],"improvements":[]}'
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response(payload)):
        result = await GeminiWritingEvaluator("key").evaluate("response", "prompt", "graph")
    assert result.task_achievement_band == 6
    assert result.task_response_band is None


@pytest.mark.asyncio
async def test_gemini_invalid_payload():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response({"candidates": []})):
        with pytest.raises(ValueError, match="invalid evaluation response"):
            await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_score", ['"7"', "7.25", "10", "-0.5", "null", "true"])
async def test_gemini_rejects_invalid_scores(bad_score):
    payload = valid_payload()
    payload["candidates"][0]["content"]["parts"][0]["text"] = '{"task_band":' + bad_score + ',"coherence_band":6.5,"lexical_band":7,"grammar_band":6.5,"feedback":"Good","strengths":["clear"],"improvements":["develop"]}'
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response(payload)):
        with pytest.raises(ValueError, match="invalid evaluation response"):
            await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")


@pytest.mark.asyncio
async def test_gemini_retries_transient_status_then_succeeds():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[fake_response({}, 503), fake_response(valid_payload())]) as post:
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")
    assert result.overall_band == 7
    assert post.await_count == 2


@pytest.mark.asyncio
async def test_gemini_retries_network_error_then_succeeds():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[httpx.ConnectError("temporary"), fake_response(valid_payload())]) as post:
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")
    assert result.overall_band == 7
    assert post.await_count == 2


@pytest.mark.asyncio
async def test_gemini_http_error_does_not_leak_provider_body():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response({"secret": "provider details"}, 401)):
        with pytest.raises(RuntimeError, match="HTTP 401") as exc:
            await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")
    assert "provider details" not in str(exc.value)


@pytest.mark.asyncio
async def test_gemini_rejects_invalid_feedback_schema():
    payload = valid_payload()
    payload["candidates"][0]["content"]["parts"][0]["text"] = '{"task_band":7,"coherence_band":6.5,"lexical_band":7,"grammar_band":6.5,"feedback":"","strengths":"clear","improvements":["develop"]}'
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fake_response(payload)):
        with pytest.raises(ValueError, match="invalid evaluation response"):
            await GeminiWritingEvaluator("key").evaluate("response", "prompt", "essay")
