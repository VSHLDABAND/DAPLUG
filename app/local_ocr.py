"""Optional, fully local macOS OCR using Apple's Vision framework.

No network or paid service is used. OCR gracefully reports unavailable on systems
without macOS Vision or the Swift command-line toolchain.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SWIFT_SCRIPT = ROOT / "scripts" / "ocr_broker_media.swift"
MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".heic", ".pdf"}


def extract_text_by_media(paths: Iterable[Path]) -> dict:
    """OCR a batch in one Swift/Vision process and return text keyed by absolute path."""
    candidates = list(dict.fromkeys(
        Path(p).resolve() for p in paths
        if Path(p).is_file() and Path(p).suffix.lower() in MEDIA_SUFFIXES
    ))
    if not candidates:
        return {"status": "not_applicable", "texts": {}, "detail": "No image or PDF attachments."}
    if platform.system() != "Darwin":
        return {"status": "unavailable", "texts": {}, "detail": "Apple Vision OCR requires macOS."}
    swift = shutil.which("swift")
    if not swift or not SWIFT_SCRIPT.is_file():
        return {"status": "unavailable", "texts": {}, "detail": "Install the free Xcode Command Line Tools to enable built-in macOS Vision OCR."}

    # A single export can contain hundreds of images. Process up to 200 per run
    # in one Swift process to avoid recompiling the OCR script once per message.
    partial = len(candidates) > 200
    candidates = candidates[:200]
    try:
        result = subprocess.run(
            [swift, str(SWIFT_SCRIPT), *[str(p) for p in candidates]],
            capture_output=True, text=True, timeout=300, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "texts": {}, "detail": "Local OCR timed out. Import a smaller group export or reprocess fewer attachments."}
    except OSError as exc:
        return {"status": "error", "texts": {}, "detail": str(exc)[:300]}
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Vision OCR failed.").strip()
        return {"status": "error", "texts": {}, "detail": detail[-600:]}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "texts": {}, "detail": "OCR returned an unreadable result."}
    texts = {}
    for row in payload if isinstance(payload, list) else []:
        path = str(Path(row.get("path", "")).resolve())
        value = str(row.get("text", "")).strip()
        if path:
            texts[path] = value
    any_text = any(texts.values())
    status = "partial" if partial else ("completed" if any_text else "completed_empty")
    detail = "OCR processed the first 200 media files; import smaller batches for the remainder." if partial else (
        "Local OCR completed." if any_text else "No readable text was detected in the media."
    )
    return {"status": status, "texts": texts, "detail": detail}


def extract_text_from_media(paths: Iterable[Path]) -> dict[str, str]:
    """Compatibility helper for one post; returns combined text/status/detail."""
    result = extract_text_by_media(paths)
    return {
        "status": result["status"],
        "text": "\n".join(value for value in result["texts"].values() if value).strip(),
        "detail": result["detail"],
    }
