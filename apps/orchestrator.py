"""FastAPI orchestrator for Muse Protocol."""

import logging
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from apps.config import load_config
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient
from integrations.deepl import DeepLClient
from integrations.repo import RepoWriter
from agents.banterhearts_ingestor import BanterheartsIngestor
from agents.banterpacks_collector import BanterpacksCollector
from agents.council import CouncilAgent
from agents.publisher import PublisherAgent
from agents.i18n_translator import I18nTranslator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Muse Protocol Orchestrator",
    description="Multi-agent content authoring with i18n support",
    version="0.1.0"
)

# Global clients (will be initialized on startup)
clickhouse_client: Optional[ClickHouseClient] = None
datadog_client: Optional[DatadogClient] = None
deepl_client: Optional[DeepLClient] = None
repo_writer: Optional[RepoWriter] = None

# Global agents
watcher_agent = None  # optional future
ingestor_agent: Optional[BanterheartsIngestor] = None
collector_agent: Optional[BanterpacksCollector] = None
council_agent: Optional[CouncilAgent] = None
publisher_agent: Optional[PublisherAgent] = None
translator_agent: Optional[I18nTranslator] = None


class EpisodeRequest(BaseModel):
    """Request model for episode generation."""
    series: str
    sql: Optional[str] = None


class TranslationRequest(BaseModel):
    """Request model for translation sync."""
    langs: List[str]
    series: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    dependencies: Dict[str, bool]


@app.on_event("startup")
async def startup_event():
    """Initialize clients on startup."""
    global clickhouse_client, datadog_client, deepl_client, repo_writer
    global ingestor_agent, collector_agent, council_agent, publisher_agent, translator_agent

    try:
        config = load_config()

        # Initialize clients
        clickhouse_client = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password,
        )
        datadog_client = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key,
        )
        deepl_client = DeepLClient()
        repo_writer = RepoWriter(config.repo)

        # Initialize agents
        ingestor_agent = BanterheartsIngestor(clickhouse_client, datadog_client)
        collector_agent = BanterpacksCollector(clickhouse_client, datadog_client)
        council_agent = CouncilAgent(clickhouse_client, datadog_client)
        publisher_agent = PublisherAgent(clickhouse_client, datadog_client)
        translator_agent = I18nTranslator(clickhouse_client, datadog_client)

        logger.info("Orchestrator started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness probe - lightweight health check."""
    return HealthResponse(status="healthy", dependencies={})


@app.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness probe - validates all dependencies."""
    dependencies = {}

    # Check ClickHouse
    if clickhouse_client:
        dependencies["clickhouse"] = clickhouse_client.ready()
    else:
        dependencies["clickhouse"] = False

    # Check Datadog
    if datadog_client:
        dependencies["datadog"] = datadog_client.ready()
    else:
        dependencies["datadog"] = False

    # Check DeepL
    if deepl_client:
        dependencies["deepl"] = deepl_client.ready()
    else:
        dependencies["deepl"] = False

    # Check Repository
    if repo_writer:
        dependencies["repository"] = repo_writer.ready()
    else:
        dependencies["repository"] = False

    # Check watcher status
    import tempfile
    from pathlib import Path
    watcher_ok_file = Path(tempfile.gettempdir()) / "watcher_ok"
    dependencies["watcher"] = watcher_ok_file.exists()

    # Overall status
    all_ready = all(dependencies.values())
    status = "healthy" if all_ready else "degraded"

    return HealthResponse(
        status=status,
        dependencies=dependencies
    )


@app.post("/run/council")
async def run_council(background_tasks: BackgroundTasks):
    """Trigger Council Agent episode generation."""
    if not council_agent:
        raise HTTPException(status_code=503, detail="Council Agent not available")

    result = council_agent.generate_episode()
    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result)
    return result


@app.post("/run/ingest")
async def run_ingest(hours: int = 24):
    """Trigger Banterhearts Ingestor for benchmark data."""
    if not ingestor_agent:
        raise HTTPException(status_code=503, detail="Ingestor not available")
    return ingestor_agent.ingest_benchmarks(hours)


@app.post("/run/collect")
async def run_collect(hours: int = 24):
    """Trigger Banterpacks Collector for commit watching."""
    if not collector_agent:
        raise HTTPException(status_code=503, detail="Collector not available")
    return collector_agent.run_collection(hours)


@app.post("/run/publish")
async def run_publish(episode: Optional[int] = None):
    """Trigger Publisher Agent to publish an episode."""
    if not publisher_agent:
        raise HTTPException(status_code=503, detail="Publisher not available")
    return publisher_agent.publish_episode(episode)


@app.post("/i18n/sync")
async def sync_translations(request: TranslationRequest, background_tasks: BackgroundTasks):
    """Trigger translation sync."""
    if not translator_agent:
        raise HTTPException(status_code=503, detail="Translator not available")

    # Validate languages against DeepL known set if available
    try:
        supported_langs = deepl_client.get_supported_languages() if deepl_client else {}
        invalid_langs = [lang for lang in request.langs if supported_langs and lang.upper() not in supported_langs]
        if invalid_langs:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported languages: {invalid_langs}. Supported: {list(supported_langs.keys())}"
            )
    except Exception:
        # If DeepL not fully configured, proceed; user said APIs coming soon
        pass

    def _run_translation():
        translator_agent.run_translation(request.langs)

    background_tasks.add_task(_run_translation)
    return {"status": "accepted", "languages": request.langs, "series": request.series or "all"}


async def _process_episode_placeholder():
    """Deprecated path kept for compatibility (no-op)."""
    return


async def _process_translations_placeholder():
    """Deprecated path kept for compatibility (no-op)."""
    return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
