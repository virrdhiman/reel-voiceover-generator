#!/usr/bin/env python3
"""Wait for OTP on PC — stdlib only. Phone forwards SMS to https://otp.flightpath.co.in"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Same contract as sms-otp-forwarder/python/otp_shared.py
import re
import time

OTP_DIGIT_MIN = 4
OTP_DIGIT_MAX = 8
OTP_RE = re.compile(rf"^\d{{{OTP_DIGIT_MIN},{OTP_DIGIT_MAX}}}$")
OTP_TTL_SECONDS = 600
DEFAULT_BASE = "https://otp.flightpath.co.in"
DEFAULT_WAIT_TIMEOUT = 120

BASE = os.environ.get("OTP_PLATFORM_URL", DEFAULT_BASE).rstrip("/")
OTP_KEY = "FP-W2DPZ7TH"


def normalize_key(key: str) -> str:
    s = key.strip().upper()
    return s if s.startswith("FP-") else f"FP-{s.replace('FP-', '')}"


def validate_otp(otp: str) -> str:
    otp = str(otp)
    if not OTP_RE.match(otp):
        raise ValueError(
            f"Invalid OTP (expected {OTP_DIGIT_MIN}-{OTP_DIGIT_MAX} digits): {otp!r}"
        )
    return otp


def validate_wait_response(data: dict) -> str:
    otp = validate_otp(data["otp"])
    age = data.get("ageSeconds")
    if age is not None and age > OTP_TTL_SECONDS:
        raise ValueError(f"OTP expired ({age}s old; TTL {OTP_TTL_SECONDS}s)")
    return otp


def wait_for_otp(key: str = OTP_KEY, timeout: int = DEFAULT_WAIT_TIMEOUT) -> str:
    """Block until a fresh OTP arrives (4-8 digits). OTP expires on server after 5 min."""
    key = normalize_key(key)
    since = int(time.time() * 1000)
    q = urllib.parse.urlencode({"key": key, "timeout": timeout, "since": since})
    url = f"{BASE}/v1/otp/wait?{q}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout + 15) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body).get("error", body)
        except Exception:
            msg = body
        raise RuntimeError(f"OTP wait failed ({e.code}): {msg}") from e
    return validate_wait_response(data)


def get_latest_otp(key: str = OTP_KEY) -> str | None:
    """Return latest OTP if still within 5-minute server cache, else None."""
    key = normalize_key(key)
    url = f"{BASE}/v1/otp/latest?{urllib.parse.urlencode({'key': key})}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            if data.get("ageSeconds", 0) > OTP_TTL_SECONDS:
                return None
            return validate_otp(str(data["otp"]))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


if __name__ == "__main__":
    try:
        print(wait_for_otp())
    except (RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
