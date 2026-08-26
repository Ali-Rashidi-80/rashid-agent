#!/usr/bin/env python3
"""Fail if committed *.example env templates contain secret-looking values."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEY_PARTS = ("password", "secret", "token", "api_key", "encryption")


def main() -> int:
    bad: list[str] = []
    for path in ROOT.rglob("*.example*"):
        rel = path.relative_to(ROOT)
        if any(p in rel.parts for p in ("node_modules", ".venv", "venv", ".git")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            key, _, value = s.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not value:
                continue
            kl = key.lower()
            if any(part in kl for part in SECRET_KEY_PARTS):
                bad.append(f"{rel}:{i}:{key}=***")
    if bad:
        print("SENSITIVE_VALUES_IN_EXAMPLES:")
        print("\n".join(bad))
        return 1
    print("examples_clean_no_secret_values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
