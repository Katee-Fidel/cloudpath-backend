import asyncio
import json
import logging

import httpx
import pytest
from fastapi import HTTPException

from app.ai import generate
from app.schemas import QuizRequest, StudyRequest


PRIVATE_KEY = "private-test-key-do-not-log"
PRIVATE_PROMPT = "private-learner-question-do-not-log"
PRIVATE_NOTES = "private-uploaded-notes-do-not-log"
PRIVATE_OUTPUT = "private-provider-output-do-not-log"
PUBLIC_ERROR = "AI service failed or returned invalid content. Please retry."


@pytest.fixture
def live_ai(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("LLM_API_KEY", PRIVATE_KEY)
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_MODEL", "llama-3.1-8b-instant")


def assert_safe_failure(caplog, request, *, kind="buddy", error_class, status):
    with caplog.at_level(logging.ERROR, logger="app.ai"):
        with pytest.raises(HTTPException) as error:
            asyncio.run(generate(kind, request, [{"chunk": 1, "text": PRIVATE_NOTES}]))

    assert error.value.status_code == 502
    assert error.value.detail == PUBLIC_ERROR
    records = [record for record in caplog.records if record.name == "app.ai"]
    assert len(records) == 1
    assert records[0].getMessage() == (
        f"AI generation failed: task={kind} error_class={error_class} "
        f"upstream_status={status}"
    )
    assert records[0].exc_info is None
    for private_value in (PRIVATE_KEY, PRIVATE_PROMPT, PRIVATE_NOTES, PRIVATE_OUTPUT):
        assert private_value not in caplog.text
        assert private_value not in error.value.detail


@pytest.mark.parametrize("status", [400, 401, 429, 503])
def test_provider_status_logged_without_private_body(live_ai, monkeypatch, caplog, status):
    async def post(self, url, **kwargs):
        return httpx.Response(
            status,
            json={"error": {"message": " ".join((PRIVATE_KEY, PRIVATE_NOTES, PRIVATE_OUTPUT))}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert_safe_failure(
        caplog, StudyRequest(prompt=PRIVATE_PROMPT),
        error_class="HTTPStatusError", status=status,
    )


def test_timeout_logged_without_exception_message(live_ai, monkeypatch, caplog):
    async def post(self, url, **kwargs):
        raise httpx.ReadTimeout(PRIVATE_KEY + PRIVATE_PROMPT + PRIVATE_NOTES)

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert_safe_failure(
        caplog, StudyRequest(prompt=PRIVATE_PROMPT),
        error_class="ReadTimeout", status=None,
    )


@pytest.mark.parametrize(
    "payload, error_class",
    [(PRIVATE_OUTPUT, "JSONDecodeError"), ({"answer": PRIVATE_OUTPUT}, "KeyError")],
)
def test_unreadable_provider_response_logged(live_ai, monkeypatch, caplog, payload, error_class):
    async def post(self, url, **kwargs):
        if isinstance(payload, str):
            return httpx.Response(200, text=payload, request=httpx.Request("POST", url))
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert_safe_failure(
        caplog, StudyRequest(prompt=PRIVATE_PROMPT), error_class=error_class, status=None,
    )


@pytest.mark.parametrize(
    "kind, result, error_class",
    [
        ("buddy", {"answer": {"private": PRIVATE_OUTPUT}}, "ValueError"),
        ("quiz", {"questions": PRIVATE_OUTPUT}, "ValidationError"),
    ],
)
def test_invalid_generated_content_logged_safely(live_ai, monkeypatch, caplog, kind, result, error_class):
    async def post(self, url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(result)}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    request = QuizRequest(prompt=PRIVATE_PROMPT) if kind == "quiz" else StudyRequest(prompt=PRIVATE_PROMPT)
    assert_safe_failure(caplog, request, kind=kind, error_class=error_class, status=None)


def test_successful_buddy_response_has_no_error_log(live_ai, monkeypatch, caplog):
    async def post(self, url, **kwargs):
        assert url == "https://api.groq.com/openai/v1/chat/completions"
        assert kwargs["json"]["model"] == "llama-3.1-8b-instant"
        assert kwargs["headers"]["Authorization"] == f"Bearer {PRIVATE_KEY}"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"answer": PRIVATE_OUTPUT})}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    result = asyncio.run(generate("buddy", StudyRequest(prompt=PRIVATE_PROMPT), []))
    assert result == {"answer": PRIVATE_OUTPUT, "mode": "live"}
    assert not [record for record in caplog.records if record.name == "app.ai"]
