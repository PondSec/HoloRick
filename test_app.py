import io
import pytest
import app as holo


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
    r = client_a.get("/api/me", headers={"User-Agent": "BrowserA", "Accept-Language": "de"})
    token_a = r.get_json()["guest_token"]

    assert client_a.post("/api/send", data={"message": "eins", "chat_id": "0"}, headers={"X-Guest-Token": token_a, "User-Agent": "BrowserA", "Accept-Language": "de"}, environ_base={"REMOTE_ADDR": "1.1.1.1"}).status_code == 200
    assert client_a.post("/api/send", data={"message": "zwei", "chat_id": "0"}, headers={"X-Guest-Token": token_a, "User-Agent": "BrowserA", "Accept-Language": "de"}, environ_base={"REMOTE_ADDR": "2.2.2.2"}).status_code == 429

    client_b = holo.app.test_client()
    r = client_b.get("/api/me", headers={"User-Agent": "BrowserB", "Accept-Language": "de"}, environ_base={"REMOTE_ADDR": "1.1.1.1"})
    token_b = r.get_json()["guest_token"]
    assert client_b.post("/api/send", data={"message": "familie", "chat_id": "0"}, headers={"X-Guest-Token": token_b, "User-Agent": "BrowserB", "Accept-Language": "de"}, environ_base={"REMOTE_ADDR": "1.1.1.1"}).status_code == 200


def test_guest_text_attachment_upload_works(monkeypatch):
    monkeypatch.setattr(holo, "call_llm", lambda messages, **kwargs: "saw file" if "DATEI note.txt" in messages[-1]["content"] else "missing")
    holo.set_setting("public_message_limit", "20")
    holo.set_setting("public_attachment_limit", "3")
    c = holo.app.test_client()
    token = c.get("/api/me", headers={"User-Agent": "Uploader"}).get_json()["guest_token"]
    data = {
        "message": "analysiere",
        "chat_id": "0",
        "files": (io.BytesIO(b"hello attachment"), "note.txt"),
    }
    r = c.post("/api/send", data=data, content_type="multipart/form-data", headers={"X-Guest-Token": token, "User-Agent": "Uploader"})
    assert r.status_code == 200
    assert r.get_json()["assistant_message"]["content"] == "saw file"
