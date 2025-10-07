"""Repository writer integration for Muse Protocol."""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from apps.config import RepoConfig


logger = logging.getLogger(__name__)


class RepoWriter:
    """Git repository writer."""

    def __init__(self, config: RepoConfig):
        """Initialize repository writer.

        Args:
            config: Repository configuration
        """
        self.config = config
        self.repo_path = Path(config.path).resolve()

    def ready(self) -> bool:
        """Check if repository is ready.

        Returns:
            True if ready, False otherwise
        """
        try:
            # Check if it's a git repository
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            logger.warning(f"Not a git repository: {self.repo_path}")
            return False

    def write_file(self, file_path: Path, content: str, frontmatter: Optional[Dict[str, Any]] = None) -> bool:
        """Write file with optional front-matter.

        Args:
            file_path: File path relative to repo root
            content: File content
            frontmatter: Optional front-matter metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self.repo_path / file_path

            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            if frontmatter:
                content_with_frontmatter = self._add_frontmatter(content, frontmatter)
                full_path.write_text(content_with_frontmatter, encoding='utf-8')
            else:
                full_path.write_text(content, encoding='utf-8')

            logger.info(f"Wrote file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return False

    def add_and_commit(self, file_path: Path, message: str) -> bool:
        """Add file to git and commit.

        Args:
            file_path: File path relative to repo root
            message: Commit message

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add file
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=self.repo_path,
                check=True
            )

            # Commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True,
                env={
                    "GIT_AUTHOR_NAME": self.config.author_name,
                    "GIT_AUTHOR_EMAIL": self.config.author_email,
                    "GIT_COMMITTER_NAME": self.config.author_name,
                    "GIT_COMMITTER_EMAIL": self.config.author_email,
                }
            )

            logger.info(f"Committed file: {file_path}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit file {file_path}: {e}")
            return False

    def get_current_commit_sha(self) -> Optional[str]:
        """Get current commit SHA.

        Returns:
            Commit SHA or None if failed
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get commit SHA: {e}")
            return None

    def get_current_branch(self) -> Optional[str]:
        """Get current branch name.

        Returns:
            Branch name or None if failed
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get current branch: {e}")
            return None

    def _add_frontmatter(self, content: str, frontmatter: Dict[str, Any]) -> str:
        """Add YAML front-matter to content.

        Args:
            content: Original content
            frontmatter: Front-matter metadata

        Returns:
            Content with front-matter
        """
        import yaml

        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

        return f"---\n{frontmatter_yaml}---\n\n{content}"


class MockRepoWriter:
    """Mock repository writer for testing."""

    def __init__(self, config: RepoConfig):
        """Initialize mock writer."""
        self.config = config
        self.written_files: List[Dict[str, Any]] = []
        self.commits: List[Dict[str, Any]] = []

    def ready(self) -> bool:
        """Mock ready check."""
        return True

    def write_file(self, file_path: Path, content: str, frontmatter: Optional[Dict[str, Any]] = None) -> bool:
        """Mock file writing."""
        self.written_files.append({
            "file_path": str(file_path),
            "content": content,
            "frontmatter": frontmatter
        })
        logger.info(f"Mock: Wrote file {file_path}")
        return True

    def add_and_commit(self, file_path: Path, message: str) -> bool:
        """Mock commit."""
        self.commits.append({
            "file_path": str(file_path),
            "message": message
        })
        logger.info(f"Mock: Committed file {file_path}")
        return True

    def get_current_commit_sha(self) -> Optional[str]:
        """Mock commit SHA."""
        return "mock_commit_sha_40_characters_long"

    def get_current_branch(self) -> Optional[str]:
        """Mock branch name."""
        return "main"
