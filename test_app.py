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



def auth_headers(client):
    data = client.get("/api/me").get_json()
    return {"X-CSRF-Token": data["csrf_token"]}


def test_project_chat_send_uses_project_context(monkeypatch):
    captured = {}

    def fake_llm(messages, **kwargs):
        if "Projekt: Testprojekt" in messages[0]["content"]:
            captured["messages"] = messages
            return "Projektantwort"
        return "Projekttitel"

    monkeypatch.setattr(holo, "call_llm", fake_llm)
    client = holo.app.test_client()
    headers = auth_headers(client)
    email = "project-test@example.com"
    with holo.db() as con:
        con.execute("DELETE FROM users WHERE email=?", (email,))
        con.commit()

    register = client.post(
        "/api/register",
        json={
            "display_name": "Project Tester",
            "email": email,
            "password": "super-sicheres-passwort-123",
            "privacy_accepted": True,
            "terms_accepted": True,
        },
        headers=headers,
    )
    assert register.status_code == 200
    headers = auth_headers(client)

    project = client.post("/api/projects", json={"name": "Testprojekt", "description": "Shared Ziel"}, headers=headers)
    assert project.status_code == 200
    project_id = project.get_json()["id"]
    assert client.put(
        f"/api/projects/{project_id}",
        json={"name": "Testprojekt", "description": "Shared Ziel", "shared_context": "Immer duzen."},
        headers=headers,
    ).status_code == 200

    response = client.post("/api/send", data={"message": "Hallo", "chat_id": "0", "project_id": str(project_id)}, headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["assistant_message"]["content"] == "Projektantwort"

    system_prompt = captured["messages"][0]["content"]
    assert "Projekt: Testprojekt" in system_prompt
    assert "Beschreibung: Shared Ziel" in system_prompt
    assert "Manueller Projektkontext" in system_prompt
    assert "Immer duzen." in system_prompt


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


def register_user(client, email):
    headers = auth_headers(client)
    with holo.db() as con:
        con.execute("DELETE FROM users WHERE email=?", (email,))
        con.commit()
    response = client.post(
        "/api/register",
        json={
            "display_name": "Share Tester",
            "email": email,
            "password": "super-sicheres-passwort-123",
            "privacy_accepted": True,
            "terms_accepted": True,
        },
        headers=headers,
    )
    assert response.status_code == 200
    return auth_headers(client)


def test_shared_chat_link_allows_guest_to_read_and_write(monkeypatch):
    monkeypatch.setattr(holo, "call_llm", lambda messages, **kwargs: "shared ok")
    owner = holo.app.test_client()
    owner_headers = register_user(owner, "share-owner@example.com")
    sent = owner.post("/api/send", data={"message": "Start", "chat_id": "0"}, headers=owner_headers)
    assert sent.status_code == 200
    chat_id = sent.get_json()["chat_id"]

    shared = owner.post(f"/api/chats/{chat_id}/share", headers=owner_headers)
    assert shared.status_code == 200
    token = shared.get_json()["token"]
    assert len(token) >= 32

    guest = holo.app.test_client()
    guest_headers_data = guest_headers(guest, **{"User-Agent": "ShareGuest"})
    detail = guest.get(f"/api/shared/{token}", headers=guest_headers_data)
    assert detail.status_code == 200
    assert [m["content"] for m in detail.get_json()["messages"] if m["role"] == "user"] == ["Start"]

    reply = guest.post("/api/send", data={"message": "Gast schreibt", "share_token": token}, headers=guest_headers_data)
    assert reply.status_code == 200
    after = owner.get(f"/api/chats/{chat_id}", headers=owner_headers)
    assert "Gast schreibt" in [m["content"] for m in after.get_json()["messages"]]


def test_project_delete_removes_project_chats(monkeypatch):
    monkeypatch.setattr(holo, "call_llm", lambda messages, **kwargs: "ok")
    client = holo.app.test_client()
    headers = register_user(client, "project-delete@example.com")
    project = client.post("/api/projects", json={"name": "Weg", "description": ""}, headers=headers)
    project_id = project.get_json()["id"]
    sent = client.post("/api/send", data={"message": "Hallo", "chat_id": "0", "project_id": str(project_id)}, headers=headers)
    chat_id = sent.get_json()["chat_id"]

    deleted = client.delete(f"/api/projects/{project_id}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/projects/{project_id}", headers=headers).status_code == 404
    assert client.get(f"/api/chats/{chat_id}", headers=headers).status_code == 404


def test_markdown_does_not_autolink_filenames_but_keeps_urls():
    filename_html = holo.render_markdown("server.py")
    url_html = holo.render_markdown("https://example.com")
    assert "<a" not in filename_html
    assert "server.py" in filename_html
    assert "<a" in url_html
    assert "text-decoration" not in url_html
