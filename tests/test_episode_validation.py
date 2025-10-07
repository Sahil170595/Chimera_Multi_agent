"""Tests for episode schema validation."""

import pytest
from schemas.episode import EpisodeValidator, EpisodeMetadata, validate_episode_file


class TestEpisodeMetadata:
    """Test episode metadata validation."""

    def test_valid_metadata(self):
        """Test valid metadata passes validation."""
        metadata = {
            "title": "Test Episode",
            "series": "Chimera",
            "episode": 1,
            "date": "2023-01-01T00:00:00",
            "models": ["gpt-4"],
            "run_id": "123e4567-e89b-12d3-a456-426614174000",
            "commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
            "latency_ms_p95": 1000,
            "tokens_in": 500,
            "tokens_out": 300,
            "cost_usd": 0.01
        }

        episode = EpisodeMetadata(**metadata)
        assert episode.title == "Test Episode"
        assert episode.series == "Chimera"
        assert episode.episode == 1

    def test_invalid_series(self):
        """Test invalid series fails validation."""
        metadata = {
            "title": "Test Episode",
            "series": "InvalidSeries",
            "episode": 1,
            "date": "2023-01-01T00:00:00",
            "models": ["gpt-4"],
            "run_id": "123e4567-e89b-12d3-a456-426614174000",
            "commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
            "latency_ms_p95": 1000,
            "tokens_in": 500,
            "tokens_out": 300,
            "cost_usd": 0.01
        }

        with pytest.raises(ValueError, match="Series must be one of"):
            EpisodeMetadata(**metadata)

    def test_invalid_run_id(self):
        """Test invalid run_id fails validation."""
        metadata = {
            "title": "Test Episode",
            "series": "Chimera",
            "episode": 1,
            "date": "2023-01-01T00:00:00",
            "models": ["gpt-4"],
            "run_id": "invalid-uuid",
            "commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
            "latency_ms_p95": 1000,
            "tokens_in": 500,
            "tokens_out": 300,
            "cost_usd": 0.01
        }

        with pytest.raises(ValueError, match="run_id must be a valid UUID"):
            EpisodeMetadata(**metadata)

    def test_invalid_commit_sha(self):
        """Test invalid commit_sha fails validation."""
        metadata = {
            "title": "Test Episode",
            "series": "Chimera",
            "episode": 1,
            "date": "2023-01-01T00:00:00",
            "models": ["gpt-4"],
            "run_id": "123e4567-e89b-12d3-a456-426614174000",
            "commit_sha": "short",
            "latency_ms_p95": 1000,
            "tokens_in": 500,
            "tokens_out": 300,
            "cost_usd": 0.01
        }

        with pytest.raises(ValueError, match="commit_sha must be 40 characters"):
            EpisodeMetadata(**metadata)

    def test_negative_episode_number(self):
        """Test negative episode number fails validation."""
        metadata = {
            "title": "Test Episode",
            "series": "Chimera",
            "episode": -1,
            "date": "2023-01-01T00:00:00",
            "models": ["gpt-4"],
            "run_id": "123e4567-e89b-12d3-a456-426614174000",
            "commit_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
            "latency_ms_p95": 1000,
            "tokens_in": 500,
            "tokens_out": 300,
            "cost_usd": 0.01
        }

        with pytest.raises(ValueError, match="Episode number must be positive"):
            EpisodeMetadata(**metadata)


class TestEpisodeValidator:
    """Test episode file validation."""

    def test_valid_episode_file(self, tmp_path):
        """Test valid episode file passes validation."""
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

        episode_file = tmp_path / "test-episode.md"
        episode_file.write_text(episode_content)

        validator = EpisodeValidator()
        is_valid, errors, warnings = validator.validate_file(episode_file)

        assert is_valid
        assert len(errors) == 0

    def test_missing_frontmatter(self, tmp_path):
        """Test file without front-matter fails validation."""
        episode_file = tmp_path / "test-episode.md"
        episode_file.write_text("No front-matter here")

        validator = EpisodeValidator()
        is_valid, errors, warnings = validator.validate_file(episode_file)

        assert not is_valid
        assert len(errors) > 0
        assert "File must start with YAML front-matter" in errors[0]

    def test_missing_sections(self, tmp_path):
        """Test file with missing sections fails validation."""
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

Missing the last section!
"""

        episode_file = tmp_path / "test-episode.md"
        episode_file.write_text(episode_content)

        validator = EpisodeValidator()
        is_valid, errors, warnings = validator.validate_file(episode_file)

        assert not is_valid
        assert any("Missing required sections" in error for error in errors)

    def test_wrong_section_order(self, tmp_path):
        """Test file with wrong section order fails validation."""
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

## Why it matters

Wrong order!

## What changed

This is a test episode.

## Benchmarks (summary)

Good performance.

## Next steps

Continue testing.

## Links & artifacts

- [Test Link](https://example.com)
"""

        episode_file = tmp_path / "test-episode.md"
        episode_file.write_text(episode_content)

        validator = EpisodeValidator()
        is_valid, errors, warnings = validator.validate_file(episode_file)

        assert not is_valid
        assert any("Section order violation" in error for error in errors)

    def test_nonexistent_file(self, tmp_path):
        """Test validation of nonexistent file."""
        episode_file = tmp_path / "nonexistent.md"

        validator = EpisodeValidator()
        is_valid, errors, warnings = validator.validate_file(episode_file)

        assert not is_valid
        assert "File does not exist" in errors[0]


class TestValidateEpisodeFile:
    """Test convenience validation function."""

    def test_validate_episode_file(self, tmp_path):
        """Test validate_episode_file function."""
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

        episode_file = tmp_path / "test-episode.md"
        episode_file.write_text(episode_content)

        is_valid, errors, warnings = validate_episode_file(episode_file)

        assert is_valid
        assert len(errors) == 0

