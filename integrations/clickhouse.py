"""ClickHouse integration for Muse Protocol."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from clickhouse_driver import Client
from apps.config import ClickHouseConfig


logger = logging.getLogger(__name__)


@dataclass
class EpisodeRecord:
    """Episode record for ClickHouse."""
    run_id: str
    series: str
    episode: int
    title: str
    date: str
    models: List[str]
    commit_sha: str
    latency_ms_p95: int
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass
class TranslationRecord:
    """Translation record for ClickHouse."""
    run_id: str
    source_series: str
    source_episode: int
    target_language: str
    translation_of: str


class ClickHouseClient:
    """ClickHouse client wrapper."""

    def __init__(self, config: ClickHouseConfig):
        """Initialize ClickHouse client.

        Args:
            config: ClickHouse configuration
        """
        self.config = config
        self.client: Optional[Client] = None
        self._connected = False

    def connect(self) -> None:
        """Establish connection to ClickHouse."""
        try:
            self.client = Client(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database
            )
            self._connected = True
            logger.info("Connected to ClickHouse")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def ready(self) -> bool:
        """Check if ClickHouse is ready.

        Returns:
            True if ready, False otherwise
        """
        try:
            if not self._connected:
                self.connect()

            # Simple health check
            result = self.client.execute("SELECT 1")
            return result[0][0] == 1
        except Exception as e:
            logger.warning(f"ClickHouse health check failed: {e}")
            return False

    def insert_episode(self, episode: EpisodeRecord) -> None:
        """Insert episode record.

        Args:
            episode: Episode record to insert
        """
        if not self._connected:
            self.connect()

        query = """
        INSERT INTO episodes (
            run_id, series, episode, title, date, models,
            commit_sha, latency_ms_p95, tokens_in, tokens_out, cost_usd
        ) VALUES
        """

        values = [
            episode.run_id,
            episode.series,
            episode.episode,
            episode.title,
            episode.date,
            episode.models,
            episode.commit_sha,
            episode.latency_ms_p95,
            episode.tokens_in,
            episode.tokens_out,
            episode.cost_usd
        ]

        try:
            self.client.execute(query, [values])
            logger.info(f"Inserted episode {episode.episode} for series {episode.series}")
        except Exception as e:
            logger.error(f"Failed to insert episode: {e}")
            raise

    def insert_translation(self, translation: TranslationRecord) -> None:
        """Insert translation record.

        Args:
            translation: Translation record to insert
        """
        if not self._connected:
            self.connect()

        query = """
        INSERT INTO translations (
            run_id, source_series, source_episode, target_language, translation_of
        ) VALUES
        """

        values = [
            translation.run_id,
            translation.source_series,
            translation.source_episode,
            translation.target_language,
            translation.translation_of
        ]

        try:
            self.client.execute(query, [values])
            logger.info(f"Inserted translation for {translation.source_series} ep{translation.source_episode} -> {translation.target_language}")
        except Exception as e:
            logger.error(f"Failed to insert translation: {e}")
            raise

    def next_episode(self, series: str) -> int:
        """Get next episode number for series.

        Args:
            series: Series name

        Returns:
            Next episode number
        """
        if not self._connected:
            self.connect()

        query = "SELECT MAX(episode) FROM episodes WHERE series = ?"

        try:
            result = self.client.execute(query, [series])
            max_episode = result[0][0] if result[0][0] is not None else 0
            return max_episode + 1
        except Exception as e:
            logger.error(f"Failed to get next episode number: {e}")
            # Fallback to 1 if query fails
            return 1

    def episode_exists(self, run_id: str) -> bool:
        """Check if episode with run_id already exists.

        Args:
            run_id: Run identifier

        Returns:
            True if episode exists, False otherwise
        """
        if not self._connected:
            self.connect()

        query = "SELECT COUNT(*) FROM episodes WHERE run_id = ?"

        try:
            result = self.client.execute(query, [run_id])
            return result[0][0] > 0
        except Exception as e:
            logger.error(f"Failed to check episode existence: {e}")
            return False


class MockClickHouseClient:
    """Mock ClickHouse client for testing."""

    def __init__(self, config: ClickHouseConfig):
        """Initialize mock client."""
        self.config = config
        self.episodes: List[EpisodeRecord] = []
        self.translations: List[TranslationRecord] = []
        self._connected = True

    def ready(self) -> bool:
        """Mock ready check."""
        return True

    def insert_episode(self, episode: EpisodeRecord) -> None:
        """Mock episode insertion."""
        self.episodes.append(episode)
        logger.info(f"Mock: Inserted episode {episode.episode} for series {episode.series}")

    def insert_translation(self, translation: TranslationRecord) -> None:
        """Mock translation insertion."""
        self.translations.append(translation)
        logger.info(f"Mock: Inserted translation for {translation.source_series} ep{translation.source_episode} -> {translation.target_language}")

    def next_episode(self, series: str) -> int:
        """Mock next episode number."""
        max_episode = max((ep.episode for ep in self.episodes if ep.series == series), default=0)
        return max_episode + 1

    def episode_exists(self, run_id: str) -> bool:
        """Mock episode existence check."""
        return any(ep.run_id == run_id for ep in self.episodes)

