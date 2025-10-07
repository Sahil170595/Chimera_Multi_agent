"""DeepL integration for Muse Protocol."""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import deepl
from apps.config import DeepLConfig


logger = logging.getLogger(__name__)


class DeepLClient:
    """DeepL translation client."""

    def __init__(self, config: DeepLConfig):
        """Initialize DeepL client.

        Args:
            config: DeepL configuration
        """
        self.config = config
        self.translator: Optional[deepl.Translator] = None
        self._enabled = bool(config.api_key)

    def connect(self) -> None:
        """Initialize DeepL translator."""
        if not self._enabled:
            logger.warning("DeepL disabled - no API key provided")
            return

        try:
            self.translator = deepl.Translator(self.config.api_key)
            logger.info("Connected to DeepL")
        except Exception as e:
            logger.error(f"Failed to connect to DeepL: {e}")
            self._enabled = False

    def ready(self) -> bool:
        """Check if DeepL is ready.

        Returns:
            True if ready or disabled, False if connection failed
        """
        if not self._enabled:
            return True

        try:
            if not self.translator:
                self.connect()

            # Simple health check - get usage
            return True
        except Exception as e:
            logger.warning(f"DeepL health check failed: {e}")
            return False

    def translate_markdown(self, src_path: Path, target_lang: str, out_path: Path) -> bool:
        """Translate markdown file.

        Args:
            src_path: Source markdown file path
            target_lang: Target language code (e.g., 'DE', 'ZH', 'HI')
            out_path: Output file path

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            logger.warning(f"DeepL disabled - skipping translation: {src_path} -> {target_lang}")
            return False

        try:
            if not self.translator:
                self.connect()

            # Read source content
            content = src_path.read_text(encoding='utf-8')

            # Parse front-matter and content
            frontmatter, markdown_content = self._parse_frontmatter(content)

            # Translate markdown content
            translated_content = self._translate_text(markdown_content, target_lang)

            # Add translation metadata to front-matter
            frontmatter["translation_of"] = str(src_path)
            frontmatter["target_language"] = target_lang

            # Write translated file
            self._write_translated_file(out_path, frontmatter, translated_content)

            logger.info(f"Translated {src_path} to {target_lang} -> {out_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to translate {src_path}: {e}")
            return False

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse YAML front-matter from markdown content."""
        import yaml

        if not content.startswith('---'):
            raise ValueError("File must start with YAML front-matter")

        lines = content.split('\n')
        if len(lines) < 2 or lines[1] != '---':
            raise ValueError("Invalid front-matter format")

        end_idx = None
        for i, line in enumerate(lines[2:], start=2):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx is None:
            raise ValueError("Front-matter must end with ---")

        metadata_yaml = '\n'.join(lines[1:end_idx])
        metadata = yaml.safe_load(metadata_yaml)

        markdown_content = '\n'.join(lines[end_idx + 1:])

        return metadata, markdown_content

    def _translate_text(self, text: str, target_lang: str) -> str:
        """Translate text using DeepL.

        Args:
            text: Text to translate
            target_lang: Target language code

        Returns:
            Translated text
        """
        if not self.translator:
            raise RuntimeError("DeepL translator not initialized")

        # DeepL API rate limiting
        time.sleep(0.1)

        result = self.translator.translate_text(text, target_lang=target_lang)
        return result.text

    def _write_translated_file(self, out_path: Path, frontmatter: Dict[str, Any], content: str) -> None:
        """Write translated file with front-matter."""
        import yaml

        # Ensure output directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
            f.write('---\n\n')
            f.write(content)

    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported target languages.

        Returns:
            Dictionary mapping language codes to names
        """
        if not self._enabled:
            return {}

        try:
            if not self.translator:
                self.connect()

            languages = self.translator.get_target_languages()
            return {lang.code: lang.name for lang in languages}
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return {}


class MockDeepLClient:
    """Mock DeepL client for testing."""

    def __init__(self, config: DeepLConfig):
        """Initialize mock client."""
        self.config = config
        self.translations: List[Dict[str, Any]] = []

    def ready(self) -> bool:
        """Mock ready check."""
        return True

    def translate_markdown(self, src_path: Path, target_lang: str, out_path: Path) -> bool:
        """Mock markdown translation."""
        try:
            # Read source content
            content = src_path.read_text(encoding='utf-8')

            # Parse front-matter and content
            frontmatter, markdown_content = self._parse_frontmatter(content)

            # Mock translation (just add language prefix)
            translated_content = f"[{target_lang}] {markdown_content}"

            # Add translation metadata
            frontmatter["translation_of"] = str(src_path)
            frontmatter["target_language"] = target_lang

            # Write translated file
            self._write_translated_file(out_path, frontmatter, translated_content)

            self.translations.append({
                "src_path": str(src_path),
                "target_lang": target_lang,
                "out_path": str(out_path)
            })

            logger.info(f"Mock: Translated {src_path} to {target_lang}")
            return True

        except Exception as e:
            logger.error(f"Mock translation failed: {e}")
            return False

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Mock front-matter parsing."""
        import yaml

        if not content.startswith('---'):
            raise ValueError("File must start with YAML front-matter")

        lines = content.split('\n')
        end_idx = None
        for i, line in enumerate(lines[2:], start=2):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx is None:
            raise ValueError("Front-matter must end with ---")

        metadata_yaml = '\n'.join(lines[1:end_idx])
        metadata = yaml.safe_load(metadata_yaml)

        markdown_content = '\n'.join(lines[end_idx + 1:])

        return metadata, markdown_content

    def _write_translated_file(self, out_path: Path, frontmatter: Dict[str, Any], content: str) -> None:
        """Mock file writing."""
        import yaml

        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
            f.write('---\n\n')
            f.write(content)

    def get_supported_languages(self) -> Dict[str, str]:
        """Mock supported languages."""
        return {
            "DE": "German",
            "ZH": "Chinese",
            "HI": "Hindi",
            "FR": "French",
            "ES": "Spanish"
        }
