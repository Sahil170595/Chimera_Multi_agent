"""CLI application for Muse Protocol."""

import logging
import sys
import uuid
from pathlib import Path
from typing import List
import click
from apps.config import load_config
from schemas.episode import EpisodeValidator
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


@click.group()
@click.option('--env-file', default='.env', help='Environment file path')
@click.pass_context
def cli(ctx, env_file):
    """Muse Protocol CLI - Multi-agent content authoring with i18n."""
    try:
        config = load_config(env_file)
        ctx.ensure_object(dict)
        ctx.obj['config'] = config
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@cli.group()
def episodes():
    """Episode management commands."""
    pass


@episodes.command()
@click.option('--series', type=click.Choice(['chimera', 'banterpacks']), required=True,
              help='Series name')
@click.option('--sql', help='Optional SQL query for data analysis')
@click.pass_context
def new(ctx, series, sql):
    """Create a new episode."""
    config = ctx.obj['config']

    try:
        # Initialize clients
        clickhouse = ClickHouseClient(config.clickhouse)
        datadog = DatadogClient(config.datadog)
        repo_writer = RepoWriter(config.repo)

        # Get current commit SHA
        commit_sha = repo_writer.get_current_commit_sha()
        if not commit_sha:
            click.echo("Error: Could not get current commit SHA", err=True)
            sys.exit(1)

        # Generate episode
        if series == 'chimera':
            author = ChimeraAuthor(config.agent)
        else:
            author = BanterpacksAuthor(config.agent)

        episode_data = author.generate_episode(commit_sha, sql)
        metadata = episode_data['metadata']
        content = episode_data['content']

        # Check if episode already exists (idempotency)
        if clickhouse.episode_exists(metadata['run_id']):
            click.echo(f"Episode with run_id {metadata['run_id']} already exists. Skipping.")
            return

        # Write episode file
        series_dir = Path(f"posts/{series}")
        series_dir.mkdir(parents=True, exist_ok=True)

        episode_file = series_dir / f"ep-{metadata['episode']:03d}.md"

        if not repo_writer.write_file(episode_file, content, metadata):
            click.echo(f"Error: Failed to write episode file {episode_file}", err=True)
            sys.exit(1)

        # Commit to git
        commit_message = f"Add {series} episode {metadata['episode']}: {metadata['title']}"
        if not repo_writer.add_and_commit(episode_file, commit_message):
            click.echo("Warning: Failed to commit episode file", err=True)

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

        clickhouse.insert_episode(episode_record)

        # Send metrics to Datadog
        datadog.send_episode_metrics(metadata)

        click.echo(f"✅ Created {series} episode {metadata['episode']}: {episode_file}")

    except Exception as e:
        logger.error(f"Failed to create episode: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def i18n():
    """Internationalization commands."""
    pass


@i18n.command()
@click.option('--langs', required=True, help='Comma-separated list of languages (e.g., de,zh,hi)')
@click.option('--series', help='Specific series to translate (optional)')
@click.pass_context
def sync(ctx, langs, series):
    """Sync translations for episodes."""
    config = ctx.obj['config']

    try:
        # Parse languages
        target_langs = [lang.strip().upper() for lang in langs.split(',')]

        # Initialize clients
        deepl = DeepLClient(config.deepl)
        clickhouse = ClickHouseClient(config.clickhouse)
        datadog = DatadogClient(config.datadog)

        # Find source episodes
        posts_dir = Path("posts")
        if not posts_dir.exists():
            click.echo("No posts directory found", err=True)
            sys.exit(1)

        source_files = []
        if series:
            series_dir = posts_dir / series
            if series_dir.exists():
                source_files.extend(series_dir.glob("*.md"))
        else:
            for series_dir in posts_dir.iterdir():
                if series_dir.is_dir():
                    source_files.extend(series_dir.glob("*.md"))

        if not source_files:
            click.echo("No source episodes found", err=True)
            sys.exit(1)

        # Translate each file
        for src_file in source_files:
            click.echo(f"Translating {src_file}...")

            for lang in target_langs:
                # Determine output path
                src_series = src_file.parent.name
                out_dir = Path(f"posts_i18n/{lang.lower()}/{src_series}")
                out_file = out_dir / src_file.name

                # Skip if translation already exists
                if out_file.exists():
                    click.echo(f"  Skipping {lang} - already exists")
                    continue

                # Translate
                if deepl.translate_markdown(src_file, lang, out_file):
                    click.echo(f"  ✅ Translated to {lang}")

                    # Log translation to ClickHouse
                    translation_record = TranslationRecord(
                        run_id=str(uuid.uuid4()),
                        source_series=src_series,
                        source_episode=int(src_file.stem.split('-')[1]),  # Extract episode number
                        target_language=lang,
                        translation_of=str(src_file)
                    )

                    clickhouse.insert_translation(translation_record)

                    # Send metrics
                    datadog.send_translation_metrics({
                        "source_series": src_series,
                        "target_language": lang
                    })
                else:
                    click.echo(f"  ❌ Failed to translate to {lang}")

        click.echo("✅ Translation sync completed")

    except Exception as e:
        logger.error(f"Failed to sync translations: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def check(ctx):
    """Validate all posts for schema compliance."""
    try:
        posts_dir = Path("posts")
        if not posts_dir.exists():
            click.echo("No posts directory found", err=True)
            sys.exit(1)

        validator = EpisodeValidator()
        results = validator.validate_all_posts(posts_dir)

        if not results:
            click.echo("No episode files found")
            return

        # Report results
        valid_count = 0
        invalid_count = 0

        for file_path, (is_valid, errors, warnings) in results.items():
            if is_valid:
                click.echo(f"✅ {file_path}")
                valid_count += 1
            else:
                click.echo(f"❌ {file_path}")
                invalid_count += 1

                for error in errors:
                    click.echo(f"  Error: {error}")

                for warning in warnings:
                    click.echo(f"  Warning: {warning}")

        click.echo(f"\nSummary: {valid_count} valid, {invalid_count} invalid")

        if invalid_count > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to validate posts: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    cli()


if __name__ == '__main__':
    main()
