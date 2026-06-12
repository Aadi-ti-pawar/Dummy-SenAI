"""
Replay email-data-advanced.json into the ingestion API.

Examples:
    python scripts/simulate_stream.py --speed 1
    python scripts/simulate_stream.py --speed 10 --limit 20
    python scripts/simulate_stream.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_URL = "http://localhost:8000/api/ingest"
DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "email-data-advanced.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay emails into the ingestion API.")
    parser.add_argument("--file", default=str(DEFAULT_DATASET), help="Path to email-data-advanced.json.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Ingestion endpoint URL.")
    parser.add_argument("--speed", type=float, default=1.0, help="Emails per second. Use 0 for no sleep.")
    parser.add_argument("--limit", type=int, default=None, help="Only replay the first N emails.")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle emails before replay.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Print emails without sending requests.")
    return parser.parse_args()


def load_dataset(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array.")
    return data


def post_email(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            return response.status, json.loads(response_body)
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError:
            parsed = {"error": response_body}
        return exc.code, parsed


def main() -> None:
    args = parse_args()
    emails = load_dataset(args.file)

    if args.limit is not None:
        emails = emails[: args.limit]
    if args.shuffle:
        random.shuffle(emails)

    interval = 0 if args.speed <= 0 else 1 / args.speed
    totals = {"sent": 0, "duplicates": 0, "failed": 0}
    start = time.perf_counter()

    print(f"Loaded {len(emails)} emails from {args.file}")
    print(f"Target: {args.url}")
    print(f"Speed: {'no sleep' if interval == 0 else f'{args.speed:g} email(s)/sec'}")

    for index, email in enumerate(emails, start=1):
        label = f"[{index:03d}/{len(emails):03d}] {email.get('message_id')} {email.get('thread_id')}"
        if args.dry_run:
            print(f"{label} dry-run")
        else:
            status, response = post_email(args.url, email, args.timeout)
            if 200 <= status < 300:
                totals["sent"] += 1
                if response.get("duplicate"):
                    totals["duplicates"] += 1
                print(
                    f"{label} -> {status} "
                    f"job={response.get('job_id')} priority={response.get('priority')} "
                    f"duplicate={response.get('duplicate')}"
                )
            else:
                totals["failed"] += 1
                print(f"{label} -> {status} error={response}")

        if interval and index < len(emails):
            time.sleep(interval)

    elapsed = time.perf_counter() - start
    print(
        "Done: "
        f"sent={totals['sent']} duplicates={totals['duplicates']} "
        f"failed={totals['failed']} elapsed={elapsed:.2f}s"
    )


if __name__ == "__main__":
    main()
