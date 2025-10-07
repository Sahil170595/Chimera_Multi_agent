#!/usr/bin/env python3
"""
Test script to demonstrate Muse Protocol benchmark functionality.
This script generates comprehensive benchmarks for Chimera episodes.
"""

import sys
from pathlib import Path

from schemas.simple_benchmark_generator import SimpleBenchmarkGenerator, generate_episode_benchmarks
from agents.chimera import ChimeraAuthor
from apps.config import AgentConfig

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_benchmark_generation():
    """Test benchmark generation functionality."""
    print("=" * 60)
    print("MUSE PROTOCOL BENCHMARK GENERATION TEST")
    print("=" * 60)

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Initialize benchmark generator
    generator = SimpleBenchmarkGenerator(reports_dir)

    # Test different benchmark types
    print("\n1. Testing Individual Benchmark Types...")

    model_config = {
        "name": "llama3.1:8b-instruct-q4_0",
        "device": "cpu",
        "dtype": "torch.float32",
        "batch_size": 1,
        "seq_len": 512
    }

    # Generate compilation benchmark
    print("   Generating compilation benchmark...")
    compilation_benchmark = generator.generate_compilation_benchmark(model_config)
    compilation_path = generator.save_benchmark(compilation_benchmark, "test_compilation_benchmark.json")
    print(f"   Saved: {compilation_path}")

    # Generate quantization benchmark
    print("   Generating quantization benchmark...")
    quantization_benchmark = generator.generate_quantization_benchmark(model_config)
    quantization_path = generator.save_benchmark(quantization_benchmark, "test_quantization_benchmark.json")
    print(f"   Saved: {quantization_path}")

    # Generate kernel optimization benchmark
    print("   Generating kernel optimization benchmark...")
    kernel_benchmark = generator.generate_kernel_optimization_benchmark()
    kernel_path = generator.save_benchmark(kernel_benchmark, "test_kernel_benchmark.json")
    print(f"   Saved: {kernel_path}")

    # Generate attention benchmark
    print("   Generating attention mechanism benchmark...")
    attention_benchmark = generator.generate_attention_benchmark(model_config)
    attention_path = generator.save_benchmark(attention_benchmark, "test_attention_benchmark.json")
    print(f"   Saved: {attention_path}")

    # Generate prompt suite benchmark
    print("   Generating prompt suite benchmark...")
    prompts = [
        "Generate encouraging banter for a player who failed a mission",
        "Create celebratory text for defeating a boss",
        "Write excited commentary for finding rare loot"
    ]
    models = ["llama3.1:8b-instruct-q4_0", "gpt-4"]
    prompt_benchmark = generator.generate_prompt_suite_benchmark(prompts, models)
    prompt_path = generator.save_benchmark(prompt_benchmark, "test_prompt_suite_benchmark.json")
    print(f"   Saved: {prompt_path}")

    # Generate system performance benchmark
    print("   Generating system performance benchmark...")
    system_benchmark = generator.generate_system_performance_benchmark()
    system_path = generator.save_benchmark(system_benchmark, "test_system_benchmark.json")
    print(f"   Saved: {system_path}")

    # Generate inference performance benchmark
    print("   Generating inference performance benchmark...")
    inference_benchmark = generator.generate_inference_performance_benchmark(model_config)
    inference_path = generator.save_benchmark(inference_benchmark, "test_inference_benchmark.json")
    print(f"   Saved: {inference_path}")

    print("\n2. Testing Comprehensive Episode Benchmarks...")

    # Generate comprehensive episode benchmarks
    episode_metadata = {
        "title": "Chimera Episode 001: Advanced AI Optimization",
        "series": "Chimera",
        "episode": 1,
        "models": ["llama3.1:8b-instruct-q4_0", "gpt-4"],
        "run_id": "test-run-001",
        "commit_sha": "a" * 40
    }

    episode_benchmarks = generate_episode_benchmarks(episode_metadata)
    print(f"   Generated {len(episode_benchmarks)} benchmark types for episode")

    # Display summary
    print("\n3. Benchmark Summary:")
    print(f"   Total benchmark types: {len(episode_benchmarks)}")
    print("   Individual benchmark files: 7")

    # Show key metrics from benchmarks
    print("\n4. Key Performance Highlights:")

    # Compilation benchmarks
    compilation_data = episode_benchmarks["compilation"]
    fastest_backend = min(
        compilation_data["backends"].items(),
        key=lambda x: x[1]["benchmark"]["mean_time_ms"]
    )
    print(f"   Fastest Backend: {fastest_backend[0]} ({fastest_backend[1]['benchmark']['mean_time_ms']:.1f}ms)")

    # Quantization benchmarks
    quantization_data = episode_benchmarks["quantization"]
    best_quantization = max(
        quantization_data["quantization_methods"].items(),
        key=lambda x: x[1]["accuracy"]
    )
    print(f"   Best Quantization: {best_quantization[0].upper()} ({best_quantization[1]['accuracy']:.3f} accuracy)")

    # Attention benchmarks
    attention_data = episode_benchmarks["attention"]
    fastest_attention = min(
        attention_data["performance_results"].items(),
        key=lambda x: x[1]["mean_time_ms"]
    )
    print(f"   Fastest Attention: {fastest_attention[0].upper()} ({fastest_attention[1]['mean_time_ms']:.1f}ms)")

    # Inference performance
    inference_data = episode_benchmarks["inference_performance"]
    perf_summary = inference_data["performance_summary"]
    print(f"   Inference Performance: {perf_summary['average_time_ms']:.1f}ms avg, {perf_summary['tokens_per_second']:.2f} tokens/s")

    # System performance
    system_data = episode_benchmarks["system_performance"]
    sys_metrics = system_data["system_metrics"]
    print(f"   System Performance: {sys_metrics['cpu_avg_percent']:.1f}% CPU, {sys_metrics['memory_avg_percent']:.1f}% Memory")

    print("\n5. Testing Chimera Agent Integration...")

    # Test Chimera agent with benchmarks
    config = AgentConfig(
        model="llama3.1:8b-instruct-q4_0",
        temperature=0.3,
        max_tokens=1000
    )

    chimera_author = ChimeraAuthor(config)
    episode_result = chimera_author.generate_episode("test-commit-sha", "SELECT * FROM performance_metrics")

    print(f"   Generated Chimera episode: {episode_result['metadata']['title']}")
    print(f"   Episode number: {episode_result['metadata']['episode']}")
    print(f"   Benchmark files: {len(episode_result['benchmark_files'])}")

    # Show benchmark file paths
    for file_type, file_path in episode_result['benchmark_files'].items():
        print(f"   - {file_type.upper()}: {file_path}")

    print("\n" + "=" * 60)
    print("BENCHMARK GENERATION TEST COMPLETED!")
    print("=" * 60)
    print(f"Total files generated: {len(list(reports_dir.glob('test_*.json'))) + len(list(reports_dir.glob('chimera_episode_*.json')))}")
    print(f"Reports directory: {reports_dir.absolute()}")

    return True


if __name__ == "__main__":
    try:
        success = test_benchmark_generation()
        if success:
            print("\nAll tests passed successfully!")
            sys.exit(0)
        else:
            print("\nSome tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
