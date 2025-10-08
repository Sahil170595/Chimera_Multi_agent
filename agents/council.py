"""Council Agent - The intelligence layer that generates episodes with confidence scoring."""

import logging
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple
from pathlib import Path
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient

logger = logging.getLogger(__name__)


class CouncilAgent:
    """Council Agent - Generates episodes with confidence scoring and\n    correlation analysis."""

    def __init__(self, clickhouse_client: ClickHouseClient, datadog_client: DatadogClient):
        """Initialize Council Agent.

        Args:
            clickhouse_client: ClickHouse client instance
            datadog_client: Datadog client instance
        """
        self.clickhouse = clickhouse_client
        self.datadog = datadog_client
        # Use same temp directory logic as watcher
        tmp_dir = Path(os.getenv('TEMP', '/tmp'))
        self.status_file = tmp_dir / "watcher_ok"

    def check_watcher_status(self) -> bool:
        """Check if watcher status is OK.

        Returns:
            True if watcher is OK
        """
        try:
            if not self.status_file.exists():
                logger.warning("Watcher status file not found - blocking Council")
                return False

            # Check if status file is recent (within 30 minutes)
            status_time = datetime.fromisoformat(self.status_file.read_text().strip())
            age_minutes = (datetime.now() - status_time).total_seconds() / 60

            if age_minutes > 30:
                logger.warning(f"Watcher status file is {age_minutes:.1f} minutes old - blocking Council")
                return False

            logger.info("Watcher status OK - proceeding with Council")
            return True

        except Exception as e:
            logger.error(f"Failed to check watcher status: {e}")
            return False

    def get_latest_commits(self) -> Tuple[str, str]:
        """Get latest commits from both repositories.

        Returns:
            Tuple of (hearts_commit, packs_commit)
        """
        try:
            import subprocess

            # Get Banterhearts latest commit
            hearts_result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                cwd="../Banterhearts",
                capture_output=True,
                text=True
            )
            hearts_commit = hearts_result.stdout.strip()

            # Get Banterpacks latest commit
            packs_result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                cwd="../Banterpacks",
                capture_output=True,
                text=True
            )
            packs_commit = packs_result.stdout.strip()

            logger.info(f"Latest commits - Hearts: {hearts_commit[:8]}, Packs: {packs_commit[:8]}")
            return hearts_commit, packs_commit

        except Exception as e:
            logger.error(f"Failed to get latest commits: {e}")
            return "", ""

    def get_correlation_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get correlation data for episode generation.

        Args:
            days: Number of days to look back

        Returns:
            List of correlation data points
        """
        try:
            correlation_data = self.clickhouse.get_correlation_data(days)

            if not correlation_data:
                logger.warning("No correlation data found")
                return []

            logger.info(f"Retrieved {len(correlation_data)} correlation data points")
            return correlation_data

        except Exception as e:
            logger.error(f"Failed to get correlation data: {e}")
            return []

    def calculate_confidence_score(self, correlation_data: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate confidence score based on correlation data.

        Args:
            correlation_data: Correlation data points

        Returns:
            Tuple of (confidence_score, correlation_strength)
        """
        try:
            if not correlation_data:
                return 0.0, 0.0

            # Calculate data completeness
            total_expected_days = 7
            actual_days = len(correlation_data)
            completeness = min(1.0, actual_days / total_expected_days)

            # Calculate correlation strength
            correlations = [abs(point.get("correlation", 0)) for point in correlation_data if point.get("correlation") is not None]
            correlation_strength = sum(correlations) / len(correlations) if correlations else 0.0

            # Calculate recency (more recent data = higher score)
            most_recent = max(point["day"] for point in correlation_data)
            days_old = (datetime.now().date() - most_recent).days
            recency = max(0.5, 1.0 - (days_old / 7.0))  # Decay to 0.5 at 7 days

            # Calculate data quality (more rows = better quality)
            total_hearts_rows = sum(point.get("hearts_rows", 0) for point in correlation_data)
            total_packs_rows = sum(point.get("packs_rows", 0) for point in correlation_data)
            expected_rows = total_expected_days * 10  # Expected 10 rows per day
            data_quality = min(1.0, (total_hearts_rows + total_packs_rows) / expected_rows)

            # Final confidence score
            confidence_score = min(completeness, correlation_strength, recency, data_quality)

            logger.info(
                f"Confidence calculation: completeness={completeness:.2f}, "
                f"correlation={correlation_strength:.2f}, recency={recency:.2f}, "
                f"quality={data_quality:.2f} -> final={confidence_score:.2f}"
            )

            return confidence_score, correlation_strength

        except Exception as e:
            logger.error(f"Failed to calculate confidence score: {e}")
            return 0.0, 0.0

    def determine_series(self, confidence_score: float, correlation_strength: float) -> str:
        """Determine which series the episode belongs to.

        Args:
            confidence_score: Episode confidence score
            correlation_strength: Correlation strength between hearts and packs

        Returns:
            Series name ('chimera' or 'banterpacks')
        """
        # High confidence + strong correlation = Chimera episode
        if confidence_score >= 0.7 and correlation_strength >= 0.6:
            return "chimera"
        else:
            return "banterpacks"

    def generate_episode_content(
        self,
        correlation_data: List[Dict[str, Any]],
        confidence_score: float,
        correlation_strength: float,
        hearts_commit: str,
        packs_commit: str,
    ) -> str:
        """Generate episode content based on correlation data.

        Args:
            correlation_data: Correlation data points
            confidence_score: Episode confidence score
            correlation_strength: Correlation strength
            hearts_commit: Banterhearts commit SHA
            packs_commit: Banterpacks commit SHA

        Returns:
            Generated episode content
        """
        try:
            # Determine series
            series = self.determine_series(confidence_score, correlation_strength)

            # Get episode number
            episode_num = self.clickhouse.get_next_episode_number(series)

            # Generate title based on confidence and correlation
            if confidence_score >= 0.8:
                title = f"Episode {episode_num:03d}: High-Confidence Performance Insights"
            elif confidence_score >= 0.6:
                title = f"Episode {episode_num:03d}: Moderate-Confidence Analysis"
            else:
                title = f"Episode {episode_num:03d}: Preliminary Data Review"

            # Generate content sections
            content = f"""# {title}

## commit-message
*AI-Generated Analysis of Banterhearts and Banterpacks Correlation*

### 📅 Date and Time
{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

### 🔗 Commits: `{hearts_commit[:8]}` (Hearts) | `{packs_commit[:8]}` (Packs)

### 📊 Episode {episode_num} of the Banterpacks Development Saga

---

## What changed

This week's analysis reveals significant developments across both Banterhearts and 
Banterpacks ecosystems. The correlation analysis shows {'strong' if correlation_strength >= 0.6 else 'moderate' if correlation_strength >= 0.3 else 'weak'} correlation between performance optimizations and user experience metrics.

Key developments include:
- Banterhearts performance optimizations with measurable impact
- Banterpacks user interaction patterns showing {'improved' if correlation_strength >= 0.5 else 'stable'} responsiveness
- Cross-system correlation strength of {correlation_strength:.2f}

## Why it matters

The correlation between Banterhearts performance improvements and\n    Banterpacks user experience metrics {'validates' if correlation_strength >= 0.6 else 'suggests' if correlation_strength >= 0.3 else 'requires further investigation of'} our optimization strategies.

{'Strong correlation indicates that performance improvements directly translate to better user experience.' if correlation_strength >= 0.6 else 'Moderate correlation suggests some impact but requires continued monitoring.' if correlation_strength >= 0.3 else 'Weak correlation indicates potential disconnect between optimizations and user experience.'}

## Benchmarks (summary)

**Data Quality Metrics:**
- Confidence Score: {confidence_score:.2f} ({'High' if confidence_score >= 0.7 else 'Moderate' if confidence_score >= 0.5 else 'Low'} confidence)
- Correlation Strength: {correlation_strength:.2f} ({'Strong' if correlation_strength >= 0.6 else 'Moderate' if correlation_strength >= 0.3 else 'Weak'} correlation)
- Data Points Analyzed: {len(correlation_data)} days

**Performance Insights:**
"""

            # Add specific metrics if we have correlation data
            if correlation_data:
                latest_data = correlation_data[0]  # Most recent data point
                content += f"""- Latest Hearts Latency: {latest_data.get('hearts_avg_lat', 0):.1f}ms
- Latest Hearts Cost: ${latest_data.get('hearts_avg_cost', 0):.4f}/1k tokens
- Latest Packs User Latency: {latest_data.get('packs_user_lat', 0):.1f}ms
- Latest Packs Error Rate: {latest_data.get('packs_err_rate', 0):.2%}
- Latest Packs Abandonment Rate: {latest_data.get('packs_abandon', 0):.2%}
"""
            else:
                content += "- No recent correlation data available\n"

            # Add confidence-based disclaimer
            if confidence_score < 0.6:
                content += f"""
## Data Quality Notice

⚠️ **Low Confidence Episode** (Score: {confidence_score:.2f})

This episode is based on limited or incomplete data. The analysis should be considered preliminary and may not reflect the full picture of system performance. Additional data collection is recommended before making significant decisions based on these findings.
"""

            content += f"""
## Next steps

Based on the correlation analysis:

1. {'Continue monitoring' if confidence_score >= 0.7 else 'Increase data collection'} to {'maintain' if confidence_score >= 0.7 else 'improve'} confidence levels
2. {'Scale successful optimizations' if correlation_strength >= 0.6 else 'Investigate correlation gaps'} across both systems
3. {'Maintain current performance targets' if correlation_strength >= 0.5 else 'Reassess performance targets'} based on user experience metrics
4. {'Expand monitoring coverage' if confidence_score < 0.7 else 'Optimize existing metrics'} for better data quality

## Links & artifacts

- [Banterhearts Commit](https://github.com/Sahil170595/Banterhearts/commit/{hearts_commit})
- [Banterpacks Commit](https://github.com/Sahil170595/Banterpacks/commit/{packs_commit})
- [Correlation Analysis](reports/correlation_analysis_{episode_num:03d}.json)
- [Performance Dashboard](https://monitoring.banterpacks.ai)
- [Data Quality Report](reports/data_quality_{episode_num:03d}.md)
"""

            return content

        except Exception as e:
            logger.error(f"Failed to generate episode content: {e}")
            return f"# Episode Generation Error\n\nFailed to generate episode content: {e}"

    def save_episode(self, content: str, series: str, episode_num: int) -> str:
        """Save episode to file.

        Args:
            content: Episode content
            series: Series name
            episode_num: Episode number

        Returns:
            Path to saved episode file
        """
        try:
            # Create episode file path
            episode_path = f"../Banterblogs/banterblogs-nextjs/posts/{series}/ep-{episode_num:03d}.md"

            # Ensure directory exists
            Path(episode_path).parent.mkdir(parents=True, exist_ok=True)

            # Write episode content
            with open(episode_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Saved episode to {episode_path}")
            return episode_path

        except Exception as e:
            logger.error(f"Failed to save episode: {e}")
            return ""

    def generate_episode(self) -> Dict[str, Any]:
        """Generate a new episode.

        Returns:
            Episode generation results
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Starting Council episode generation: {run_id}")

        try:
            # Check watcher status
            if not self.check_watcher_status():
                return {
                    "status": "blocked",
                    "reason": "watcher_not_ok",
                    "run_id": run_id,
                    "episode_num": 0,
                    "confidence_score": 0.0,
                    "correlation_strength": 0.0
                }

            # Get latest commits
            hearts_commit, packs_commit = self.get_latest_commits()
            if not hearts_commit or not packs_commit:
                return {
                    "status": "error",
                    "reason": "no_commits",
                    "run_id": run_id,
                    "episode_num": 0,
                    "confidence_score": 0.0,
                    "correlation_strength": 0.0
                }

            # Get correlation data
            correlation_data = self.get_correlation_data()

            # Calculate confidence score
            confidence_score, correlation_strength = self.calculate_confidence_score(correlation_data)

            # Determine series
            series = self.determine_series(confidence_score, correlation_strength)

            # Get episode number
            episode_num = self.clickhouse.get_next_episode_number(series)

            # Generate episode content
            content = self.generate_episode_content(
                correlation_data, confidence_score, correlation_strength,
                hearts_commit, packs_commit
            )

            # Save episode
            episode_path = self.save_episode(content, series, episode_num)
            if not episode_path:
                return {
                    "status": "error",
                    "reason": "save_failed",
                    "run_id": run_id,
                    "episode_num": episode_num,
                    "confidence_score": confidence_score,
                    "correlation_strength": correlation_strength
                }

            # Determine episode status
            if confidence_score >= 0.6:
                episode_status = "published"
            else:
                episode_status = "draft"

            # Calculate tokens and cost (mock)
            tokens_total = len(content.split()) * 1.3  # Rough token estimate
            cost_total = tokens_total * 0.00003  # Mock cost per token

            # Insert episode record
            episode_data = {
                "ts": start_time,
                "episode": episode_num,
                "run_id": run_id,
                "hearts_commit": hearts_commit,
                "packs_commit": packs_commit,
                "lang": "en",
                "path": episode_path,
                "confidence_score": confidence_score,
                "tokens_total": int(tokens_total),
                "cost_total": cost_total,
                "correlation_strength": correlation_strength,
                "status": episode_status
            }

            self.clickhouse.insert_episode(episode_data)

            # Insert LLM event
            llm_event = {
                "ts": start_time,
                "run_id": run_id,
                "source": "council",
                "model": "council_agent",
                "operation": "episode_generation",
                "tokens_in": int(tokens_total * 0.3),
                "tokens_out": int(tokens_total * 0.7),
                "latency_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                "cost_usd": cost_total,
                "status": "success",
                "error_msg": ""
            }

            self.clickhouse.insert_llm_event(llm_event)

            # Emit Datadog metrics
            self.datadog.increment("episodes.generated", tags=[f"confidence_score:{confidence_score:.2f}"])
            self.datadog.gauge("episodes.correlation", correlation_strength)
            self.datadog.gauge("episodes.tokens_total", tokens_total)
            self.datadog.gauge("episodes.cost_total", cost_total)

            result = {
                "status": "success",
                "run_id": run_id,
                "episode_num": episode_num,
                "series": series,
                "episode_path": episode_path,
                "confidence_score": confidence_score,
                "correlation_strength": correlation_strength,
                "episode_status": episode_status,
                "hearts_commit": hearts_commit,
                "packs_commit": packs_commit,
                "tokens_total": int(tokens_total),
                "cost_total": cost_total
            }

            logger.info(f"Episode generation completed: {episode_num} ({series}) - confidence: {confidence_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Episode generation failed: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "run_id": run_id,
                "episode_num": 0,
                "confidence_score": 0.0,
                "correlation_strength": 0.0
            }


def run_council_agent():
    """Run Council Agent as standalone script."""
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

    # Run Council
    council = CouncilAgent(clickhouse, datadog)
    result = council.generate_episode()

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    run_council_agent()
