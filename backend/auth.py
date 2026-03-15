import hashlib
import hmac
import urllib.parse
import os
import json

from fastapi import Header, HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN", "")


def validate_init_data(authorization: str = Header(...)) -> dict:
    """Validates Telegram WebApp initData. Returns parsed user dict."""
    # During development, allow test init data
    if authorization == "test_init_data":
        return {"id": 12345, "first_name": "Test", "username": "test"}

    try:
        # authorization is the raw initData string from tg.initData
        parsed = dict(urllib.parse.parse_qsl(authorization, keep_blank_values=True))
        received_hash = parsed.pop("hash", "")

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            raise HTTPException(status_code=401, detail="Invalid initData")

        user_str = parsed.get("user", "{}")
        return json.loads(user_str)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth error: {e}")
