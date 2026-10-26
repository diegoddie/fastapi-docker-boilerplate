"""
The ai package tracing: every call to the model traced in Langfuse.

Tracing is on when ``FASTAPI_LANGFUSE_PUBLIC_KEY`` and
``FASTAPI_LANGFUSE_SECRET_KEY`` are set. Unless
``FASTAPI_LANGFUSE_CAPTURE_CONTENT`` is, the traces carry the model, the
tokens, the timings, the user id and the metadata, but no prompt or answer.
"""

from functools import cache
from typing import Annotated

from fastapi import Depends
from langchain_core.callbacks import BaseCallbackHandler
from langfuse import Langfuse, LangfuseOtelSpanAttributes
from langfuse.langchain import CallbackHandler
from langfuse.types import MaskOtelSpansParams, MaskOtelSpansResult, OtelSpanPatch
from opentelemetry.sdk.trace import TracerProvider

from app.core.config import settings

CONTENT_ATTRIBUTES = (
    LangfuseOtelSpanAttributes.OBSERVATION_INPUT,
    LangfuseOtelSpanAttributes.OBSERVATION_OUTPUT,
)


def drop_content(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult:
    """Remove the prompts and the answers from the spans sent to Langfuse."""
    return MaskOtelSpansResult(
        span_patches={
            identifier: OtelSpanPatch(
                delete_attributes=tuple(
                    name for name in CONTENT_ATTRIBUTES if name in span.attributes
                )
            )
            for identifier, span in params.spans.items()
            if any(name in span.attributes for name in CONTENT_ATTRIBUTES)
        }
    )


@cache
def get_langfuse() -> Langfuse | None:
    """Return the Langfuse client, created once; None when tracing is off."""
    if settings.LANGFUSE_PUBLIC_KEY is None or settings.LANGFUSE_SECRET_KEY is None:
        return None
    return Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY.get_secret_value(),
        base_url=settings.LANGFUSE_BASE_URL,
        environment=settings.ENVIRONMENT,
        release=settings.VERSION,
        # Why: a provider of its own, so the spans of the app's other
        # OpenTelemetry instrumentation never reach Langfuse, nor these them.
        tracer_provider=TracerProvider(),
        mask_otel_spans=None if settings.LANGFUSE_CAPTURE_CONTENT else drop_content,
    )


def get_tracing_callbacks() -> list[BaseCallbackHandler]:
    """Return the callbacks that trace a call to the model, if tracing is on."""
    if get_langfuse() is None:
        return []
    return [CallbackHandler(public_key=settings.LANGFUSE_PUBLIC_KEY)]


TracingCallbacksDep = Annotated[
    list[BaseCallbackHandler], Depends(get_tracing_callbacks)
]
