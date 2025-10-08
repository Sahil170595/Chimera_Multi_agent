"""OpenTelemetry tracing for Muse Protocol."""

import logging
import os
from typing import Optional
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

# Global tracer
_tracer: Optional[trace.Tracer] = None


def init_tracing(service_name: str = "muse-protocol") -> None:
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: Service name for traces
    """
    global _tracer

    try:
        # Create resource with service name
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENV", "production")
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter (sends to Datadog via OTLP)
        # Use gRPC endpoint and lowercase header key for gRPC metadata
        otlp_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "https://otlp.datadoghq.com:4317"
        )
        
        dd_api_key = os.getenv("DD_API_KEY", "")
        
        # gRPC requires lowercase header keys
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=(("api-key", dd_api_key),) if dd_api_key else ()
        )

        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(__name__)

        logger.info(f"OpenTelemetry tracing initialized for {service_name}")

    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}")
        # Fallback to no-op tracer
        _tracer = trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """Get the global tracer.

    Returns:
        OpenTelemetry tracer
    """
    global _tracer
    if _tracer is None:
        init_tracing()
    return _tracer


@contextmanager
def trace_operation(
        operation_name: str,
        attributes: Optional[dict] = None):
    """Context manager for tracing operations.

    Args:
        operation_name: Name of the operation
        attributes: Optional attributes to add to span

    Example:
        with trace_operation("ingest_benchmarks", {"repo": "banterhearts"}):
            # ... do work ...
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.set_attribute("error.type", type(e).__name__)
            raise


def trace_agent_run(agent_name: str):
    """Decorator for tracing agent runs.

    Args:
        agent_name: Name of the agent

    Example:
        @trace_agent_run("watcher")
        def check_data_freshness(self, hours: int):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with trace_operation(
                f"agent.{agent_name}.{func.__name__}",
                {"agent": agent_name}
            ):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class TracedAgent:
    """Base class for agents with automatic tracing."""

    def __init__(self, agent_name: str):
        """Initialize traced agent.

        Args:
            agent_name: Name of the agent for tracing
        """
        self.agent_name = agent_name
        self.tracer = get_tracer()

    def trace(self, operation: str, **attributes):
        """Create a traced operation.

        Args:
            operation: Operation name
            **attributes: Additional span attributes

        Returns:
            Context manager for the traced operation
        """
        attrs = {"agent": self.agent_name, **attributes}
        return trace_operation(
            f"agent.{self.agent_name}.{operation}",
            attrs
        )
