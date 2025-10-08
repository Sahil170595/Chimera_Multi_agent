"""ClickHouse client for Chimera Muse bulletproof architecture."""

import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple
from clickhouse_driver import Client
from integrations.retry_utils import clickhouse_retry

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """ClickHouse client for all Muse Protocol operations."""

    def __init__(self, host: str = "localhost", port: int = 8123,
                 username: str = "default", password: str = "",
                 database: str = "default"):
        """Initialize ClickHouse client.

        Args:
            host: ClickHouse server host
            port: ClickHouse server port
            username: ClickHouse username
            password: ClickHouse password
            database: ClickHouse database name
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.client = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to ClickHouse."""
        secure = str(os.getenv('CLICKHOUSE_SECURE', 'true')).lower() == 'true'
        try:
            self.client = Client(
                host=self.host,
                port=9440 if secure else 9000,  # Native protocol ports
                user=self.username,
                password=self.password,
                database=self.database,
                secure=secure,
                verify=False,
            )
            logger.info(
                f"Connected to ClickHouse at {self.host}:{'9440' if secure else '9000'} "
                f"db={self.database} secure={secure}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def _tbl(self, name: str) -> str:
        return f"{self.database}.{name}"

    @clickhouse_retry
    def insert_bench_run(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('bench_runs')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert bench run: {e}")
            return False

    @clickhouse_retry
    def insert_llm_event(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('llm_events')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert LLM event: {e}")
            return False

    @clickhouse_retry
    def insert_ui_event(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('ui_events')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert UI event: {e}")
            return False

    @clickhouse_retry
    def insert_session_stats(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('session_stats')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert session stats: {e}")
            return False

    @clickhouse_retry
    def insert_watcher_run(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('watcher_runs')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert watcher run: {e}")
            return False

    @clickhouse_retry
    def insert_episode(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('episodes')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert episode: {e}")
            return False

    @clickhouse_retry
    def insert_deployment(self, data: Dict[str, Any]) -> bool:
        try:
            self.client.execute(
                f"INSERT INTO {self._tbl('deployments')} VALUES",
                [tuple(data.values())]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert deployment: {e}")
            return False

    def get_next_episode_number(self, series: str = "chimera") -> int:
        try:
            query = f"""
            SELECT COALESCE(MAX(episode), 0) + 1 as next_episode
            FROM {self._tbl('episodes')}
            WHERE path LIKE %(pattern)s
            """
            result = self.client.execute(
                query,
                {'pattern': f"%/{series}/ep-%"}
            )
            return int(result[0][0]) if result else 1
        except Exception as e:
            logger.error(f"Failed to get next episode number: {e}")
            return 1

    def check_data_freshness(self, hearts_commit: str, packs_commit: str) -> Tuple[int, int, int]:
        try:
            hearts_query = f"""
            SELECT COUNT(*) as count,
                   COALESCE(MAX(ts), toDateTime64('1970-01-01', 3)) as last_ts
            FROM {self._tbl('bench_runs')}
            WHERE commit_sha = %(hearts_commit)s
            """
            hres = self.client.execute(
                hearts_query,
                {'hearts_commit': hearts_commit}
            )
            hearts_rows = hres[0][0] if hres else 0
            hearts_last_ts_raw = hres[0][1] if hres else None

            packs_query = f"""
            SELECT COUNT(*) as count,
                   COALESCE(MAX(ts), toDateTime64('1970-01-01', 3)) as last_ts
            FROM {self._tbl('ui_events')}
            WHERE commit_sha = %(packs_commit)s
            """
            pres = self.client.execute(
                packs_query,
                {'packs_commit': packs_commit}
            )
            packs_rows = pres[0][0] if pres else 0
            packs_last_ts_raw = pres[0][1] if pres else None

            # Calculate lag (handle timezone-aware datetimes from ClickHouse)
            epoch = datetime(1970, 1, 1)
            now = datetime.now()
            
            # Hearts lag
            if hearts_last_ts_raw:
                # Remove timezone if present
                if hasattr(hearts_last_ts_raw, 'tzinfo') and hearts_last_ts_raw.tzinfo:
                    hearts_last_ts = hearts_last_ts_raw.replace(tzinfo=None)
                else:
                    hearts_last_ts = hearts_last_ts_raw
                    
                if hearts_last_ts > epoch:
                    hearts_lag = (now - hearts_last_ts).total_seconds()
                else:
                    hearts_lag = 999999
            else:
                hearts_lag = 999999
                
            # Packs lag
            if packs_last_ts_raw:
                # Remove timezone if present
                if hasattr(packs_last_ts_raw, 'tzinfo') and packs_last_ts_raw.tzinfo:
                    packs_last_ts = packs_last_ts_raw.replace(tzinfo=None)
                else:
                    packs_last_ts = packs_last_ts_raw
                    
                if packs_last_ts > epoch:
                    packs_lag = (now - packs_last_ts).total_seconds()
                else:
                    packs_lag = 999999
            else:
                packs_lag = 999999
                
            return hearts_rows, packs_rows, int(max(hearts_lag, packs_lag))
        except Exception as e:
            logger.error(f"Failed to check data freshness: {e}")
            return 0, 0, 999999

    def get_correlation_data(self, days: int = 7) -> List[Dict[str, Any]]:
        try:
            query = f"""
            WITH hearts AS (
                SELECT toDate(ts) as day,
                       avg(latency_p95_ms) as avg_lat,
                       avg(cost_per_1k) as avg_cost,
                       count(*) as rows_count
                FROM {self._tbl('bench_runs')}
                WHERE ts >= now() - INTERVAL %(days)s DAY
                GROUP BY day
            ),
            packs AS (
                SELECT toDate(hour) as day,
                       avg(avg_latency_ms) as user_lat,
                       avg(error_rate) as err_rate,
                       avg(abandonment_rate) as abandon,
                       count(*) as rows_count
                FROM {self._tbl('session_stats')}
                WHERE hour >= now() - INTERVAL %(days)s DAY
                GROUP BY day
            )
            SELECT h.day,
                   h.avg_lat, h.avg_cost, h.rows_count as hearts_rows,
                   p.user_lat, p.err_rate, p.abandon, p.rows_count as packs_rows,
                   corr(h.avg_lat, p.user_lat) as correlation
            FROM hearts h
            JOIN packs p ON h.day = p.day
            ORDER BY h.day DESC
            """
            res = self.client.execute(query, {'days': days})
            out: List[Dict[str, Any]] = []
            for r in res:
                out.append({
                    'day': r[0],
                    'hearts_avg_lat': r[1],
                    'hearts_avg_cost': r[2],
                    'hearts_rows': r[3],
                    'packs_user_lat': r[4],
                    'packs_err_rate': r[5],
                    'packs_abandon': r[6],
                    'packs_rows': r[7],
                    'correlation': r[8],
                })
            return out
        except Exception as e:
            logger.error(f"Failed to get correlation data: {e}")
            return []

    def ready(self) -> bool:
        try:
            res = self.client.execute("SELECT 1")
            return res[0][0] == 1
        except Exception as e:
            logger.error(f"ClickHouse not ready: {e}")
            return False
