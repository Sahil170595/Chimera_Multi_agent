"""Episode schema validation for Muse Protocol."""

import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, validator


class EpisodeMetadata(BaseModel):
    """Episode front-matter metadata."""
    title: str = Field(..., description="Episode title")
    series: str = Field(..., description="Series name (Banterpacks or\n    Chimera)")
    episode: int = Field(..., description="Episode number")
    date: datetime = Field(..., description="Episode date in ISO8601 format")
    models: List[str] = Field(..., description="List of models used")
    run_id: str = Field(..., description="Unique run identifier")
    commit_sha: str = Field(..., description="Git commit SHA (40 characters)")
    latency_ms_p95: int = Field(..., description="95th percentile latency in milliseconds")
    tokens_in: int = Field(..., description="Input tokens count")
    tokens_out: int = Field(..., description="Output tokens count")
    cost_usd: float = Field(..., description="Cost in USD")
    benchmarks: Optional[Dict[str, Any]] = Field(default=None, description="Benchmark data")

    @validator('series')
    def validate_series(cls, v):
        """Validate series name."""
        valid_series = ['Banterpacks', 'Chimera']
        if v not in valid_series:
            raise ValueError(f"Series must be one of {valid_series}, got: {v}")
        return v

    @validator('run_id')
    def validate_run_id(cls, v):
        """Validate run_id is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"run_id must be a valid UUID, got: {v}")
        return v

    @validator('commit_sha')
    def validate_commit_sha(cls, v):
        """Validate commit SHA is 40 characters."""
        if len(v) != 40:
            raise ValueError(f"commit_sha must be 40 characters, got {len(v)}")
        if not re.match(r'^[a-f0-9]+$', v):
            raise ValueError("commit_sha must be hexadecimal")
        return v

    @validator('episode')
    def validate_episode(cls, v):
        """Validate episode number is positive."""
        if v <= 0:
            raise ValueError(f"Episode number must be positive, got: {v}")
        return v

    @validator('latency_ms_p95', 'tokens_in', 'tokens_out')
    def validate_positive_numbers(cls, v):
        """Validate numeric fields are non-negative."""
        if v < 0:
            raise ValueError(f"Value must be non-negative, got: {v}")
        return v

    @validator('cost_usd')
    def validate_cost(cls, v):
        """Validate cost is non-negative."""
        if v < 0:
            raise ValueError(f"Cost must be non-negative, got: {v}")
        return v


class EpisodeValidator:
    """Validates episode markdown files against schema requirements."""

    REQUIRED_SECTIONS = [
        "## What changed",
        "## Why it matters",
        "## Benchmarks (summary)",
        "## Next steps",
        "## Links & artifacts"
    ]

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_file(self, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Validate an episode file.

        Args:
            file_path: Path to the episode markdown file

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        if not file_path.exists():
            self.errors.append(f"File does not exist: {file_path}")
            return False, self.errors, self.warnings

        try:
            content = file_path.read_text(encoding='utf-8')
            metadata, markdown_content = self._parse_frontmatter(content)

            # Validate metadata
            self._validate_metadata(metadata)

            # Validate sections
            self._validate_sections(markdown_content)

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            self.errors.append(f"Failed to parse file: {e}")
            return False, self.errors, self.warnings

    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML front-matter from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (metadata_dict, markdown_content)
        """
        if not content.startswith('---'):
            raise ValueError("File must start with YAML front-matter (---)")

        # Find end of front-matter
        lines = content.split('\n')
        if len(lines) < 2:
            raise ValueError("Invalid front-matter format")

        end_idx = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx is None:
            raise ValueError("Front-matter must end with ---")

        # Extract metadata
        metadata_yaml = '\n'.join(lines[1:end_idx])
        metadata = yaml.safe_load(metadata_yaml)

        if metadata is None:
            raise ValueError("Empty front-matter")

        # Extract markdown content
        markdown_content = '\n'.join(lines[end_idx + 1:])

        return metadata, markdown_content

    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """Validate episode metadata.

        Args:
            metadata: Parsed metadata dictionary
        """
        try:
            EpisodeMetadata(**metadata)
        except Exception as e:
            self.errors.append(f"Metadata validation failed: {e}")

    def _validate_sections(self, content: str) -> None:
        """Validate required sections are present and in order.

        Args:
            content: Markdown content without front-matter
        """
        lines = content.split('\n')
        section_indices = []

        # Find section headers
        for i, line in enumerate(lines):
            line = line.strip()
            if line in self.REQUIRED_SECTIONS:
                section_indices.append((i, line))

        # Check all required sections are present
        found_sections = [section for _, section in section_indices]
        missing_sections = set(self.REQUIRED_SECTIONS) - set(found_sections)

        if missing_sections:
            self.errors.append(f"Missing required sections: {', '.join(missing_sections)}")

        # Check sections are in correct order
        if section_indices:
            expected_order = self.REQUIRED_SECTIONS
            actual_order = [section for _, section in section_indices]

            # Find first deviation from expected order
            for i, (expected, actual) in enumerate(zip(expected_order, actual_order)):
                if expected != actual:
                    self.errors.append(
                        f"Section order violation: expected '{expected}' at position {i}, "
                        f"found '{actual}'"
                    )
                    break

    def validate_all_posts(self, posts_dir: Path) -> Dict[str, Tuple[bool, List[str], List[str]]]:
        """Validate all episode files in a directory.

        Args:
            posts_dir: Directory containing episode files

        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}

        if not posts_dir.exists():
            return results

        # Find all markdown files recursively
        for md_file in posts_dir.rglob("*.md"):
            is_valid, errors, warnings = self.validate_file(md_file)
            results[str(md_file)] = (is_valid, errors, warnings)

        return results


def validate_episode_file(file_path: Path) -> Tuple[bool, List[str], List[str]]:
    """Convenience function to validate a single episode file.

    Args:
        file_path: Path to episode markdown file

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = EpisodeValidator()
    return validator.validate_file(file_path)


def validate_all_episodes(posts_dir: Path) -> Dict[str, Tuple[bool, List[str], List[str]]]:
    """Convenience function to validate all episodes.

    Args:
        posts_dir: Directory containing episode files

    Returns:
        Dictionary mapping file paths to validation results
    """
    validator = EpisodeValidator()
    return validator.validate_all_posts(posts_dir)
