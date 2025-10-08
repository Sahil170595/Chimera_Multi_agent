#!/usr/bin/env python3
"""Verify ClickHouse data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.config import load_config
from integrations.clickhouse_client import ClickHouseClient

config = load_config()
ch = ClickHouseClient(
    host=config.clickhouse.host,
    port=config.clickhouse.port,
    username=config.clickhouse.username,
    password=config.clickhouse.password,
    database=config.clickhouse.database
)

# Count rows
bench_count = ch.client.execute('SELECT count() FROM bench_runs')[0][0]
ui_count = ch.client.execute('SELECT count() FROM ui_events')[0][0]

print(f"bench_runs: {bench_count} rows")
print(f"ui_events: {ui_count} rows")

# Sample data
if bench_count > 0:
    sample = ch.client.execute('SELECT ts, model, quant, dataset FROM bench_runs LIMIT 5')
    print("\nSample bench_runs:")
    for row in sample:
        print(f"  {row}")

if ui_count > 0:
    sample = ch.client.execute('SELECT ts, event_type, commit_sha FROM ui_events LIMIT 5')
    print("\nSample ui_events:")
    for row in sample:
        print(f"  {row}")

