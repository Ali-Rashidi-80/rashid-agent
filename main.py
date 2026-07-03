#!/usr/bin/env python3
"""Deprecated entrypoint — use the v2 stack instead."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "DEPRECATED: root main.py was removed.\n"
        "  API:     .\\scripts\\dev.ps1\n"
        "  Worker:  .\\scripts\\dev-worker.ps1\n"
        "  UI:      cd frontend && npm run dev\n"
        "  Legacy:  python legacy/main.py  (old tkinter UI, not supported)\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
