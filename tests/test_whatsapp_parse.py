import hashlib
import hmac
import json

from app.whatsapp_parse import extract_messages, verify_signature

SECRET = "test-secret"


def sign(body: bytes, secret=SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


PAYLOAD = {"entry": [{"changes": [{"field": "messages", "value": {
    "contacts": [{"wa_id": "919800000001", "profile": {"name": "Ramesh Broker"}}],
    "messages": [
        {"id": "wamid.A", "from": "919800000001", "timestamp": "1762400000", "type": "text",
         "text": {"body": "3 BHK Bopal 85L"}},
        {"id": "wamid.B", "from": "919800000001", "timestamp": "1762400001", "type": "image",
         "image": {"id": "MEDIA1", "mime_type": "image/jpeg", "caption": "2 BHK SG Highway rent 30k"}},
    ]}}]}]}


def test_signature_valid_and_invalid():
    body = json.dumps(PAYLOAD).encode()
    assert verify_signature(body, sign(body), SECRET)
    assert not verify_signature(body, sign(body, "other"), SECRET)
    assert not verify_signature(body, None, SECRET)
    assert not verify_signature(body, sign(body), "")  # no secret configured -> fail closed


def test_extract_text_and_image():
    msgs = extract_messages(PAYLOAD)
    assert [m["wamid"] for m in msgs] == ["wamid.A", "wamid.B"]
    assert msgs[0]["text"] == "3 BHK Bopal 85L" and msgs[0]["sender_name"] == "Ramesh Broker"
    assert msgs[1]["media_id"] == "MEDIA1" and msgs[1]["text"].startswith("2 BHK")


def test_status_callbacks_yield_nothing():
    status = {"entry": [{"changes": [{"field": "messages", "value": {"statuses": [{"id": "x"}]}}]}]}
    assert extract_messages(status) == []


if __name__ == "__main__":
    test_signature_valid_and_invalid(); test_extract_text_and_image(); test_status_callbacks_yield_nothing()
    print("all passed")
