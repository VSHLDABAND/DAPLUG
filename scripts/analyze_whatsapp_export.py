#!/usr/bin/env python3
"""Read-only DA'PLUG WhatsApp export analyzer.

Usage:
  python scripts/analyze_whatsapp_export.py "/path/to/WhatsApp Chat.txt"

No database access or writes are performed. Message-level classification is
reported separately from post-splitting entry-level classification.
"""
from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.broker_feed import (  # noqa: E402
    classify_broker_message,
    parse_broker_post,
    split_property_entries,
    split_whatsapp_export,
)


def parse_date(value: str):
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[ *_~`]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python scripts/analyze_whatsapp_export.py "/path/to/chat.txt"')
        return 2

    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.is_file():
        print(f"File not found: {source}")
        return 2
    if source.suffix.lower() != ".txt":
        print("Please provide the extracted WhatsApp .txt file (not the media ZIP).")
        return 2

    text = source.read_text(encoding="utf-8-sig", errors="replace")
    messages = split_whatsapp_export(text)
    message_counts: Counter[str] = Counter()
    entry_counts: Counter[str] = Counter()
    unique_supply_hashes: set[str] = set()
    date_buckets: Counter[str] = Counter()
    dates = [d for d in (parse_date(m.get("date", "")) for m in messages) if d]
    media_pattern = re.compile(r"\.(?:jpe?g|png|webp|gif|heic|tiff?|pdf|mp4|mov)\s*\(file attached\)", re.I)

    for message in messages:
        raw = (message.get("text") or "").strip()
        whole_intent = classify_broker_message(raw)
        message_counts[whole_intent] += 1
        if media_pattern.search(raw):
            message_counts["contains_media_placeholder"] += 1

        entries = split_property_entries(raw)
        if len(entries) > 1:
            entry_counts["messages_split"] += 1
            entry_counts["segments_created"] += len(entries)

        message_date = parse_date(message.get("date", ""))
        if message_date:
            age_days = (datetime.now().date() - message_date).days
            if age_days < 0:
                date_buckets["future_or_timezone_issue"] += 1
            elif age_days <= 7:
                date_buckets["0-7 days"] += 1
            elif age_days <= 30:
                date_buckets["8-30 days"] += 1
            elif age_days <= 60:
                date_buckets["31-60 days"] += 1
            elif age_days <= 90:
                date_buckets["61-90 days"] += 1
            else:
                date_buckets["over 90 days"] += 1

        # Crucial change: classify each split segment, not only the whole source
        # message. This can rescue valid property offers from mixed bulk posts.
        for entry in entries:
            entry = entry.strip()
            if len(entry) < 3:
                entry_counts["too_short"] += 1
                continue
            intent = classify_broker_message(entry)
            if intent == "demand":
                entry_counts["demand_segments_skipped"] += 1
                continue
            if intent == "mixed":
                entry_counts["mixed_segments_review_only"] += 1
                continue
            if intent == "unknown":
                entry_counts["unknown_segments_review_only"] += 1
                continue

            parsed = parse_broker_post(entry)
            entry_counts["supply_candidate_entries"] += 1
            unique_supply_hashes.add(hashlib.sha256(normalize(entry).encode("utf-8")).hexdigest())
            if parsed.get("transaction_type"):
                entry_counts["with_transaction"] += 1
            if parsed.get("locality"):
                entry_counts["with_locality"] += 1
            if parsed.get("price") is not None:
                entry_counts["with_price"] += 1
            if parsed.get("transaction_type") and parsed.get("locality") and parsed.get("price") is not None:
                entry_counts["with_transaction_location_price"] += 1
            if parsed.get("confidence", 0) < 35:
                entry_counts["low_confidence_under_35"] += 1
            elif parsed.get("confidence", 0) < 50:
                entry_counts["confidence_35_to_49"] += 1

    print("DA'PLUG — WhatsApp export dry run (read only)")
    print("=" * 54)
    print(f"File: {source.name}")
    print(f"Size: {source.stat().st_size / (1024 * 1024):.2f} MiB")
    print(f"Messages parsed: {len(messages):,}")
    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")

    print("\nMESSAGE-LEVEL CLASSIFICATION (before splitting)")
    for key, label in (("supply", "Supply messages"), ("demand", "Demand messages"),
                       ("mixed", "Mixed messages"), ("unknown", "Unknown messages")):
        print(f"{label}: {message_counts.get(key, 0):,}")
    print(f"Messages containing media placeholders: {message_counts.get('contains_media_placeholder', 0):,}")

    print("\nENTRY-LEVEL RESULTS (after safe splitting)")
    labels = (
        ("messages_split", "Messages safely split"),
        ("segments_created", "Segments created"),
        ("supply_candidate_entries", "Supply candidate entries"),
        ("demand_segments_skipped", "Demand segments skipped"),
        ("mixed_segments_review_only", "Mixed segments held for review"),
        ("unknown_segments_review_only", "Unknown segments held for review"),
        ("with_transaction", "Supply entries with transaction type"),
        ("with_locality", "Supply entries with recognised locality"),
        ("with_price", "Supply entries with extracted price"),
        ("with_transaction_location_price", "Supply entries with transaction + locality + price"),
        ("low_confidence_under_35", "Very low-confidence supply entries (<35)"),
        ("confidence_35_to_49", "Low-confidence supply entries (35–49)"),
    )
    for key, label in labels:
        print(f"{label}: {entry_counts.get(key, 0):,}")
    print(f"Approx. exact-text unique supply segments: {len(unique_supply_hashes):,}")

    if date_buckets:
        print("\nMESSAGE AGE (based on export timestamps)")
        for label in ("0-7 days", "8-30 days", "31-60 days", "61-90 days", "over 90 days", "future_or_timezone_issue"):
            if date_buckets.get(label):
                print(f"{label}: {date_buckets[label]:,}")

    print("\nImportant: candidates are not verified available properties.")
    print("Old/reposted listings must be availability-checked before contacting clients.")
    print("No records were imported and the DA'PLUG database was not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
