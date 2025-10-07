"""Banterhearts Ingestor Agent - Ingests benchmark data from Banterhearts."""

import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
from integrations.clickhouse_client import ClickHouseClient
from integrations.datadog import DatadogClient

logger = logging.getLogger(__name__)


class BanterheartsIngestor:
    """Banterhearts Ingestor - Reads benchmark reports and ingests to ClickHouse."""

    def __init__(self, clickhouse_client: ClickHouseClient, datadog_client: DatadogClient):
        """Initialize Banterhearts Ingestor.

        Args:
            clickhouse_client: ClickHouse client instance
            datadog_client: Datadog client instance
        """
        self.clickhouse = clickhouse_client
        self.datadog = datadog_client
        self.reports_dir = Path("../Banterhearts/reports")

    def get_latest_commit(self) -> str:
        """Get latest commit SHA from Banterhearts.

        Returns:
            Latest commit SHA
        """
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                cwd="../Banterhearts",
                capture_output=True,
                text=True
            )
            commit_sha = result.stdout.strip()
            logger.info(f"Latest Banterhearts commit: {commit_sha[:8]}")
            return commit_sha

        except Exception as e:
            logger.error(f"Failed to get latest commit: {e}")
            return ""

    def find_benchmark_files(self, run_id: Optional[str] = None) -> List[Path]:
        """Find benchmark files to ingest.

        Args:
            run_id: Specific run ID to look for

        Returns:
            List of benchmark file paths
        """
        try:
            benchmark_files = []

            if run_id:
                # Look for specific run ID
                pattern = f"*{run_id}*.json"
                files = list(self.reports_dir.glob(pattern))
                benchmark_files.extend(files)
            else:
                # Find all recent benchmark files
                for subdir in ["compilation", "quantization", "kernel_optimization", "attention_mechanism", "system_performance", "inference_performance"]:
                    subdir_path = self.reports_dir / subdir
                    if subdir_path.exists():
                        files = list(subdir_path.glob("*.json"))
                        # Get files from last 24 hours
                        recent_files = [f for f in files if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() < 86400]
                        benchmark_files.extend(recent_files)

            logger.info(f"Found {len(benchmark_files)} benchmark files to ingest")
            return benchmark_files

        except Exception as e:
            logger.error(f"Failed to find benchmark files: {e}")
            return []

    def parse_benchmark_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse benchmark file and extract data.

        Args:
            file_path: Path to benchmark file

        Returns:
            Parsed benchmark data
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Extract common fields
            benchmark_type = data.get("benchmark_type", "unknown")

            # Parse based on benchmark type
            if benchmark_type == "compilation":
                return self._parse_compilation_benchmark(data, file_path)
            elif benchmark_type == "quantization":
                return self._parse_quantization_benchmark(data, file_path)
            elif benchmark_type == "kernel_optimization":
                return self._parse_kernel_benchmark(data, file_path)
            elif benchmark_type == "attention_mechanism":
                return self._parse_attention_benchmark(data, file_path)
            elif benchmark_type == "system_performance":
                return self._parse_system_benchmark(data, file_path)
            elif benchmark_type == "inference_performance":
                return self._parse_inference_benchmark(data, file_path)
            else:
                logger.warning(f"Unknown benchmark type: {benchmark_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to parse benchmark file {file_path}: {e}")
            return None

    def _parse_compilation_benchmark(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse compilation benchmark data."""
        model_config = data.get("model", {})

        # Extract performance data from fastest backend
        backends = data.get("backends", {})
        fastest_backend = min(backends.items(), key=lambda x: x[1]["benchmark"]["mean_time_ms"]) if backends else None

        if fastest_backend:
            backend_name, backend_data = fastest_backend
            benchmark_data = backend_data["benchmark"]

            return {
                "ts": datetime.now(),
                "run_id": str(uuid.uuid4()),
                "commit_sha": self.get_latest_commit(),
                "model": model_config.get("name", "unknown"),
                "quant": "none",
                "dataset": "synthetic",
                "latency_p50_ms": int(benchmark_data.get("mean_time_ms", 0)),
                "latency_p95_ms": int(benchmark_data.get("mean_time_ms", 0) * 1.2),
                "latency_p99_ms": int(benchmark_data.get("mean_time_ms", 0) * 1.5),
                "tokens_per_sec": 1000 / benchmark_data.get("mean_time_ms", 1),
                "cost_per_1k": 0.001,  # Mock cost
                "memory_peak_mb": 500,  # Mock memory
                "schema_version": 1
            }

        return None

    def _parse_quantization_benchmark(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse quantization benchmark data."""
        model_config = data.get("model", {})
        quantization_methods = data.get("quantization_methods", {})

        # Use best quantization method
        best_method = max(quantization_methods.items(), key=lambda x: x[1]["accuracy"]) if quantization_methods else None

        if best_method:
            method_name, method_data = best_method

            return {
                "ts": datetime.now(),
                "run_id": str(uuid.uuid4()),
                "commit_sha": self.get_latest_commit(),
                "model": model_config.get("name", "unknown"),
                "quant": method_name,
                "dataset": "synthetic",
                "latency_p50_ms": 1000,  # Mock latency
                "latency_p95_ms": 1200,
                "latency_p99_ms": 1500,
                "tokens_per_sec": 1.0,
                "cost_per_1k": 0.0005,  # Mock cost
                "memory_peak_mb": method_data.get("model_size_bytes", 1000) // 1024,
                "schema_version": 1
            }

        return None

    def _parse_kernel_benchmark(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse kernel optimization benchmark data."""
        kernels = data.get("kernels", {})

        # Extract attention kernel performance
        attention_kernels = kernels.get("attention", {})
        if attention_kernels:
            # Use flash attention if available, otherwise torch
            if "flash_attention" in attention_kernels:
                kernel_data = attention_kernels["flash_attention"]
            else:
                kernel_data = list(attention_kernels.values())[0]

            return {
                "ts": datetime.now(),
                "run_id": str(uuid.uuid4()),
                "commit_sha": self.get_latest_commit(),
                "model": "kernel_optimized",
                "quant": "none",
                "dataset": "synthetic",
                "latency_p50_ms": int(kernel_data.get("mean_time_ms", 0)),
                "latency_p95_ms": int(kernel_data.get("mean_time_ms", 0) * 1.2),
                "latency_p99_ms": int(kernel_data.get("mean_time_ms", 0) * 1.5),
                "tokens_per_sec": 1000 / kernel_data.get("mean_time_ms", 1),
                "cost_per_1k": 0.0008,
                "memory_peak_mb": 400,
                "schema_version": 1
            }

        return None

    def _parse_attention_benchmark(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse attention mechanism benchmark data."""
        performance_results = data.get("performance_results", {})

        # Use fastest attention mechanism
        fastest_mechanism = min(performance_results.items(), key=lambda x: x[1]["mean_time_ms"]) if performance_results else None

        if fastest_mechanism:
            mechanism_name, mechanism_data = fastest_mechanism

            return {
                "ts": datetime.now(),
                "run_id": str(uuid.uuid4()),
                "commit_sha": self.get_latest_commit(),
                "model": f"attention_{mechanism_name}",
                "quant": "none",
                "dataset": "synthetic",
                "latency_p50_ms": int(mechanism_data.get("mean_time_ms", 0)),
                "latency_p95_ms": int(mechanism_data.get("mean_time_ms", 0) * 1.2),
                "latency_p99_ms": int(mechanism_data.get("mean_time_ms", 0) * 1.5),
                "tokens_per_sec": mechanism_data.get("throughput_tokens_per_sec", 0),
                "cost_per_1k": 0.0012,
                "memory_peak_mb": int(mechanism_data.get("memory_used_mb", 500)),
                "schema_version": 1
            }

        return None

    def _parse_system_benchmark(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse system performance benchmark data."""
        system_metrics = data.get("system_metrics", {})

        return {
            "ts": datetime.now(),
            "run_id": str(uuid.uuid4()),
            "commit_sha": self.get_latest_commit(),
            "model": "system_monitor",
            "quant": "none",
            "dataset": "synthetic",
            "latency_p50_ms": 100,  # Mock latency
            "latency_p95_ms": 120,
            "latency_p99_ms": 150,
            "tokens_per_sec": 10.0,
            "cost_per_1k": 0.0001,
            "memory_peak_mb": int(system_metrics.get("memory_peak_percent", 50) * 16),  # Mock memory
            "schema_version": 1
        }

    def _parse_inference_benchmark(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Parse inference performance benchmark data."""
        performance_summary = data.get("performance_summary", {})

        return {
            "ts": datetime.now(),
            "run_id": str(uuid.uuid4()),
            "commit_sha": self.get_latest_commit(),
            "model": "inference_test",
            "quant": "none",
            "dataset": "synthetic",
            "latency_p50_ms": int(performance_summary.get("average_time_ms", 0)),
            "latency_p95_ms": int(performance_summary.get("max_time_ms", 0)),
            "latency_p99_ms": int(performance_summary.get("max_time_ms", 0) * 1.2),
            "tokens_per_sec": performance_summary.get("tokens_per_second", 0),
            "cost_per_1k": 0.002,
            "memory_peak_mb": 800,
            "schema_version": 1
        }

    def ingest_benchmark_file(self, file_path: Path) -> bool:
        """Ingest a single benchmark file.

        Args:
            file_path: Path to benchmark file

        Returns:
            True if successful
        """
        try:
            # Parse benchmark data
            benchmark_data = self.parse_benchmark_file(file_path)
            if not benchmark_data:
                logger.warning(f"No data extracted from {file_path}")
                return False

            # Insert into ClickHouse
            success = self.clickhouse.insert_bench_run(benchmark_data)

            if success:
                # Also insert as LLM event
                llm_event = {
                    "ts": benchmark_data["ts"],
                    "run_id": benchmark_data["run_id"],
                    "source": "banterhearts",
                    "model": benchmark_data["model"],
                    "operation": "benchmark",
                    "tokens_in": 1000,  # Mock input tokens
                    "tokens_out": 500,  # Mock output tokens
                    "latency_ms": benchmark_data["latency_p50_ms"],
                    "cost_usd": benchmark_data["cost_per_1k"] * 0.001,
                    "status": "success",
                    "error_msg": ""
                }

                self.clickhouse.insert_llm_event(llm_event)

                # Emit Datadog metrics
                self.datadog.increment("ingest.banterhearts", tags=[f"commit_sha:{benchmark_data['commit_sha'][:8]}"])
                self.datadog.gauge("ingest.latency_ms", benchmark_data["latency_p50_ms"], tags=["source:banterhearts"])

                logger.info(f"Successfully ingested {file_path}")
                return True
            else:
                logger.error(f"Failed to insert benchmark data from {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to ingest benchmark file {file_path}: {e}")
            return False

    def run_ingestion(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Run complete ingestion process.

        Args:
            run_id: Specific run ID to ingest

        Returns:
            Ingestion results
        """
        start_time = datetime.now()
        logger.info(f"Starting Banterhearts ingestion: {run_id or 'all recent'}")

        try:
            # Find benchmark files
            benchmark_files = self.find_benchmark_files(run_id)

            if not benchmark_files:
                logger.warning("No benchmark files found to ingest")
                return {
                    "status": "no_files",
                    "files_processed": 0,
                    "files_successful": 0,
                    "files_failed": 0,
                    "duration_seconds": 0
                }

            # Process each file
            successful = 0
            failed = 0

            for file_path in benchmark_files:
                if self.ingest_benchmark_file(file_path):
                    successful += 1
                else:
                    failed += 1

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "status": "completed",
                "files_processed": len(benchmark_files),
                "files_successful": successful,
                "files_failed": failed,
                "duration_seconds": duration
            }

            # Emit summary metrics
            self.datadog.increment("ingest.banterhearts.completed", tags=["status:success"])
            self.datadog.gauge("ingest.banterhearts.files_processed", len(benchmark_files))
            self.datadog.gauge("ingest.banterhearts.duration_seconds", duration)

            logger.info(f"Ingestion completed: {successful}/{len(benchmark_files)} files successful")
            return result

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "files_processed": 0,
                "files_successful": 0,
                "files_failed": 0,
                "duration_seconds": 0
            }


def run_banterhearts_ingestor():
    """Run Banterhearts Ingestor as standalone script."""
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

    # Run ingestion
    ingestor = BanterheartsIngestor(clickhouse, datadog)

    # Check for run_id argument
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = ingestor.run_ingestion(run_id)

    # Print results
    print(json.dumps(result, indent=2, default=str))

    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "completed" else 1)


if __name__ == "__main__":
    run_banterhearts_ingestor()
