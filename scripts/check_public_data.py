#!/usr/bin/env python3
# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Fail when public source files contain likely secrets or real IP addresses."""

from __future__ import annotations

import ipaddress
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
TEXT_SUFFIXES = {
    "",
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".example",
    ".txt",
}
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")

# Build signatures in fragments so the scanner does not report its own source.
SECRET_SIGNATURES = {
    "private key": "BEGIN " + "PRIVATE KEY",
    "provider access key": "AK" + "IA" + r"[A-Z0-9]{16}",
    "GitHub token": "gh" + r"[pousr]_[A-Za-z0-9]{20,}",
    "generic bearer token": "Bearer" + r"\s+[A-Za-z0-9._~+/=-]{20,}",
}


def is_allowed_ip(value: str) -> bool:
    """Allow only loopback, unspecified, and documentation-only address blocks."""

    address = ipaddress.ip_address(value)
    documentation_ranges = (
        ipaddress.ip_network("192.0.2.0/24"),
        ipaddress.ip_network("198.51.100.0/24"),
        ipaddress.ip_network("203.0.113.0/24"),
    )
    return (
        address.is_loopback
        or address.is_unspecified
        or any(address in network for network in documentation_ranges)
    )


def candidate_files() -> list[Path]:
    """Return public text files without walking caches or repository metadata."""

    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in SKIP_PARTS for part in path.parts)
        and (path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE"})
    ]


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(ROOT)

        for match in IPV4.finditer(text):
            try:
                if not is_allowed_ip(match.group()):
                    findings.append(f"{relative}: real IP address: {match.group()}")
            except ValueError:
                continue

        for label, signature in SECRET_SIGNATURES.items():
            if re.search(signature, text):
                findings.append(f"{relative}: possible {label}")

    if findings:
        print("Public-data gate failed:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1

    print("Public-data gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
