"""CLI interface for Chimera Muse operations."""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import click
from apps.config import load_config
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient
from agents.watcher import WatcherAgent
from agents.banterhearts_ingestor import BanterheartsIngestor
from agents.banterpacks_collector import BanterpacksCollector
from agents.council import CouncilAgent
from agents.publisher import PublisherAgent
from agents.i18n_translator import I18nTranslator

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose: bool):
    """Chimera Muse CLI - Orchestrate AI agents for episode generation."""
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


@cli.command()
@click.option('--hours', '-h', default=24, help='Hours to look back for data')
def watcher(hours: int):
    """Run Watcher Agent to check data freshness."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        watcher = WatcherAgent(clickhouse, datadog)
        result = watcher.check_data_freshness(hours)

        click.echo(json.dumps(result, indent=2, default=str))

        if result.get("status") == "ok":
            click.echo("✅ Watcher status: OK", err=True)
            sys.exit(0)
        else:
            click.echo("❌ Watcher status: FAILED", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Watcher failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--hours', '-h', default=24, help='Hours to look back for commits')
def ingest(hours: int):
    """Run Banterhearts Ingestor to process benchmark data."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        ingestor = BanterheartsIngestor(clickhouse, datadog)
        result = ingestor.ingest_benchmarks(hours)

        click.echo(json.dumps(result, indent=2, default=str))

        if result.get("status") == "completed":
            click.echo("✅ Ingestor completed successfully", err=True)
            sys.exit(0)
        else:
            click.echo("❌ Ingestor failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Ingestor failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--hours', '-h', default=24, help='Hours to look back for commits')
def collect(hours: int):
    """Run Banterpacks Collector to process commit data."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        collector = BanterpacksCollector(clickhouse, datadog)
        result = collector.run_collection(hours)

        click.echo(json.dumps(result, indent=2, default=str))

        if result.get("status") == "completed":
            click.echo("✅ Collector completed successfully", err=True)
            sys.exit(0)
        else:
            click.echo("❌ Collector failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Collector failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def council():
    """Run Council Agent to generate new episode."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        council = CouncilAgent(clickhouse, datadog)
        result = council.generate_episode()

        click.echo(json.dumps(result, indent=2, default=str))

        if result.get("status") == "success":
            click.echo("✅ Council generated episode successfully", err=True)
            sys.exit(0)
        else:
            click.echo("❌ Council failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Council failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--episode', '-e', type=int, help='Specific episode number to publish')
def publish(episode: Optional[int]):
    """Run Publisher Agent to publish episode."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        publisher = PublisherAgent(clickhouse, datadog)
        result = publisher.publish_episode(episode)

        click.echo(json.dumps(result, indent=2, default=str))

        if result.get("status") == "success":
            click.echo("✅ Publisher completed successfully", err=True)
            sys.exit(0)
        else:
            click.echo("❌ Publisher failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Publisher failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--langs', '-l', help='Comma-separated list of languages (e.g., de,zh,hi)')
def translate(langs: Optional[str]):
    """Run i18n Translator to translate episodes."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        translator = I18nTranslator(clickhouse, datadog)

        languages = None
        if langs:
            languages = [lang.strip() for lang in langs.split(',')]

        result = translator.run_translation(languages)

        click.echo(json.dumps(result, indent=2, default=str))

        if result.get("status") == "completed":
            click.echo("✅ Translator completed successfully", err=True)
            sys.exit(0)
        else:
            click.echo("❌ Translator failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Translator failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def pipeline():
    """Run complete pipeline: Watcher -> Ingest -> Collect -> Council -> Publish -> Translate."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        datadog = DatadogClient(
            api_key=config.datadog.api_key,
            app_key=config.datadog.app_key
        )

        # Initialize all agents
        watcher = WatcherAgent(clickhouse, datadog)
        ingestor = BanterheartsIngestor(clickhouse, datadog)
        collector = BanterpacksCollector(clickhouse, datadog)
        council = CouncilAgent(clickhouse, datadog)
        publisher = PublisherAgent(clickhouse, datadog)
        translator = I18nTranslator(clickhouse, datadog)

        pipeline_results = {}

        # Step 1: Watcher
        click.echo("🔍 Running Watcher...", err=True)
        watcher_result = watcher.check_data_freshness(24)
        pipeline_results["watcher"] = watcher_result

        if watcher_result.get("status") != "ok":
            click.echo("❌ Pipeline stopped: Watcher failed", err=True)
            click.echo(json.dumps(pipeline_results, indent=2, default=str))
            sys.exit(1)

        # Step 2: Ingest
        click.echo("📊 Running Ingestor...", err=True)
        ingest_result = ingestor.ingest_benchmarks(24)
        pipeline_results["ingest"] = ingest_result

        # Step 3: Collect
        click.echo("📝 Running Collector...", err=True)
        collect_result = collector.run_collection(24)
        pipeline_results["collect"] = collect_result

        # Step 4: Council
        click.echo("🧠 Running Council...", err=True)
        council_result = council.generate_episode()
        pipeline_results["council"] = council_result

        if council_result.get("status") != "success":
            click.echo("❌ Pipeline stopped: Council failed", err=True)
            click.echo(json.dumps(pipeline_results, indent=2, default=str))
            sys.exit(1)

        # Step 5: Publish
        click.echo("🚀 Running Publisher...", err=True)
        publish_result = publisher.publish_episode()
        pipeline_results["publish"] = publish_result

        if publish_result.get("status") != "success":
            click.echo("❌ Pipeline stopped: Publisher failed", err=True)
            click.echo(json.dumps(pipeline_results, indent=2, default=str))
            sys.exit(1)

        # Step 6: Translate
        click.echo("🌍 Running Translator...", err=True)
        translate_result = translator.run_translation()
        pipeline_results["translate"] = translate_result

        # Final results
        click.echo("✅ Pipeline completed successfully!", err=True)
        click.echo(json.dumps(pipeline_results, indent=2, default=str))

        sys.exit(0)

    except Exception as e:
        click.echo(f"❌ Pipeline failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Check system status and recent activity."""
    try:
        config = load_config()

        clickhouse = ClickHouseClient(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            username=config.clickhouse.username,
            password=config.clickhouse.password
        )

        # Check ClickHouse connection
        if not clickhouse.ready():
            click.echo("❌ ClickHouse connection failed", err=True)
            sys.exit(1)

        # Get recent activity
        try:
            query = """
            SELECT
                COUNT(*) as total_episodes,
                COUNT(CASE WHEN status = 'published' THEN 1 END) as published_episodes,
                COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_episodes,
                MAX(ts) as last_episode
            FROM episodes
            WHERE ts > now() - INTERVAL 7 DAY
            """

            result = clickhouse.client.query(query)
            if result.result_rows:
                row = result.result_rows[0]
                status_data = {
                    "total_episodes": row[0],
                    "published_episodes": row[1],
                    "draft_episodes": row[2],
                    "last_episode": row[3].isoformat() if row[3] else None
                }
            else:
                status_data = {
                    "total_episodes": 0,
                    "published_episodes": 0,
                    "draft_episodes": 0,
                    "last_episode": None
                }
        except Exception as e:
            status_data = {"error": str(e)}

        click.echo("📊 System Status:", err=True)
        click.echo(json.dumps(status_data, indent=2, default=str))

        sys.exit(0)

    except Exception as e:
        click.echo(f"❌ Status check failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()

