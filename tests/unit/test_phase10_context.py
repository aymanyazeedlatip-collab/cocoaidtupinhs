from __future__ import annotations

from app.coco_pilot.context import redact_payload


def test_phase10_redaction_removes_pii_keys_and_inline_contacts():
    payload = {
        "farmer_name": "Private Farmer",
        "email": "private@example.com",
        "nested": {"phone": "09171234567", "notes": "Call 09181234567 or x@y.com"},
        "farm_id": "safe-id",
    }
    redacted, count = redact_payload(payload)
    assert "farmer_name" not in redacted
    assert "email" not in redacted
    assert "phone" not in redacted["nested"]
    assert "Private Farmer" not in str(redacted)
    assert "09181234567" not in str(redacted)
    assert "x@y.com" not in str(redacted)
    assert redacted["farm_id"] == "safe-id"
    assert count >= 5
