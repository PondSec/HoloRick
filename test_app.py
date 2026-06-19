import io
import pytest
import app as holo


def guest_headers(client, **extra):
    response = client.get("/api/me", headers=extra)
    data = response.get_json()
    headers = {
        "X-CSRF-Token": data["csrf_token"],
        "X-Guest-Token": data["guest_token"],
    }
    headers.update(extra)
    return headers


@pytest.fixture(autouse=True)
def clean_public_usage():
    old_msg = holo.get_setting("public_message_limit", "3")
    old_attach = holo.get_setting("public_attachment_limit", "1")
    with holo.db() as con:
        con.execute("DELETE FROM public_usage")
        con.commit()
    yield
    holo.set_setting("public_message_limit", old_msg)
    holo.set_setting("public_attachment_limit", old_attach)
    with holo.db() as con:
        con.execute("DELETE FROM public_usage")
        con.commit()


def test_guest_identity_survives_ip_change_and_allows_family_independence(monkeypatch):
    monkeypatch.setattr(holo, "call_llm", lambda messages, **kwargs: "ok")
    holo.set_setting("public_message_limit", "1")
    client_a = holo.app.test_client()
    headers_a = guest_headers(client_a, **{"User-Agent": "BrowserA", "Accept-Language": "de"})

    assert client_a.post("/api/send", data={"message": "eins", "chat_id": "0"}, headers=headers_a, environ_base={"REMOTE_ADDR": "1.1.1.1"}).status_code == 200
    assert client_a.post("/api/send", data={"message": "zwei", "chat_id": "0"}, headers=headers_a, environ_base={"REMOTE_ADDR": "2.2.2.2"}).status_code == 429

    client_b = holo.app.test_client()
    headers_b = guest_headers(client_b, **{"User-Agent": "BrowserB", "Accept-Language": "de"})
    assert client_b.post("/api/send", data={"message": "familie", "chat_id": "0"}, headers=headers_b, environ_base={"REMOTE_ADDR": "1.1.1.1"}).status_code == 200


def test_guest_text_attachment_upload_works(monkeypatch):
    monkeypatch.setattr(holo, "call_llm", lambda messages, **kwargs: "saw file" if "DATEI note.txt" in messages[-1]["content"] else "missing")
    holo.set_setting("public_message_limit", "20")
    holo.set_setting("public_attachment_limit", "3")
    c = holo.app.test_client()
    headers = guest_headers(c, **{"User-Agent": "Uploader"})
    data = {
        "message": "analysiere",
        "chat_id": "0",
        "files": (io.BytesIO(b"hello attachment"), "note.txt"),
    }
    r = c.post("/api/send", data=data, content_type="multipart/form-data", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["assistant_message"]["content"] == "saw file"


def test_long_history_is_compacted_before_provider_call(monkeypatch):
    captured = {}

    class FakeMessage:
        content = "ok"

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletion:
        choices = [FakeChoice()]

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return FakeCompletion()

    monkeypatch.setattr(holo, "MODEL_REQUEST_TOKEN_BUDGET", 2200)
    monkeypatch.setattr(holo.groq_key_pool, "chat_completion_create", fake_completion)
    messages = [{"role": "system", "content": "system"}]
    for _ in range(14):
        messages.append({"role": "user", "content": "u" * 4000})
        messages.append({"role": "assistant", "content": "a" * 4000})
    messages.append({"role": "user", "content": "kurze neue frage"})

    assert holo.call_llm(messages, max_tokens=1600) == "ok"
    assert len(captured["messages"]) < len(messages)
    assert holo.estimate_messages_tokens(captured["messages"]) + captured["max_completion_tokens"] <= holo.MODEL_REQUEST_TOKEN_BUDGET
    assert captured["messages"][-1]["content"] == "kurze neue frage"


def test_groq_tpm_413_is_treated_as_rate_limit():
    class FakeProviderError(Exception):
        status_code = 413

    exc = FakeProviderError(
        "Request too large for model on tokens per minute (TPM): "
        "Limit 8000, Requested 8871, code rate_limit_exceeded"
    )
    assert holo.is_rate_limit_error(exc)


def test_model_reasoning_blocks_are_removed():
    text = "<think>interner kram</think>\n\nSichtbare Antwort."
    assert holo.strip_model_reasoning(text) == "Sichtbare Antwort."
