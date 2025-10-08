"""i18n Translator Agent - Translates episodes to multiple languages."""

import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient
from integrations.deepl import DeepLClient as LegacyDeepLClient
from integrations.mcp_client import DeepLClient as MCPDeepLClient

logger = logging.getLogger(__name__)


class I18nTranslator:
    """i18n Translator Agent - Translates episodes to multiple languages."""

    def __init__(
            self,
            clickhouse_client: ClickHouseClient,
            datadog_client: DatadogClient,
            deepl_client: Optional[MCPDeepLClient] = None):
        """Initialize i18n Translator.

        Args:
            clickhouse_client: ClickHouse client instance
            datadog_client: Datadog client instance
            deepl_client: DeepL MCP client (optional)
        """
        self.clickhouse = clickhouse_client
        self.datadog = datadog_client
        self.deepl_mcp = deepl_client
        self.deepl_legacy = LegacyDeepLClient() if not deepl_client else None
        self.banterblogs_dir = Path("../Banterblogs")
        self.supported_languages = ["de", "zh", "hi"]

    def get_episodes_to_translate(self, days: int = 2) -> List[Dict[str, Any]]:
        """Get episodes that need translation.

        Args:
            days: Number of days to look back

        Returns:
            List of episodes to translate
        """
        try:
            query = """
            SELECT episode, run_id, hearts_commit, packs_commit, path,
                   confidence_score, correlation_strength, status
            FROM episodes
            WHERE lang = 'en' AND ts > now() - INTERVAL %(days)s DAY
            ORDER BY ts DESC
            """

            result = self.clickhouse.client.query(query, parameters={'days': days})

            episodes = []
            for row in result.result_rows:
                episodes.append({
                    "episode": row[0],
                    "run_id": row[1],
                    "hearts_commit": row[2],
                    "packs_commit": row[3],
                    "path": row[4],
                    "confidence_score": row[5],
                    "correlation_strength": row[6],
                    "status": row[7]
                })

            logger.info(f"Found {len(episodes)} episodes to translate")
            return episodes

        except Exception as e:
            logger.error(f"Failed to get episodes to translate: {e}")
            return []

    def check_existing_translations(self, episode_num: int) -> Dict[str, bool]:
        """Check which translations already exist.

        Args:
            episode_num: Episode number

        Returns:
            Dictionary of language -> exists mapping
        """
        try:
            query = """
            SELECT lang FROM episodes
            WHERE episode = %(episode_num)s AND lang != 'en'
            """

            result = self.clickhouse.client.query(query, parameters={'episode_num': episode_num})

            existing_langs = {row[0] for row in result.result_rows}

            return {
                lang: lang in existing_langs
                for lang in self.supported_languages
            }

        except Exception as e:
            logger.error(f"Failed to check existing translations: {e}")
            return {lang: False for lang in self.supported_languages}

    def read_episode_content(self, episode_path: str) -> str:
        """Read episode content from file.

        Args:
            episode_path: Path to episode file

        Returns:
            Episode content
        """
        try:
            with open(episode_path, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to read episode content: {e}")
            return ""

    def preserve_frontmatter(self, content: str) -> tuple[str, str]:
        """Extract and preserve frontmatter from episode content.

        Args:
            content: Episode content

        Returns:
            Tuple of (frontmatter, body)
        """
        try:
            lines = content.split('\n')

            if lines and lines[0] == '---':
                # Find closing frontmatter
                for i, line in enumerate(lines[1:], 1):
                    if line == '---':
                        frontmatter = '\n'.join(lines[: i + 1])
                        body = '\n'.join(lines[i + 1 :])
                        return frontmatter, body

            # No frontmatter found
            return "", content

        except Exception as e:
            logger.error(f"Failed to preserve frontmatter: {e}")
            return "", content

    def translate_content(self, content: str, target_lang: str) -> str:
        """Translate content to target language.

        Args:
            content: Content to translate
            target_lang: Target language code

        Returns:
            Translated content
        """
        try:
            # Preserve frontmatter
            frontmatter, body = self.preserve_frontmatter(content)

            # Translate body content
            translated_body = self.deepl.translate_markdown(body, target_lang)

            # Combine frontmatter and translated body
            if frontmatter:
                return frontmatter + '\n' + translated_body
            else:
                return translated_body

        except Exception as e:
            logger.error(f"Failed to translate content to {target_lang}: {e}")
            return content  # Return original content on failure

    def save_translation(self, content: str, episode_num: int, lang: str) -> str:
        """Save translated content to file.

        Args:
            content: Translated content
            episode_num: Episode number
            lang: Language code

        Returns:
            Path to saved translation file
        """
        try:
            # Create translation file path
            translation_path = f"../Banterblogs/banterblogs-nextjs/posts_i18n/{lang}/ep-{episode_num:03d}.md"

            # Ensure directory exists
            Path(translation_path).parent.mkdir(parents=True, exist_ok=True)

            # Write translated content
            with open(translation_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Saved {lang} translation to {translation_path}")
            return translation_path

        except Exception as e:
            logger.error(f"Failed to save translation: {e}")
            return ""

    def record_translation(self, episode_num: int, lang: str, translation_path: str,
                           original_data: Dict[str, Any]) -> bool:
        """Record translation in ClickHouse.

        Args:
            episode_num: Episode number
            lang: Language code
            translation_path: Path to translation file
            original_data: Original episode data

        Returns:
            True if successful
        """
        try:
            translation_data = {
                "ts": datetime.now(),
                "episode": episode_num,
                "run_id": str(uuid.uuid4()),
                "hearts_commit": original_data["hearts_commit"],
                "packs_commit": original_data["packs_commit"],
                "lang": lang,
                "path": translation_path,
                "confidence_score": original_data["confidence_score"],
                "tokens_total": original_data.get("tokens_total", 0),
                "cost_total": original_data.get("cost_total", 0.0),
                "correlation_strength": original_data["correlation_strength"],
                "status": "translated"
            }

            self.clickhouse.insert_episode(translation_data)
            logger.info(f"Recorded {lang} translation for episode {episode_num}")
            return True

        except Exception as e:
            logger.error(f"Failed to record translation: {e}")
            return False

    def translate_episode(self, episode_data: Dict[str, Any], languages: List[str]) -> Dict[str, Any]:
        """Translate an episode to multiple languages.

        Args:
            episode_data: Episode data
            languages: List of languages to translate to

        Returns:
            Translation results
        """
        episode_num = episode_data["episode"]
        episode_path = episode_data["path"]

        logger.info(f"Translating episode {episode_num} to {languages}")

        try:
            # Read original content
            original_content = self.read_episode_content(episode_path)
            if not original_content:
                return {
                    "status": "error",
                    "reason": "content_read_failed",
                    "episode_num": episode_num,
                    "translations": {}
                }

            # Check existing translations
            existing_translations = self.check_existing_translations(episode_num)

            translations = {}
            successful = 0
            failed = 0

            for lang in languages:
                if existing_translations.get(lang, False):
                    logger.info(f"Translation to {lang} already exists, skipping")
                    translations[lang] = {"status": "skipped", "reason": "already_exists"}
                    continue

                try:
                    # Translate content
                    translated_content = self.translate_content(original_content, lang)

                    # Save translation
                    translation_path = self.save_translation(translated_content, episode_num, lang)

                    if translation_path:
                        # Record translation
                        self.record_translation(episode_num, lang, translation_path, episode_data)

                        translations[lang] = {
                            "status": "success",
                            "path": translation_path
                        }
                        successful += 1

                        # Emit Datadog metrics
                        self.datadog.increment("i18n.translation", tags=[f"lang:{lang}"])

                    else:
                        translations[lang] = {
                            "status": "error",
                            "reason": "save_failed"
                        }
                        failed += 1

                except Exception as e:
                    logger.error(f"Failed to translate episode {episode_num} to {lang}: {e}")
                    translations[lang] = {
                        "status": "error",
                        "reason": str(e)
                    }
                    failed += 1

            result = {
                "status": "completed",
                "episode_num": episode_num,
                "translations": translations,
                "successful": successful,
                "failed": failed
            }

            logger.info(f"Episode {episode_num} translation completed: {successful}/{len(languages)} successful")
            return result

        except Exception as e:
            logger.error(f"Failed to translate episode {episode_num}: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "episode_num": episode_num,
                "translations": {}
            }

    def run_translation(self, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run complete translation process.

        Args:
            languages: List of languages to translate to

        Returns:
            Translation results
        """
        start_time = datetime.now()

        if languages is None:
            languages = self.supported_languages

        logger.info(f"Starting i18n translation for languages: {languages}")

        try:
            # Get episodes to translate
            episodes = self.get_episodes_to_translate()

            if not episodes:
                logger.warning("No episodes found to translate")
                return {
                    "status": "no_episodes",
                    "episodes_processed": 0,
                    "translations_successful": 0,
                    "translations_failed": 0,
                    "duration_seconds": 0
                }

            # Process each episode
            total_successful = 0
            total_failed = 0
            episode_results = []

            for episode_data in episodes:
                result = self.translate_episode(episode_data, languages)
                episode_results.append(result)

                total_successful += result.get("successful", 0)
                total_failed += result.get("failed", 0)

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "status": "completed",
                "episodes_processed": len(episodes),
                "translations_successful": total_successful,
                "translations_failed": total_failed,
                "duration_seconds": duration,
                "episode_results": episode_results
            }

            # Emit summary metrics
            self.datadog.increment("i18n.completed", tags=[f"langs:{len(languages)}"])
            self.datadog.gauge("i18n.episodes_processed", len(episodes))
            self.datadog.gauge("i18n.duration_seconds", duration)

            logger.info(f"Translation completed: {total_successful}/{total_successful + total_failed} translations successful")
            return result

        except Exception as e:
            logger.error(f"Translation process failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "episodes_processed": 0,
                "translations_successful": 0,
                "translations_failed": 0,
                "duration_seconds": 0
            }


def run_i18n_translator():
    """Run i18n Translator as standalone script."""
    import sys
    from apps.config import load_config

    # Load configuration
    config = load_config()

    # Initialize clients
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

    # Run Translator
    translator = I18nTranslator(clickhouse, datadog)

    # Check for languages argument
    if len(sys.argv) > 1:
        languages = sys.argv[1].split(',')
    else:
        languages = None

    result = translator.run_translation(languages)

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "completed" else 1)


if __name__ == "__main__":
    run_i18n_translator()
