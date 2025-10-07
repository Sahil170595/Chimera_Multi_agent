"""Benchmark report generation for Muse Protocol episodes."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from schemas.benchmark_generator import generate_episode_benchmarks
from schemas.benchmarks import BenchmarkReport, BenchmarkMetadata, BenchmarkType


class BenchmarkReporter:
    """Generate comprehensive benchmark reports for episodes."""

    def __init__(self, reports_dir: Path = Path("reports")):
        """Initialize benchmark reporter.

        Args:
            reports_dir: Directory to store benchmark reports
        """
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)

    def generate_episode_benchmark_report(self, episode_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive benchmark report for an episode.

        Args:
            episode_metadata: Episode metadata

        Returns:
            Comprehensive benchmark report
        """
        # Generate all benchmark types
        benchmarks = generate_episode_benchmarks(episode_metadata)

        # Create report metadata
        metadata = BenchmarkMetadata(
            generated_at=datetime.now(),
            benchmark_type=BenchmarkType.SYSTEM_PERFORMANCE,  # Default type
            version="1.0",
            environment={
                "python_version": "3.9+",
                "pytorch_version": "2.0+",
                "device": "cpu",
                "episode_series": episode_metadata.get("series", "Unknown"),
                "episode_number": episode_metadata.get("episode", 0)
            },
            tags=["episode", "comprehensive", "performance"]
        )

        # Generate summary
        summary = self._generate_benchmark_summary(benchmarks, episode_metadata)

        # Generate recommendations
        recommendations = self._generate_recommendations(benchmarks, episode_metadata)

        # Create comprehensive report
        report = BenchmarkReport(
            metadata=metadata,
            benchmarks=list(benchmarks.values()),
            summary=summary,
            recommendations=recommendations
        )

        return report.dict()

    def save_episode_benchmark_report(self, episode_metadata: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save episode benchmark report to file.

        Args:
            episode_metadata: Episode metadata
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to saved file
        """
        report = self.generate_episode_benchmark_report(episode_metadata)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            series = episode_metadata.get("series", "unknown").lower()
            episode_num = episode_metadata.get("episode", 0)
            filename = f"{series}_episode_{episode_num:03d}_benchmarks_{timestamp}.json"

        file_path = self.reports_dir / filename

        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return file_path

    def generate_benchmark_summary_markdown(self, episode_metadata: Dict[str, Any]) -> str:
        """Generate markdown summary of benchmarks.

        Args:
            episode_metadata: Episode metadata

        Returns:
            Markdown formatted benchmark summary
        """
        benchmarks = generate_episode_benchmarks(episode_metadata)

        markdown = f"""# Benchmark Summary - {episode_metadata.get('title', 'Unknown Episode')}

**Series:** {episode_metadata.get('series', 'Unknown')}
**Episode:** {episode_metadata.get('episode', 0)}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Models:** {', '.join(episode_metadata.get('models', []))}

## Performance Overview

### Inference Performance
- **Average Generation Time:** {benchmarks['inference_performance'].performance_summary.get('average_time_ms', 0):.1f}ms
- **Tokens per Second:** {benchmarks['inference_performance'].performance_summary.get('tokens_per_second', 0):.2f}
- **Total Tokens Generated:** {benchmarks['inference_performance'].total_tokens:,}

### System Performance
- **CPU Utilization:** {benchmarks['system_performance'].system_metrics.cpu_avg_percent:.1f}% avg, {benchmarks['system_performance'].system_metrics.cpu_peak_percent:.1f}% peak
- **Memory Utilization:** {benchmarks['system_performance'].system_metrics.memory_avg_percent:.1f}% avg, {benchmarks['system_performance'].system_metrics.memory_peak_percent:.1f}% peak
"""

        if benchmarks['system_performance'].system_metrics.gpu_temperature_avg_c:
            markdown += f"""- **GPU Temperature:** {benchmarks['system_performance'].system_metrics.gpu_temperature_avg_c:.1f}°C avg, {benchmarks['system_performance'].system_metrics.gpu_temperature_peak_c:.1f}°C peak
- **GPU Power:** {benchmarks['system_performance'].system_metrics.gpu_power_avg_w:.1f}W avg, {benchmarks['system_performance'].system_metrics.gpu_power_peak_w:.1f}W peak
- **GPU Utilization:** {benchmarks['system_performance'].system_metrics.gpu_utilization_avg_percent:.1f}% avg, {benchmarks['system_performance'].system_metrics.gpu_utilization_peak_percent:.1f}% peak
"""

        markdown += """
## Compilation Benchmarks

| Backend | Compile Time (s) | Inference Time (ms) | Speedup |
|---------|------------------|---------------------|---------|
"""

        for backend_name, backend_data in benchmarks['compilation'].backends.items():
            compile_time = backend_data['compilation']['compile_time_s']
            inference_time = backend_data['benchmark']['mean_time_ms']
            speedup = benchmarks['compilation'].backends['eager']['benchmark']['mean_time_ms'] / inference_time
            markdown += f"| {backend_name} | {compile_time:.3f} | {inference_time:.1f} | {speedup:.2f}x |\n"

        markdown += """
## Quantization Results

| Method | Accuracy | Loss | Size (bytes) | Compression |
|--------|----------|------|--------------|-------------|
"""

        baseline_size = benchmarks['quantization'].quantization_methods['baseline']['model_size_bytes']
        for method, data in benchmarks['quantization'].quantization_methods.items():
            accuracy = data['accuracy']
            loss = data['loss']
            size = data['model_size_bytes']
            compression = (1 - size / baseline_size) * 100
            markdown += f"| {method.upper()} | {accuracy:.3f} | {loss:.3f} | {size:,} | {compression:.1f}% |\n"

        markdown += """
## Attention Mechanism Performance

| Mechanism | Time (ms) | Throughput (tokens/s) | Memory (MB) |
|-----------|-----------|----------------------|-------------|
"""

        for mechanism, data in benchmarks['attention'].performance_results.items():
            time_ms = data['mean_time_ms']
            throughput = data['throughput_tokens_per_sec']
            memory = data['memory_used_mb']
            markdown += f"| {mechanism.upper()} | {time_ms:.1f} | {throughput:.1f} | {memory:.0f} |\n"

        markdown += f"""
## Kernel Optimization Results

### Attention Kernels
- **Standard PyTorch:** {benchmarks['kernel_optimization'].kernels['attention']['torch']['mean_time_ms']:.1f}ms
- **Flash Attention:** {benchmarks['kernel_optimization'].kernels['attention']['flash_attention']['mean_time_ms']:.1f}ms

### Kernel Fusion
- **Baseline Linear+GELU:** {benchmarks['kernel_optimization'].kernels['fusion']['baseline_linear_gelu']['mean_time_ms']:.3f}ms
- **Fused Linear+GELU:** {benchmarks['kernel_optimization'].kernels['fusion']['fused_linear_gelu']['mean_time_ms']:.3f}ms

## Prompt Suite Results

"""

        for model_data in benchmarks['prompt_suite'].models:
            model_name = model_data['model']
            results = benchmarks['prompt_suite'].results.get(model_name, {})
            avg_time = results.get('average_time_ms', 0)
            tokens = results.get('tokens_generated', 0)
            success_rate = results.get('success_rate', 0) * 100

            markdown += f"### {model_name}\n"
            markdown += f"- **Average Time:** {avg_time:.1f}ms\n"
            markdown += f"- **Tokens Generated:** {tokens:,}\n"
            markdown += f"- **Success Rate:** {success_rate:.1f}%\n\n"

        markdown += """
## Recommendations

"""

        recommendations = self._generate_recommendations(benchmarks, episode_metadata)
        for i, rec in enumerate(recommendations, 1):
            markdown += f"{i}. {rec}\n"

        markdown += """
---
*Report generated by Muse Protocol Benchmark System*
"""

        return markdown

    def save_benchmark_summary_markdown(self, episode_metadata: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save benchmark summary as markdown.

        Args:
            episode_metadata: Episode metadata
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to saved markdown file
        """
        markdown = self.generate_benchmark_summary_markdown(episode_metadata)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            series = episode_metadata.get("series", "unknown").lower()
            episode_num = episode_metadata.get("episode", 0)
            filename = f"{series}_episode_{episode_num:03d}_benchmark_summary_{timestamp}.md"

        file_path = self.reports_dir / filename

        with open(file_path, 'w') as f:
            f.write(markdown)

        return file_path

    def _generate_benchmark_summary(self, benchmarks: Dict[str, Any], episode_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate benchmark summary.

        Args:
            benchmarks: Generated benchmarks
            episode_metadata: Episode metadata

        Returns:
            Summary dictionary
        """
        # Extract key metrics
        inference_perf = benchmarks['inference_performance']
        system_perf = benchmarks['system_performance']
        compilation_perf = benchmarks['compilation']

        # Find fastest backend
        fastest_backend = min(
            compilation_perf.backends.items(),
            key=lambda x: x[1]['benchmark']['mean_time_ms']
        )

        # Find best quantization method
        quantization_methods = benchmarks['quantization'].quantization_methods
        best_quantization = max(
            quantization_methods.items(),
            key=lambda x: x[1]['accuracy']
        )

        # Find fastest attention mechanism
        attention_results = benchmarks['attention'].performance_results
        fastest_attention = min(
            attention_results.items(),
            key=lambda x: x[1]['mean_time_ms']
        )

        return {
            "episode_info": {
                "series": episode_metadata.get("series", "Unknown"),
                "episode": episode_metadata.get("episode", 0),
                "title": episode_metadata.get("title", "Unknown"),
                "models": episode_metadata.get("models", [])
            },
            "performance_highlights": {
                "fastest_backend": {
                    "name": fastest_backend[0],
                    "time_ms": fastest_backend[1]['benchmark']['mean_time_ms']
                },
                "best_quantization": {
                    "method": best_quantization[0],
                    "accuracy": best_quantization[1]['accuracy']
                },
                "fastest_attention": {
                    "mechanism": fastest_attention[0],
                    "time_ms": fastest_attention[1]['mean_time_ms']
                },
                "inference_performance": {
                    "average_time_ms": inference_perf.performance_summary['average_time_ms'],
                    "tokens_per_second": inference_perf.performance_summary['tokens_per_second']
                },
                "system_performance": {
                    "cpu_avg_percent": system_perf.system_metrics.cpu_avg_percent,
                    "memory_avg_percent": system_perf.system_metrics.memory_avg_percent
                }
            },
            "total_benchmarks": len(benchmarks),
            "generated_at": datetime.now().isoformat()
        }

    def _generate_recommendations(self, benchmarks: Dict[str, Any], episode_metadata: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on benchmark results.

        Args:
            benchmarks: Generated benchmarks
            episode_metadata: Episode metadata

        Returns:
            List of recommendations
        """
        recommendations = []

        # Compilation recommendations
        compilation_perf = benchmarks['compilation']
        fastest_backend = min(
            compilation_perf.backends.items(),
            key=lambda x: x[1]['benchmark']['mean_time_ms']
        )

        if fastest_backend[0] != 'eager':
            recommendations.append(
                f"Consider using {fastest_backend[0]} backend for {fastest_backend[1]['benchmark']['mean_time_ms']:.1f}ms inference time "
                f"(vs {compilation_perf.backends['eager']['benchmark']['mean_time_ms']:.1f}ms for eager)"
            )

        # Quantization recommendations
        quantization_methods = benchmarks['quantization'].quantization_methods
        baseline_accuracy = quantization_methods['baseline']['accuracy']

        for method, data in quantization_methods.items():
            if method != 'baseline' and data['accuracy'] >= baseline_accuracy * 0.95:
                compression = (1 - data['model_size_bytes'] / quantization_methods['baseline']['model_size_bytes']) * 100
                if compression > 10:
                    recommendations.append(
                        f"Consider {method.upper()} quantization for {compression:.1f}% size reduction "
                        f"with minimal accuracy loss ({data['accuracy']:.3f} vs {baseline_accuracy:.3f})"
                    )

        # Attention mechanism recommendations
        attention_results = benchmarks['attention'].performance_results
        standard_time = attention_results.get('standard', {}).get('mean_time_ms', 25.0)

        for mechanism, data in attention_results.items():
            if mechanism != 'standard' and data['mean_time_ms'] < standard_time * 0.8:
                speedup = standard_time / data['mean_time_ms']
                recommendations.append(
                    f"Consider {mechanism.upper()} attention mechanism for {speedup:.1f}x speedup "
                    f"({data['mean_time_ms']:.1f}ms vs {standard_time:.1f}ms)"
                )

        # System performance recommendations
        system_perf = benchmarks['system_performance']

        if system_perf.system_metrics.cpu_peak_percent > 90:
            recommendations.append(
                "High CPU utilization detected - consider optimizing CPU-intensive operations"
            )

        if system_perf.system_metrics.memory_peak_percent > 90:
            recommendations.append(
                "High memory usage detected - consider implementing memory optimization techniques"
            )

        if system_perf.system_metrics.gpu_temperature_peak_c and\n    system_perf.system_metrics.gpu_temperature_peak_c > 80:
            recommendations.append(
                "High GPU temperature detected - consider improving cooling or reducing GPU load"
            )

        # Inference performance recommendations
        inference_perf = benchmarks['inference_performance']

        if inference_perf.performance_summary['tokens_per_second'] < 1.0:
            recommendations.append(
                "Low token generation speed - consider model optimization or hardware upgrade"
            )

        # Default recommendations if none generated
        if not recommendations:
            recommendations.append("All benchmarks show good performance - continue current configuration")

        return recommendations

