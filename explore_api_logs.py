#!/usr/bin/env python3
"""
Explore and analyze logged image generation API calls
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from arxiv_paper_pulse import config

def load_logs(log_dir=None):
    """Load all log entries from JSONL files"""
    if log_dir is None:
        log_dir = Path(config.IMAGE_API_LOG_DIR)
    else:
        log_dir = Path(log_dir)

    if not log_dir.exists():
        print(f"❌ Log directory not found: {log_dir}")
        return []

    logs = []
    log_files = sorted(log_dir.glob("image_api_calls_*.jsonl"))

    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not parse line in {log_file}: {e}")

    return logs

def explore_log_entry(logs, index=None):
    """Explore a single log entry in detail"""
    if not logs:
        print("No logs found")
        return

    if index is None:
        # Show most recent
        entry = logs[-1]
        index = len(logs) - 1
    else:
        if index < 0 or index >= len(logs):
            print(f"Invalid index: {index} (available: 0-{len(logs)-1})")
            return
        entry = logs[index]

    print("=" * 70)
    print(f"📊 API CALL LOG ENTRY #{index}")
    print("=" * 70)
    print()

    # Basic info
    print("⏰ TIMESTAMP:")
    print(f"   {entry.get('timestamp', 'N/A')}")
    print()

    print("🤖 MODEL:")
    print(f"   {entry.get('model', 'N/A')}")
    print()

    print("📝 PROMPT:")
    prompt = entry.get('prompt', 'N/A')
    print(f"   {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"   Length: {entry.get('prompt_length', 'N/A')} characters")
    print()

    print("⏱️  PERFORMANCE:")
    print(f"   Response time: {entry.get('response_time_seconds', 'N/A')}s")
    print()

    print("🖼️  IMAGE:")
    print(f"   Size: {entry.get('image_size', 'N/A')}")
    print(f"   Mode: {entry.get('image_mode', 'N/A')}")
    if entry.get('image_data_size_bytes'):
        size_kb = entry['image_data_size_bytes'] / 1024
        print(f"   Data size: {entry['image_data_size_bytes']:,} bytes ({size_kb:.2f} KB)")
    print()

    if entry.get('saved_file'):
        print("💾 SAVED FILE:")
        file_info = entry['saved_file']
        print(f"   Path: {file_info.get('path', 'N/A')}")
        print(f"   Filename: {file_info.get('filename', 'N/A')}")
        if file_info.get('file_size_kb'):
            print(f"   File size: {file_info['file_size_kb']} KB")
        print()

    if entry.get('response_metadata'):
        print("📦 RESPONSE METADATA:")
        metadata = entry['response_metadata']

        if metadata.get('usage'):
            print("   Usage:")
            usage = metadata['usage']
            for key, value in usage.items():
                if value is not None:
                    print(f"     {key}: {value}")
            print()

        if metadata.get('candidate'):
            print("   Candidate:")
            candidate = metadata['candidate']
            for key, value in candidate.items():
                if value is not None:
                    print(f"     {key}: {value}")
            print()

    print("=" * 70)
    print()

def show_summary(logs):
    """Show summary statistics of all logs"""
    if not logs:
        print("No logs found")
        return

    print("=" * 70)
    print("📊 API CALLS SUMMARY")
    print("=" * 70)
    print(f"Total calls: {len(logs)}")
    print()

    # Time range
    timestamps = [log.get('timestamp') for log in logs if log.get('timestamp')]
    if timestamps:
        print(f"First call: {timestamps[0]}")
        print(f"Last call: {timestamps[-1]}")
        print()

    # Response times
    response_times = [log.get('response_time_seconds') for log in logs if log.get('response_time_seconds')]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        print("⏱️  RESPONSE TIMES:")
        print(f"   Average: {avg_time:.2f}s")
        print(f"   Min: {min_time:.2f}s")
        print(f"   Max: {max_time:.2f}s")
        print()

    # Image sizes
    sizes = [log.get('image_size') for log in logs if log.get('image_size')]
    size_counts = defaultdict(int)
    for size in sizes:
        size_counts[size] += 1
    if size_counts:
        print("🖼️  IMAGE SIZES:")
        for size, count in sorted(size_counts.items()):
            print(f"   {size}: {count} images")
        print()

    # Total file size
    total_size = sum(log['saved_file']['file_size_bytes'] for log in logs
                     if log.get('saved_file') and log['saved_file'].get('file_size_bytes'))
    if total_size:
        print(f"💾 TOTAL STORAGE: {total_size / 1024 / 1024:.2f} MB")
        print()

    # Prompt lengths
    prompt_lengths = [log.get('prompt_length') for log in logs if log.get('prompt_length')]
    if prompt_lengths:
        avg_length = sum(prompt_lengths) / len(prompt_lengths)
        print(f"📝 AVERAGE PROMPT LENGTH: {avg_length:.0f} characters")
        print()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'summary':
            logs = load_logs()
            show_summary(logs)
            return
        elif sys.argv[1] == 'list':
            logs = load_logs()
            if not logs:
                print("No logs found")
                return
            print(f"Found {len(logs)} log entries:")
            for i, log in enumerate(logs):
                timestamp = log.get('timestamp', 'N/A')[:19] if log.get('timestamp') else 'N/A'
                prompt = log.get('prompt', '')[:50]
                print(f"  [{i:3d}] {timestamp} - {prompt}...")
            return
        elif sys.argv[1].isdigit():
            index = int(sys.argv[1])
            logs = load_logs()
            explore_log_entry(logs, index)
            return

    # Default: show summary and latest entry
    logs = load_logs()

    if not logs:
        print("No logs found. Generate some images first!")
        return

    show_summary(logs)
    print()
    explore_log_entry(logs, index=None)

if __name__ == "__main__":
    main()

