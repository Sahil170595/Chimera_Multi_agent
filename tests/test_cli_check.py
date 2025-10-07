"""Tests for CLI check command."""

from pathlib import Path
from click.testing import CliRunner
from apps.cli import cli


class TestCLICheck:
    """Test CLI check command."""

    def test_check_no_posts_directory(self, tmp_path):
        """Test check command with no posts directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['check'])

            assert result.exit_code == 1
            assert "No posts directory found" in result.output

    def test_check_empty_posts_directory(self, tmp_path):
        """Test check command with empty posts directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create empty posts directory
            posts_dir = Path("posts")
            posts_dir.mkdir()

            result = runner.invoke(cli, ['check'])

            assert result.exit_code == 0
            assert "No episode files found" in result.output

    def test_check_valid_episode(self, tmp_path):
        """Test check command with valid episode."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create posts directory structure
            posts_dir = Path("posts")
            chimera_dir = posts_dir / "chimera"
            chimera_dir.mkdir(parents=True)

            # Create valid episode file
            episode_content = """---
title: Test Episode
series: Chimera
episode: 1
date: 2023-01-01T00:00:00
models: [gpt-4]
run_id: 123e4567-e89b-12d3-a456-426614174000
commit_sha: a1b2c3d4e5f6789012345678901234567890abcd
latency_ms_p95: 1000
tokens_in: 500
tokens_out: 300
cost_usd: 0.01
---

## What changed

This is a test episode.

## Why it matters

It matters for testing.

## Benchmarks (summary)

Good performance.

## Next steps

Continue testing.

## Links & artifacts

- [Test Link](https://example.com)
"""

            episode_file = chimera_dir / "ep-001.md"
            episode_file.write_text(episode_content)

            result = runner.invoke(cli, ['check'])

            assert result.exit_code == 0
            assert "✅" in result.output
            assert "1 valid, 0 invalid" in result.output

    def test_check_invalid_episode(self, tmp_path):
        """Test check command with invalid episode."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create posts directory structure
            posts_dir = Path("posts")
            chimera_dir = posts_dir / "chimera"
            chimera_dir.mkdir(parents=True)

            # Create invalid episode file (missing sections)
            episode_content = """---
title: Test Episode
series: Chimera
episode: 1
date: 2023-01-01T00:00:00
models: [gpt-4]
run_id: 123e4567-e89b-12d3-a456-426614174000
commit_sha: a1b2c3d4e5f6789012345678901234567890abcd
latency_ms_p95: 1000
tokens_in: 500
tokens_out: 300
cost_usd: 0.01
---

## What changed

This is a test episode.

## Why it matters

It matters for testing.

Missing required sections!
"""

            episode_file = chimera_dir / "ep-001.md"
            episode_file.write_text(episode_content)

            result = runner.invoke(cli, ['check'])

            assert result.exit_code == 1
            assert "❌" in result.output
            assert "Missing required sections" in result.output
            assert "0 valid, 1 invalid" in result.output

    def test_check_multiple_episodes(self, tmp_path):
        """Test check command with multiple episodes."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create posts directory structure
            posts_dir = Path("posts")
            chimera_dir = posts_dir / "chimera"
            banterpacks_dir = posts_dir / "banterpacks"
            chimera_dir.mkdir(parents=True)
            banterpacks_dir.mkdir(parents=True)

            # Create valid Chimera episode
            chimera_content = """---
title: Chimera Episode
series: Chimera
episode: 1
date: 2023-01-01T00:00:00
models: [gpt-4]
run_id: 123e4567-e89b-12d3-a456-426614174000
commit_sha: a1b2c3d4e5f6789012345678901234567890abcd
latency_ms_p95: 1000
tokens_in: 500
tokens_out: 300
cost_usd: 0.01
---

## What changed

Chimera changes.

## Why it matters

Chimera matters.

## Benchmarks (summary)

Chimera performance.

## Next steps

Chimera next steps.

## Links & artifacts

- [Chimera Link](https://chimera.com)
"""

            chimera_file = chimera_dir / "ep-001.md"
            chimera_file.write_text(chimera_content)

            # Create valid Banterpacks episode
            banterpacks_content = """---
title: Banterpacks Episode
series: Banterpacks
episode: 1
date: 2023-01-01T00:00:00
models: [gpt-4]
run_id: 123e4567-e89b-12d3-a456-426614174001
commit_sha: a1b2c3d4e5f6789012345678901234567890abcd
latency_ms_p95: 1000
tokens_in: 500
tokens_out: 300
cost_usd: 0.01
---

## What changed

Banterpacks changes.

## Why it matters

Banterpacks matters.

## Benchmarks (summary)

Banterpacks performance.

## Next steps

Banterpacks next steps.

## Links & artifacts

- [Banterpacks Link](https://banterpacks.com)
"""

            banterpacks_file = banterpacks_dir / "ep-001.md"
            banterpacks_file.write_text(banterpacks_content)

            result = runner.invoke(cli, ['check'])

            assert result.exit_code == 0
            assert "✅" in result.output
            assert "2 valid, 0 invalid" in result.output

    def test_check_mixed_validity(self, tmp_path):
        """Test check command with mix of valid and invalid episodes."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create posts directory structure
            posts_dir = Path("posts")
            chimera_dir = posts_dir / "chimera"
            chimera_dir.mkdir(parents=True)

            # Create valid episode
            valid_content = """---
title: Valid Episode
series: Chimera
episode: 1
date: 2023-01-01T00:00:00
models: [gpt-4]
run_id: 123e4567-e89b-12d3-a456-426614174000
commit_sha: a1b2c3d4e5f6789012345678901234567890abcd
latency_ms_p95: 1000
tokens_in: 500
tokens_out: 300
cost_usd: 0.01
---

## What changed

Valid changes.

## Why it matters

Valid matters.

## Benchmarks (summary)

Valid performance.

## Next steps

Valid next steps.

## Links & artifacts

- [Valid Link](https://valid.com)
"""

            valid_file = chimera_dir / "ep-001.md"
            valid_file.write_text(valid_content)

            # Create invalid episode (wrong series)
            invalid_content = """---
title: Invalid Episode
series: InvalidSeries
episode: 2
date: 2023-01-01T00:00:00
models: [gpt-4]
run_id: 123e4567-e89b-12d3-a456-426614174001
commit_sha: a1b2c3d4e5f6789012345678901234567890abcd
latency_ms_p95: 1000
tokens_in: 500
tokens_out: 300
cost_usd: 0.01
---

## What changed

Invalid changes.

## Why it matters

Invalid matters.

## Benchmarks (summary)

Invalid performance.

## Next steps

Invalid next steps.

## Links & artifacts

- [Invalid Link](https://invalid.com)
"""

            invalid_file = chimera_dir / "ep-002.md"
            invalid_file.write_text(invalid_content)

            result = runner.invoke(cli, ['check'])

            assert result.exit_code == 1
            assert "✅" in result.output  # Valid episode
            assert "❌" in result.output  # Invalid episode
            assert "Series must be one of" in result.output
            assert "1 valid, 1 invalid" in result.output
