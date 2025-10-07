"""ClickHouse client for Chimera Muse bulletproof architecture."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import clickhouse_connect
from pathlib import Path
import json
import uuid

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """ClickHouse client for all Muse Protocol operations."""

    def __init__(self, host: str = "localhost", port: int = 8123,
                 username: str = "default", password: str = ""):
        """Initialize ClickHouse client.

        Args:
            host: ClickHouse server host
            port: ClickHouse server port
            username: ClickHouse username
            password: ClickHouse password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self._connect()

    def _connect(self):
        """Establish connection to ClickHouse."""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
            logger.info(f"Connected to ClickHouse at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def insert_bench_run(self, data: Dict[str, Any]) -> bool:
        """Insert benchmark run data.

        Args:
            data: Benchmark run data

        Returns:
            True if successful
        """
        try:
            query = """
            INSERT INTO bench_runs (
                ts, run_id, commit_sha, model, quant, dataset,
                latency_p50_ms, latency_p95_ms, latency_p99_ms,
                tokens_per_sec, cost_per_1k, memory_peak_mb, schema_version
            ) VALUES (
                %(ts)s, %(run_id)s, %(commit_sha)s, %(model)s, %(quant)s, %(dataset)s,
                %(latency_p50_ms)s, %(latency_p95_ms)s, %(latency_p99_ms)s,
                %(tokens_per_sec)s, %(cost_per_1k)s, %(memory_peak_mb)s, %(schema_version)s
            )
            """

            self.client.insert('bench_runs', [data])
            logger.info(f"Inserted bench run for commit {data['commit_sha']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert bench run: {e}")
            return False

    def insert_llm_event(self, data: Dict[str, Any]) -> bool:
        """Insert LLM event data.

        Args:
            data: LLM event data

        Returns:
            True if successful
        """
        try:
            query = """
            INSERT INTO llm_events (
                ts, run_id, source, model, operation,
                tokens_in, tokens_out, latency_ms, cost_usd, status, error_msg
            ) VALUES (
                %(ts)s, %(run_id)s, %(source)s, %(model)s, %(operation)s,
                %(tokens_in)s, %(tokens_out)s, %(latency_ms)s, %(cost_usd)s, %(status)s, %(error_msg)s
            )
            """

            self.client.insert('llm_events', [data])
            logger.info(f"Inserted LLM event for {data['source']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert LLM event: {e}")
            return False

    def insert_ui_event(self, data: Dict[str, Any]) -> bool:
        """Insert UI event data.

        Args:
            data: UI event data

        Returns:
            True if successful
        """
        try:
            self.client.insert('ui_events', [data])
            logger.info(f"Inserted UI event: {data['event_type']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert UI event: {e}")
            return False

    def insert_session_stats(self, data: Dict[str, Any]) -> bool:
        """Insert session statistics.

        Args:
            data: Session stats data

        Returns:
            True if successful
        """
        try:
            self.client.insert('session_stats', [data])
            logger.info(f"Inserted session stats for {data['hour']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert session stats: {e}")
            return False

    def insert_watcher_run(self, data: Dict[str, Any]) -> bool:
        """Insert watcher run data.

        Args:
            data: Watcher run data

        Returns:
            True if successful
        """
        try:
            self.client.insert('watcher_runs', [data])
            logger.info(f"Inserted watcher run: {data['status']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert watcher run: {e}")
            return False

    def insert_episode(self, data: Dict[str, Any]) -> bool:
        """Insert episode data.

        Args:
            data: Episode data

        Returns:
            True if successful
        """
        try:
            self.client.insert('episodes', [data])
            logger.info(f"Inserted episode {data['episode']}: {data['status']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert episode: {e}")
            return False

    def insert_deployment(self, data: Dict[str, Any]) -> bool:
        """Insert deployment data.

        Args:
            data: Deployment data

        Returns:
            True if successful
        """
        try:
            self.client.insert('deployments', [data])
            logger.info(f"Inserted deployment for episode {data['episode']}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert deployment: {e}")
            return False

    def get_next_episode_number(self, series: str = "chimera") -> int:
        """Get next episode number for a series.

        Args:
            series: Series name

        Returns:
            Next episode number
        """
        try:
            query = """
            SELECT COALESCE(MAX(episode), 0) + 1 as next_episode
            FROM episodes
            WHERE path LIKE %(pattern)s
            """

            pattern = f"%/{series}/ep-%"
            result = self.client.query(query, parameters={'pattern': pattern})

            if result.result_rows:
                return result.result_rows[0][0]
            return 1

        except Exception as e:
            logger.error(f"Failed to get next episode number: {e}")
            return 1

    def check_data_freshness(self, hearts_commit: str, packs_commit: str) -> Tuple[int, int, int]:
        """Check data freshness for commits.

        Args:
            hearts_commit: Banterhearts commit SHA
            packs_commit: Banterpacks commit SHA

        Returns:
            Tuple of (hearts_rows, packs_rows, lag_seconds)
        """
        try:
            # Check Banterhearts data
            hearts_query = """
            SELECT COUNT(*) as count,
                   COALESCE(MAX(ts), toDateTime64('1970-01-01', 3)) as last_ts
            FROM bench_runs
            WHERE commit_sha = %(hearts_commit)s
            """

            hearts_result = self.client.query(hearts_query, parameters={'hearts_commit': hearts_commit})
            hearts_rows = hearts_result.result_rows[0][0] if hearts_result.result_rows else 0
            hearts_last_ts = hearts_result.result_rows[0][1] if hearts_result.result_rows else datetime(1970, 1, 1)

            # Check Banterpacks data
            packs_query = """
            SELECT COUNT(*) as count,
                   COALESCE(MAX(ts), toDateTime64('1970-01-01', 3)) as last_ts
            FROM ui_events
            WHERE commit_sha = %(packs_commit)s
            """

            packs_result = self.client.query(packs_query, parameters={'packs_commit': packs_commit})
            packs_rows = packs_result.result_rows[0][0] if packs_result.result_rows else 0
            packs_last_ts = packs_result.result_rows[0][1] if packs_result.result_rows else datetime(1970, 1, 1)

            # Calculate lag
            now = datetime.now()
            hearts_lag = (now - hearts_last_ts).total_seconds() if hearts_last_ts > datetime(1970, 1, 1) else 999999
            packs_lag = (now - packs_last_ts).total_seconds() if packs_last_ts > datetime(1970, 1, 1) else 999999
            lag_seconds = max(hearts_lag, packs_lag)

            return hearts_rows, packs_rows, int(lag_seconds)

        except Exception as e:
            logger.error(f"Failed to check data freshness: {e}")
            return 0, 0, 999999

    def get_correlation_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get correlation data for episode generation.

        Args:
            days: Number of days to look back

        Returns:
            List of correlation data points
        """
        try:
            query = """
            WITH hearts AS (
                SELECT
                    toDate(ts) as day,
                    avg(latency_p95_ms) as avg_lat,
                    avg(cost_per_1k) as avg_cost,
                    count(*) as rows_count
                FROM bench_runs
                WHERE ts >= now() - INTERVAL %(days)s DAY
                GROUP BY day
            ),
            packs AS (
                SELECT
                    toDate(hour) as day,
                    avg(avg_latency_ms) as user_lat,
                    avg(error_rate) as err_rate,
                    avg(abandonment_rate) as abandon,
                    count(*) as rows_count
                FROM session_stats
                WHERE hour >= now() - INTERVAL %(days)s DAY
                GROUP BY day
            )
            SELECT
                h.day,
                h.avg_lat, h.avg_cost, h.rows_count as hearts_rows,
                p.user_lat, p.err_rate, p.abandon, p.rows_count as packs_rows,
                corr(h.avg_lat, p.user_lat) as correlation
            FROM hearts h
            JOIN packs p ON h.day = p.day
            ORDER BY h.day DESC
            """

            result = self.client.query(query, parameters={'days': days})

            correlation_data = []
            for row in result.result_rows:
                correlation_data.append({
                    'day': row[0],
                    'hearts_avg_lat': row[1],
                    'hearts_avg_cost': row[2],
                    'hearts_rows': row[3],
                    'packs_user_lat': row[4],
                    'packs_err_rate': row[5],
                    'packs_abandon': row[6],
                    'packs_rows': row[7],
                    'correlation': row[8]
                })

            return correlation_data

        except Exception as e:
            logger.error(f"Failed to get correlation data: {e}")
            return []

    def ready(self) -> bool:
        """Check if ClickHouse is ready.

        Returns:
            True if ready
        """
        try:
            result = self.client.query("SELECT 1")
            return result.result_rows[0][0] == 1
        except Exception as e:
            logger.error(f"ClickHouse not ready: {e}")
            return False

