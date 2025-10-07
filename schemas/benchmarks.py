"""Benchmark schemas for Muse Protocol based on Banterhearts patterns."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class BenchmarkType(str, Enum):
    """Types of benchmarks supported."""
    COMPILATION = "compilation"
    QUANTIZATION = "quantization"
    KERNEL_OPTIMIZATION = "kernel_optimization"
    ATTENTION_MECHANISM = "attention_mechanism"
    MEMORY_OPTIMIZATION = "memory_optimization"
    MODEL_COMPILATION = "model_compilation"
    INFERENCE_PERFORMANCE = "inference_performance"
    PROMPT_SUITE = "prompt_suite"
    SYSTEM_PERFORMANCE = "system_performance"


class DeviceType(str, Enum):
    """Device types for benchmarks."""
    CPU = "cpu"
    GPU = "gpu"
    CUDA = "cuda"
    MPS = "mps"


class BackendType(str, Enum):
    """Backend types for compilation benchmarks."""
    EAGER = "eager"
    JIT = "jit"
    TORCH_COMPILE = "torch_compile"
    ONNX = "onnx"
    TORCH_TRT = "torch_trt"
    TRITON = "triton"


class QuantizationMethod(str, Enum):
    """Quantization methods."""
    BASELINE = "baseline"
    QAT = "qat"  # Quantization Aware Training
    INT8 = "int8"
    FP8 = "fp8"
    INT4 = "int4"
    DYNAMIC = "dynamic"
    STATIC = "static"


class AttentionMechanism(str, Enum):
    """Attention mechanism types."""
    MQA = "mqa"  # Multi-Query Attention
    GQA = "gqa"  # Grouped Query Attention
    SLIDING_WINDOW = "sliding_window"
    SPARSE = "sparse"
    STANDARD = "standard"


class SparsePattern(str, Enum):
    """Sparse attention patterns."""
    STRIDED = "strided"
    FIXED = "fixed"
    LOCAL = "local"
    GLOBAL = "global"
    STAR = "star"
    DIAMOND = "diamond"


class BenchmarkMetadata(BaseModel):
    """Common metadata for all benchmarks."""
    generated_at: datetime = Field(default_factory=datetime.now)
    benchmark_type: BenchmarkType
    version: str = Field(default="1.0")
    environment: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    """Standard performance metrics."""
    mean_time_ms: float
    std_time_ms: Optional[float] = None
    min_time_ms: Optional[float] = None
    max_time_ms: Optional[float] = None
    p50_time_ms: Optional[float] = None
    p95_time_ms: Optional[float] = None
    p99_time_ms: Optional[float] = None
    throughput_tokens_per_sec: Optional[float] = None
    memory_used_mb: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None
    cpu_utilization_percent: Optional[float] = None


class ModelConfig(BaseModel):
    """Model configuration for benchmarks."""
    name: str
    device: DeviceType
    dtype: str = "torch.float32"
    batch_size: int
    seq_len: int
    embed_dim: Optional[int] = None
    num_heads: Optional[int] = None
    num_layers: Optional[int] = None
    hidden_size: Optional[int] = None


class CompilationBenchmark(BaseModel):
    """Compilation benchmark schema."""
    metadata: BenchmarkMetadata
    model: ModelConfig
    settings: Dict[str, Any]
    backends: Dict[str, Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QuantizationBenchmark(BaseModel):
    """Quantization benchmark schema."""
    metadata: BenchmarkMetadata
    model: ModelConfig
    quantization_methods: Dict[QuantizationMethod, Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class KernelOptimizationBenchmark(BaseModel):
    """Kernel optimization benchmark schema."""
    metadata: BenchmarkMetadata
    kernels: Dict[str, Dict[str, PerformanceMetrics]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AttentionMechanismConfig(BaseModel):
    """Configuration for attention mechanisms."""
    mechanism: AttentionMechanism
    num_heads: int
    head_dim: int
    num_kv_heads: Optional[int] = None
    window_size: Optional[int] = None
    sparsity_ratio: Optional[float] = None
    sparse_pattern: Optional[SparsePattern] = None


class AttentionBenchmark(BaseModel):
    """Attention mechanism benchmark schema."""
    metadata: BenchmarkMetadata
    model: ModelConfig
    attention_configs: Dict[str, AttentionMechanismConfig]
    performance_results: Dict[str, PerformanceMetrics]
    cross_comparison: Dict[str, Dict[str, float]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PromptSuiteConfig(BaseModel):
    """Configuration for prompt suite benchmarks."""
    model: str
    temperature: float = 0.3
    top_p: float = 0.9
    max_tokens: Optional[int] = None
    prompt_count: int


class PromptSuiteBenchmark(BaseModel):
    """Prompt suite benchmark schema."""
    metadata: BenchmarkMetadata
    prompt_count: int
    prompts: List[str]
    models: List[PromptSuiteConfig]
    results: Dict[str, Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemPerformanceMetrics(BaseModel):
    """System performance metrics."""
    cpu_avg_percent: float
    cpu_peak_percent: float
    memory_avg_percent: float
    memory_peak_percent: float
    gpu_temperature_avg_c: Optional[float] = None
    gpu_temperature_peak_c: Optional[float] = None
    gpu_power_avg_w: Optional[float] = None
    gpu_power_peak_w: Optional[float] = None
    gpu_utilization_avg_percent: Optional[float] = None
    gpu_utilization_peak_percent: Optional[float] = None


class SystemPerformanceBenchmark(BaseModel):
    """System performance benchmark schema."""
    metadata: BenchmarkMetadata
    duration_minutes: float
    system_metrics: SystemPerformanceMetrics
    gpu_info: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class InferencePerformanceBenchmark(BaseModel):
    """Inference performance benchmark schema."""
    metadata: BenchmarkMetadata
    model: ModelConfig
    test_scenarios: List[Dict[str, Any]]
    generation_times: List[float]
    total_tokens: int
    performance_summary: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemoryOptimizationBenchmark(BaseModel):
    """Memory optimization benchmark schema."""
    metadata: BenchmarkMetadata
    model: ModelConfig
    optimization_methods: Dict[str, Dict[str, Any]]
    memory_usage: Dict[str, float]  # MB
    compression_ratio: Dict[str, float]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ModelCompilationBenchmark(BaseModel):
    """Model compilation benchmark schema."""
    metadata: BenchmarkMetadata
    model: ModelConfig
    compilation_targets: List[str]
    compilation_times: Dict[str, float]
    optimization_levels: Dict[str, Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Union type for all benchmark types
BenchmarkResult = Union[
    CompilationBenchmark,
    QuantizationBenchmark,
    KernelOptimizationBenchmark,
    AttentionBenchmark,
    PromptSuiteBenchmark,
    SystemPerformanceBenchmark,
    InferencePerformanceBenchmark,
    MemoryOptimizationBenchmark,
    ModelCompilationBenchmark
]


class BenchmarkReport(BaseModel):
    """Comprehensive benchmark report."""
    metadata: BenchmarkMetadata
    benchmarks: List[BenchmarkResult]
    summary: Dict[str, Any]
    recommendations: List[str]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def create_benchmark_template(benchmark_type: BenchmarkType) -> Dict[str, Any]:
    """Create a template for a specific benchmark type."""

    base_metadata = {
        "generated_at": datetime.now(),
        "benchmark_type": benchmark_type,
        "version": "1.0",
        "environment": {
            "python_version": "3.9+",
            "pytorch_version": "2.0+",
            "device": "cpu"
        },
        "tags": []
    }

    templates = {
        BenchmarkType.COMPILATION: {
            **base_metadata,
            "model": {
                "name": "transformer",
                "device": "cpu",
                "dtype": "torch.float32",
                "batch_size": 2,
                "seq_len": 128,
                "embed_dim": 256,
                "num_heads": 4,
                "num_layers": 2
            },
            "settings": {
                "runs": 10,
                "warmup_runs": 3,
                "backends": ["eager", "jit", "torch_compile", "onnx"]
            },
            "backends": {}
        },

        BenchmarkType.QUANTIZATION: {
            **base_metadata,
            "model": {
                "name": "llama3.1:8b",
                "device": "cpu",
                "dtype": "torch.float32",
                "batch_size": 1,
                "seq_len": 512
            },
            "quantization_methods": {
                "baseline": {
                    "accuracy": 0.75,
                    "loss": 0.608,
                    "model_size_bytes": 2781
                },
                "int8": {
                    "accuracy": 0.75,
                    "loss": 0.608,
                    "model_size_bytes": 3029
                },
                "fp8": {
                    "accuracy": 0.75,
                    "loss": 0.608,
                    "model_size_bytes": 2781
                }
            }
        },

        BenchmarkType.KERNEL_OPTIMIZATION: {
            **base_metadata,
            "kernels": {
                "attention": {
                    "torch": {
                        "mean_time_ms": 24.6,
                        "std_time_ms": 73.2,
                        "min_time_ms": 0.17,
                        "max_time_ms": 244.1
                    }
                },
                "tensor_core": {
                    "512x512x512": {
                        "mean_time_ms": 16.7,
                        "std_time_ms": 50.0,
                        "min_time_ms": 0.03,
                        "max_time_ms": 166.6
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
        },

        BenchmarkType.ATTENTION_MECHANISM: {
            **base_metadata,
            "model": {
                "name": "transformer",
                "device": "cpu",
                "dtype": "torch.float32",
                "batch_size": 2,
                "seq_len": 128,
                "embed_dim": 512,
                "num_heads": 8
            },
            "attention_configs": {
                "mqa": {
                    "mechanism": "mqa",
                    "num_heads": 8,
                    "head_dim": 64,
                    "num_kv_heads": 1
                },
                "gqa": {
                    "mechanism": "gqa",
                    "num_heads": 8,
                    "head_dim": 64,
                    "num_kv_heads": 2
                },
                "sliding_window": {
                    "mechanism": "sliding_window",
                    "num_heads": 8,
                    "head_dim": 64,
                    "window_size": 128
                },
                "sparse": {
                    "mechanism": "sparse",
                    "num_heads": 8,
                    "head_dim": 64,
                    "sparsity_ratio": 0.5,
                    "sparse_pattern": "strided"
                }
            },
            "performance_results": {},
            "cross_comparison": {}
        },

        BenchmarkType.PROMPT_SUITE: {
            **base_metadata,
            "prompt_count": 5,
            "prompts": [
                "banter prompt: Player failed a mission but needs encouragement.",
                "Give a battle quote for a co-op shooter win.",
                "Prompt for rare loot find celebration banter.",
                "Craft a witty remark after a close racing finish.",
                "Motivate a teammate before a final boss fight."
            ],
            "models": [
                {
                    "model": "llama3.1:8b-instruct-q4_0",
                    "prompt_count": 5,
                    "completed": 0,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                }
            ],
            "results": {}
        },

        BenchmarkType.SYSTEM_PERFORMANCE: {
            **base_metadata,
            "duration_minutes": 1.0,
            "system_metrics": {
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
            },
            "gpu_info": {
                "gpus": [
                    {
                        "index": 0,
                        "name": "NVIDIA GeForce RTX 4090",
                        "memory_used_mb": 8192,
                        "memory_total_mb": 24576,
                        "temperature_c": 65,
                        "power_draw_w": 180,
                        "utilization_gpu_percent": 75
                    }
                ]
            }
        },

        BenchmarkType.INFERENCE_PERFORMANCE: {
            **base_metadata,
            "model": {
                "name": "llama3.1:8b-instruct-q4_0",
                "device": "cpu",
                "dtype": "torch.float32",
                "batch_size": 1,
                "seq_len": 512
            },
            "test_scenarios": [
                {
                    "context": "player_died",
                    "tone": "encouraging",
                    "game_type": "rpg",
                    "player_level": 25
                }
            ],
            "generation_times": [2500.0, 2400.0, 2600.0],
            "total_tokens": 1500,
            "performance_summary": {
                "average_time_ms": 2500.0,
                "min_time_ms": 2400.0,
                "max_time_ms": 2600.0,
                "tokens_per_second": 0.6
            }
        }
    }

    return templates.get(benchmark_type, base_metadata)
