"""MAJLISH license check - talks to your key panel (same logic as the Termux tool)."""
import json
import time

import requests

# Change this if MAJLISH gets its own panel.
AUTH_BASE_URL = "https://goatkeypanel.pythonanywhere.com"
AUTH_ENDPOINTS = [
    AUTH_BASE_URL + "/api/verify",
    AUTH_BASE_URL + "/verify",
    AUTH_BASE_URL + "/api/validate",
]


def _auth_json(resp):
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _auth_request(key, device_id, device_name):
    payload = {
        "key": key,
        "device_id": device_id,
        "hwid": device_id,
        "device_name": device_name or "MAJLISH Android",
    }
    last_error = None
    for url in AUTH_ENDPOINTS:
        for _attempt in range(2):
            try:
                resp = requests.get(url, params=payload, timeout=30)
                if resp.status_code in (404, 405):
                    resp = requests.post(url, json=payload, timeout=30)
                data = _auth_json(resp)
                if resp.status_code in (404, 405):
                    if data.get("message") or data.get("status") or data.get("error"):
                        return resp.status_code, data
                    break  # wrong route -> next endpoint
                if resp.status_code >= 500:
                    last_error = "HTTP %s" % resp.status_code
                    time.sleep(1.0)
                    continue
                return resp.status_code, data
            except requests.RequestException as exc:
                last_error = str(exc)
                time.sleep(1.0)
    raise requests.RequestException(last_error or "AUTH ENDPOINT NOT FOUND")


def _auth_is_success(data):
    status = str(data.get("status", "")).strip().lower()
    if status in ("success", "ok", "valid", "active", "authorized"):
        return True
    return data.get("success") is True or data.get("valid") is True


def _auth_reason(data, default):
    for name in ("message", "error", "reason"):
        value = data.get(name)
        if value:
            return str(value).upper()
    return default


def verify_key(key, device_id, device_name):
    """Returns a JSON string: {"ok": bool, "reason": str, "expiry": str}."""
    key = (key or "").strip().strip('`"\'')
    if not key:
        return json.dumps({"ok": False, "reason": "NO KEY ENTERED", "expiry": ""})
    try:
        status, data = _auth_request(key, device_id, device_name)
        if status == 200 and _auth_is_success(data):
            expiry = data.get("expires_at") or data.get("expiry") or data.get("expires") or "N/A"
            return json.dumps({"ok": True, "reason": "", "expiry": str(expiry), "key": key})
        reason = _auth_reason(data, "INVALID KEY" if status == 200 else "ACCESS DENIED")
        return json.dumps({"ok": False, "reason": reason, "expiry": ""})
    except requests.Timeout:
        return json.dumps({"ok": False, "reason": "REQUEST TIMEOUT", "expiry": "", "network": True})
    except requests.RequestException as exc:
        return json.dumps({"ok": False, "reason": str(exc)[:120].upper(), "expiry": "", "network": True})
    except Exception as exc:  # noqa
        return json.dumps({"ok": False, "reason": "ACCESS DENIED (%s)" % type(exc).__name__, "expiry": ""})
