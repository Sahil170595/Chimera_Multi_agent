"""Benchmark generation utilities for Muse Protocol."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from schemas.benchmarks import (
    BenchmarkType,
    BenchmarkResult,
    create_benchmark_template,
    CompilationBenchmark, QuantizationBenchmark,
    KernelOptimizationBenchmark, AttentionBenchmark,
    PromptSuiteBenchmark, SystemPerformanceBenchmark,
    InferencePerformanceBenchmark
)


class BenchmarkGenerator:
    """Generate benchmark data for Muse Protocol episodes."""

    def __init__(self, reports_dir: Path = Path("reports")):
        """Initialize benchmark generator.

        Args:
            reports_dir: Directory to store benchmark reports
        """
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)

    def generate_compilation_benchmark(self, model_config: Dict[str, Any]) -> CompilationBenchmark:
        """Generate compilation benchmark data.

        Args:
            model_config: Model configuration

        Returns:
            Compilation benchmark data
        """
        template = create_benchmark_template(BenchmarkType.COMPILATION)
        template["model"].update(model_config)

        # Generate realistic performance data
        backends = template["settings"]["backends"]
        backend_results = {}

        for backend in backends:
            backend_results[backend] = {
                "backend": backend,
                "compilation": {
                    "backend": backend,
                    "success": True,
                    "compile_time_s": self._generate_compile_time(backend),
                    "metadata": self._generate_backend_metadata(backend),
                    "error": None
                },
                "benchmark": {
                    "backend": backend,
                    "mean_time_ms": self._generate_inference_time(backend),
                    "std_time_ms": self._generate_std_time(),
                    "min_time_ms": self._generate_min_time(),
                    "max_time_ms": self._generate_max_time(),
                    "metadata": {
                        "compile_time_s": self._generate_compile_time(backend)
                    }
                }
            }

        template["backends"] = backend_results

        # Create proper metadata object
        from schemas.benchmarks import BenchmarkMetadata
        metadata = BenchmarkMetadata(
            generated_at=template["generated_at"],
            benchmark_type=BenchmarkType.COMPILATION,
            version=template["version"],
            environment=template["environment"],
            tags=template["tags"]
        )

        template["metadata"] = metadata

        return CompilationBenchmark(**template)

    def generate_quantization_benchmark(self, model_config: Dict[str, Any]) -> QuantizationBenchmark:
        """Generate quantization benchmark data.

        Args:
            model_config: Model configuration

        Returns:
            Quantization benchmark data
        """
        template = create_benchmark_template(BenchmarkType.QUANTIZATION)
        template["model"].update(model_config)

        # Generate quantization results
        methods = ["baseline", "int8", "fp8", "qat"]
        quantization_results = {}

        baseline_accuracy = 0.75
        baseline_loss = 0.608
        baseline_size = 2781

        for method in methods:
            if method == "baseline":
                quantization_results[method] = {
                    "accuracy": baseline_accuracy,
                    "loss": baseline_loss,
                    "model_size_bytes": baseline_size
                }
            elif method == "int8":
                quantization_results[method] = {
                    "accuracy": baseline_accuracy * 0.98,  # Slight accuracy drop
                    "loss": baseline_loss * 1.02,
                    "model_size_bytes": int(baseline_size * 0.75)  # 25% size reduction
                }
            elif method == "fp8":
                quantization_results[method] = {
                    "accuracy": baseline_accuracy,
                    "loss": baseline_loss,
                    "model_size_bytes": baseline_size
                }
            elif method == "qat":
                quantization_results[method] = {
                    "accuracy": baseline_accuracy * 0.5,  # Training in progress
                    "loss": baseline_loss * 1.7,
                    "model_size_bytes": int(baseline_size * 1.2)  # Temporary size increase
                }

        template["quantization_methods"] = quantization_results

        return QuantizationBenchmark(**template)

    def generate_kernel_optimization_benchmark(self) -> KernelOptimizationBenchmark:
        """Generate kernel optimization benchmark data.

        Returns:
            Kernel optimization benchmark data
        """
        template = create_benchmark_template(BenchmarkType.KERNEL_OPTIMIZATION)

        # Generate kernel performance data
        kernels = {
            "attention": {
                "torch": {
                    "mean_time_ms": 24.6,
                    "std_time_ms": 73.2,
                    "min_time_ms": 0.17,
                    "max_time_ms": 244.1
                },
                "flash_attention": {
                    "mean_time_ms": 12.3,
                    "std_time_ms": 36.6,
                    "min_time_ms": 0.08,
                    "max_time_ms": 122.0
                }
            },
            "tensor_core": {
                "512x512x512": {
                    "mean_time_ms": 16.7,
                    "std_time_ms": 50.0,
                    "min_time_ms": 0.03,
                    "max_time_ms": 166.6
                },
                "1024x1024x1024": {
                    "mean_time_ms": 65.2,
                    "std_time_ms": 195.5,
                    "min_time_ms": 0.12,
                    "max_time_ms": 650.8
                }
            },
            "fusion": {
                "baseline_linear_gelu": {
                    "mean_time_ms": 0.76,
                    "std_time_ms": 2.05,
                    "min_time_ms": 0.04,
                    "max_time_ms": 6.92
                },
                "fused_linear_gelu": {
                    "mean_time_ms": 0.05,
                    "std_time_ms": 0.01,
                    "min_time_ms": 0.04,
                    "max_time_ms": 0.07
                }
            }
        }

        template["kernels"] = kernels

        return KernelOptimizationBenchmark(**template)

    def generate_attention_benchmark(self, model_config: Dict[str, Any]) -> AttentionBenchmark:
        """Generate attention mechanism benchmark data.

        Args:
            model_config: Model configuration

        Returns:
            Attention benchmark data
        """
        template = create_benchmark_template(BenchmarkType.ATTENTION_MECHANISM)
        template["model"].update(model_config)

        # Generate attention performance results
        mechanisms = ["mqa", "gqa", "sliding_window", "sparse"]
        performance_results = {}
        cross_comparison = {}

        baseline_time = 25.0  # Baseline attention time

        for mechanism in mechanisms:
            if mechanism == "mqa":
                time_ms = baseline_time * 0.6  # 40% faster
            elif mechanism == "gqa":
                time_ms = baseline_time * 0.7  # 30% faster
            elif mechanism == "sliding_window":
                time_ms = baseline_time * 0.8  # 20% faster
            elif mechanism == "sparse":
                time_ms = baseline_time * 0.5  # 50% faster

            performance_results[mechanism] = {
                "mean_time_ms": time_ms,
                "std_time_ms": time_ms * 0.1,
                "min_time_ms": time_ms * 0.8,
                "max_time_ms": time_ms * 1.2,
                "throughput_tokens_per_sec": 1000 / time_ms,
                "memory_used_mb": 500.0
            }

            cross_comparison[mechanism] = {
                "speedup_vs_mqa": baseline_time / time_ms,
                "memory_efficiency": 0.8 + (mechanism == "sparse") * 0.2
            }

        template["performance_results"] = performance_results
        template["cross_comparison"] = cross_comparison

        return AttentionBenchmark(**template)

    def generate_prompt_suite_benchmark(self, prompts: List[str], models: List[str]) -> PromptSuiteBenchmark:
        """Generate prompt suite benchmark data.

        Args:
            prompts: List of test prompts
            models: List of model names

        Returns:
            Prompt suite benchmark data
        """
        template = create_benchmark_template(BenchmarkType.PROMPT_SUITE)
        template["prompts"] = prompts
        template["prompt_count"] = len(prompts)

        # Generate model configurations
        model_configs = []
        for model in models:
            model_configs.append({
                "model": model,
                "prompt_count": len(prompts),
                "completed": len(prompts),  # All completed
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            })

        template["models"] = model_configs

        # Generate results
        results = {}
        for model in models:
            results[model] = {
                "total_time_ms": self._generate_total_time(),
                "average_time_ms": self._generate_average_time(),
                "tokens_generated": self._generate_token_count(),
                "success_rate": 1.0
            }

        template["results"] = results

        return PromptSuiteBenchmark(**template)

    def generate_system_performance_benchmark(self, duration_minutes: float = 1.0) -> SystemPerformanceBenchmark:
        """Generate system performance benchmark data.

        Args:
            duration_minutes: Duration of the benchmark

        Returns:
            System performance benchmark data
        """
        template = create_benchmark_template(BenchmarkType.SYSTEM_PERFORMANCE)
        template["duration_minutes"] = duration_minutes

        # Generate realistic system metrics
        template["system_metrics"] = {
            "cpu_avg_percent": 45.2,
            "cpu_peak_percent": 78.5,
            "memory_avg_percent": 62.1,
            "memory_peak_percent": 85.3,
            "gpu_temperature_avg_c": 65.2,
            "gpu_temperature_peak_c": 78.9,
            "gpu_power_avg_w": 180.5,
            "gpu_power_peak_w": 220.1,
            "gpu_utilization_avg_percent": 75.3,
            "gpu_utilization_peak_percent": 95.2
        }

        return SystemPerformanceBenchmark(**template)

    def generate_inference_performance_benchmark(self, model_config: Dict[str, Any]) -> InferencePerformanceBenchmark:
        """Generate inference performance benchmark data.

        Args:
            model_config: Model configuration

        Returns:
            Inference performance benchmark data
        """
        template = create_benchmark_template(BenchmarkType.INFERENCE_PERFORMANCE)
        template["model"].update(model_config)

        # Generate test scenarios
        scenarios = [
            {
                "context": "player_died",
                "tone": "encouraging",
                "game_type": "rpg",
                "player_level": 25
            },
            {
                "context": "boss_defeated",
                "tone": "celebratory",
                "game_type": "action",
                "player_level": 50
            },
            {
                "context": "rare_item_drop",
                "tone": "excited",
                "game_type": "mmo",
                "player_level": 75
            }
        ]

        template["test_scenarios"] = scenarios

        # Generate performance data
        generation_times = [2500.0, 2400.0, 2600.0, 2550.0, 2450.0]
        total_tokens = sum([800, 750, 850, 820, 780])  # Tokens per scenario

        template["generation_times"] = generation_times
        template["total_tokens"] = total_tokens

        avg_time = sum(generation_times) / len(generation_times)
        tokens_per_second = total_tokens / (sum(generation_times) / 1000)

        template["performance_summary"] = {
            "average_time_ms": avg_time,
            "min_time_ms": min(generation_times),
            "max_time_ms": max(generation_times),
            "tokens_per_second": tokens_per_second,
            "total_scenarios": len(scenarios)
        }

        return InferencePerformanceBenchmark(**template)

    def save_benchmark(self, benchmark: BenchmarkResult, filename: Optional[str] = None) -> Path:
        """Save benchmark to file.

        Args:
            benchmark: Benchmark data to save
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            benchmark_type = benchmark.metadata.benchmark_type.value
            filename = f"{benchmark_type}_benchmark_{timestamp}.json"

        file_path = self.reports_dir / filename

        with open(file_path, 'w') as f:
            json.dump(benchmark.dict(), f, indent=2, default=str)

        return file_path

    def _generate_compile_time(self, backend: str) -> float:
        """Generate realistic compile time based on backend."""
        compile_times = {
            "eager": 0.0,
            "jit": 0.175,
            "torch_compile": 0.898,
            "onnx": 0.313,
            "torch_trt": 2.5,
            "triton": 1.2
        }
        return compile_times.get(backend, 0.5)

    def _generate_inference_time(self, backend: str) -> float:
        """Generate realistic inference time based on backend."""
        inference_times = {
            "eager": 24.7,
            "jit": 4.9,
            "torch_compile": 5.7,
            "onnx": 2.8,
            "torch_trt": 1.5,
            "triton": 3.2
        }
        return inference_times.get(backend, 10.0)

    def _generate_std_time(self) -> float:
        """Generate standard deviation time."""
        return 2.2

    def _generate_min_time(self) -> float:
        """Generate minimum time."""
        return 21.7

    def _generate_max_time(self) -> float:
        """Generate maximum time."""
        return 30.2

    def _generate_backend_metadata(self, backend: str) -> Dict[str, Any]:
        """Generate backend-specific metadata."""
        metadata = {
            "eager": {},
            "jit": {"strict": False, "frozen": True},
            "torch_compile": {"backend": "inductor", "mode": "default"},
            "onnx": {"opset": 17, "providers": ["CPUExecutionProvider"]},
            "torch_trt": {"precision": "fp16", "workspace_size": 1024},
            "triton": {"num_warps": 4, "num_stages": 2}
        }
        return metadata.get(backend, {})

    def _generate_total_time(self) -> float:
        """Generate total execution time."""
        return 12500.0

    def _generate_average_time(self) -> float:
        """Generate average execution time."""
        return 2500.0

    def _generate_token_count(self) -> int:
        """Generate token count."""
        return 1500


def generate_episode_benchmarks(episode_metadata: Dict[str, Any]) -> Dict[str, BenchmarkResult]:
    """Generate comprehensive benchmarks for an episode.

    Args:
        episode_metadata: Episode metadata

    Returns:
        Dictionary of benchmark results
    """
    generator = BenchmarkGenerator()

    # Extract model info from episode metadata
    model_config = {
        "name": episode_metadata.get("models", ["gpt-4"])[0],
        "device": "cpu",
        "dtype": "torch.float32",
        "batch_size": 1,
        "seq_len": 512
    }

    benchmarks = {}

    # Generate different types of benchmarks
    benchmarks["compilation"] = generator.generate_compilation_benchmark(model_config)
    benchmarks["quantization"] = generator.generate_quantization_benchmark(model_config)
    benchmarks["kernel_optimization"] = generator.generate_kernel_optimization_benchmark()
    benchmarks["attention"] = generator.generate_attention_benchmark(model_config)
    benchmarks["system_performance"] = generator.generate_system_performance_benchmark()
    benchmarks["inference_performance"] = generator.generate_inference_performance_benchmark(model_config)

    # Generate prompt suite if we have prompts
    prompts = [
        "Generate encouraging banter for a player who failed a mission",
        "Create celebratory text for defeating a boss",
        "Write excited commentary for finding rare loot"
    ]
    models = episode_metadata.get("models", ["gpt-4"])
    benchmarks["prompt_suite"] = generator.generate_prompt_suite_benchmark(prompts, models)

    return benchmarks
