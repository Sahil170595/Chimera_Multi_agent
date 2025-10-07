"""FastAPI orchestrator for Muse Protocol."""

import logging
import uuid
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from apps.config import load_config
from integrations.clickhouse import ClickHouseClient, EpisodeRecord, TranslationRecord
from integrations.datadog import DatadogClient
from integrations.deepl import DeepLClient
from integrations.repo import RepoWriter
from agents.banterpacks import BanterpacksAuthor
from agents.chimera import ChimeraAuthor


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

    try:
        config = load_config()

        # Initialize clients
        clickhouse_client = ClickHouseClient(config.clickhouse)
        datadog_client = DatadogClient(config.datadog)
        deepl_client = DeepLClient(config.deepl)
        repo_writer = RepoWriter(config.repo)

        logger.info("Orchestrator started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with dependency status."""
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

    # Overall status
    all_ready = all(dependencies.values())
    status = "healthy" if all_ready else "degraded"

    return HealthResponse(
        status=status,
        dependencies=dependencies
    )


@app.post("/run/episode")
async def run_episode(request: EpisodeRequest, background_tasks: BackgroundTasks):
    """Trigger episode generation."""
    if not all([clickhouse_client, datadog_client, repo_writer]):
        raise HTTPException(status_code=503, detail="Required services not available")

    try:
        # Validate series
        if request.series not in ['chimera', 'banterpacks']:
            raise HTTPException(status_code=400, detail="Invalid series. Must be 'chimera' or 'banterpacks'")

        # Get current commit SHA
        commit_sha = repo_writer.get_current_commit_sha()
        if not commit_sha:
            raise HTTPException(status_code=500, detail="Could not get current commit SHA")

        # Generate episode
        config = load_config()
        if request.series == 'chimera':
            author = ChimeraAuthor(config.agent)
        else:
            author = BanterpacksAuthor(config.agent)

        episode_data = author.generate_episode(commit_sha, request.sql)
        metadata = episode_data['metadata']
        content = episode_data['content']

        # Check idempotency
        if clickhouse_client.episode_exists(metadata['run_id']):
            return {
                "status": "skipped",
                "message": f"Episode with run_id {metadata['run_id']} already exists",
                "run_id": metadata['run_id']
            }

        # Schedule background tasks
        background_tasks.add_task(
            _process_episode,
            metadata,
            content,
            request.series
        )

        return {
            "status": "accepted",
            "run_id": metadata['run_id'],
            "series": request.series,
            "episode": metadata['episode']
        }

    except Exception as e:
        logger.error(f"Failed to run episode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/i18n/sync")
async def sync_translations(request: TranslationRequest, background_tasks: BackgroundTasks):
    """Trigger translation sync."""
    if not all([deepl_client, clickhouse_client, datadog_client]):
        raise HTTPException(status_code=503, detail="Required services not available")

    try:
        # Validate languages
        supported_langs = deepl_client.get_supported_languages()
        invalid_langs = [lang for lang in request.langs if lang.upper() not in supported_langs]

        if invalid_langs:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported languages: {invalid_langs}. Supported: {list(supported_langs.keys())}"
            )

        # Schedule background task
        background_tasks.add_task(
            _process_translations,
            request.langs,
            request.series
        )

        return {
            "status": "accepted",
            "languages": request.langs,
            "series": request.series or "all"
        }

    except Exception as e:
        logger.error(f"Failed to sync translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_episode(metadata: Dict[str, Any], content: str, series: str):
    """Background task to process episode."""
    try:
        # Write episode file
        from pathlib import Path

        series_dir = Path(f"posts/{series}")
        series_dir.mkdir(parents=True, exist_ok=True)

        episode_file = series_dir / f"ep-{metadata['episode']:03d}.md"

        if not repo_writer.write_file(episode_file, content, metadata):
            logger.error(f"Failed to write episode file {episode_file}")
            return

        # Commit to git
        commit_message = f"Add {series} episode {metadata['episode']}: {metadata['title']}"
        repo_writer.add_and_commit(episode_file, commit_message)

        # Log to ClickHouse
        episode_record = EpisodeRecord(
            run_id=metadata['run_id'],
            series=metadata['series'],
            episode=metadata['episode'],
            title=metadata['title'],
            date=metadata['date'],
            models=metadata['models'],
            commit_sha=metadata['commit_sha'],
            latency_ms_p95=metadata['latency_ms_p95'],
            tokens_in=metadata['tokens_in'],
            tokens_out=metadata['tokens_out'],
            cost_usd=metadata['cost_usd']
        )

        clickhouse_client.insert_episode(episode_record)

        # Send metrics to Datadog
        datadog_client.send_episode_metrics(metadata)

        logger.info(f"Processed episode {metadata['episode']} for series {series}")

    except Exception as e:
        logger.error(f"Failed to process episode: {e}")


async def _process_translations(langs: List[str], series: Optional[str]):
    """Background task to process translations."""
    try:
        from pathlib import Path

        # Find source episodes
        posts_dir = Path("posts")
        source_files = []

        if series:
            series_dir = posts_dir / series
            if series_dir.exists():
                source_files.extend(series_dir.glob("*.md"))
        else:
            for series_dir in posts_dir.iterdir():
                if series_dir.is_dir():
                    source_files.extend(series_dir.glob("*.md"))

        # Translate each file
        for src_file in source_files:
            for lang in langs:
                lang_upper = lang.upper()

                # Determine output path
                src_series = src_file.parent.name
                out_dir = Path(f"posts_i18n/{lang.lower()}/{src_series}")
                out_file = out_dir / src_file.name

                # Skip if translation already exists
                if out_file.exists():
                    continue

                # Translate
                if deepl_client.translate_markdown(src_file, lang_upper, out_file):
                    # Log translation to ClickHouse
                    translation_record = TranslationRecord(
                        run_id=str(uuid.uuid4()),
                        source_series=src_series,
                        source_episode=int(src_file.stem.split('-')[1]),
                        target_language=lang_upper,
                        translation_of=str(src_file)
                    )

                    clickhouse_client.insert_translation(translation_record)

                    # Send metrics
                    datadog_client.send_translation_metrics({
                        "source_series": src_series,
                        "target_language": lang_upper
                    })

                    logger.info(f"Translated {src_file} to {lang_upper}")

        logger.info(f"Completed translation sync for languages: {langs}")

    except Exception as e:
        logger.error(f"Failed to process translations: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
