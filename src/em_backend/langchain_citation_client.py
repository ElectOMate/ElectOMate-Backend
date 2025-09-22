"""
LangChain Citation Client Wrapper

This module provides a wrapper around LangChain's async client that handles
citations while using pure LangChain messages throughout.
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI


# Citation-related classes to preserve functionality
@dataclass
class Document:
    """Document class for citation handling"""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


class DocumentToolContent:
    """Document tool content for citations"""

    def __init__(self, document: Document) -> None:
        self.document = document


@dataclass
class CitationOptions:
    """Citation options for compatibility"""

    mode: str = "ACCURATE"


# Tool classes for compatibility (still needed for tools.py)
class ToolV2:
    """Compatibility class for Cohere ToolV2"""

    def __init__(self, type: str, function: "ToolV2Function") -> None:
        self.type = type
        self.function = function


class ToolV2Function:
    """Compatibility class for Cohere ToolV2Function"""

    def __init__(self, name: str, description: str, parameters: dict[str, Any]) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters


class JsonObjectResponseFormatV2:
    """Compatibility class for Cohere JsonObjectResponseFormatV2"""

    def __init__(self, **kwargs) -> None:
        self.type = "json_object"
        for key, value in kwargs.items():
            setattr(self, key, value)


# Response classes
class LangChainResponse:
    """Response wrapper that mimics Cohere's response interface"""

    def __init__(self, message: AIMessage, citations: dict[str, list[Any]]) -> None:
        self.message = LangChainMessageWrapper(message, citations)
        self.citations = citations


class LangChainMessageWrapper:
    """Message wrapper that mimics Cohere's message interface"""

    def __init__(self, message: AIMessage, citations: dict[str, list[Any]]) -> None:
        self._message = message
        self.citations = citations
        self.content = [LangChainContentWrapper(message.content)]
        self.tool_calls = self._extract_tool_calls()
        self.tool_plan = ""  # OpenAI doesn't have tool plans

    def _extract_tool_calls(self) -> None | list[Any]:
        """Extract tool calls from LangChain message"""
        if not self._message.tool_calls:
            return None

        tool_calls = []
        for tc in self._message.tool_calls:
            tool_calls.append(
                {
                    "id": tc.get("id", ""),
                    "type": tc.get("type", "function"),
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": tc.get("args", ""),
                    },
                }
            )
        return tool_calls


class LangChainContentWrapper:
    """Content wrapper that mimics Cohere's content interface"""

    def __init__(self, content) -> None:
        self.text = content or ""


class LangChainStreamEvent:
    """Stream event wrapper that mimics Cohere's stream event interface"""

    def __init__(
        self,
        event_type: str,
        delta_content: str | None = None,
        tool_calls: list[dict] | None = None,
        finish_reason: str | None = None,
        citations: dict[str, list[Any]] | None = None,
    ) -> None:
        self.type = event_type
        self.delta = LangChainDelta(delta_content, tool_calls, finish_reason)
        self.citations = citations or {"database": [], "web": []}


class LangChainDelta:
    """Delta wrapper that mimics Cohere's delta interface"""

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        finish_reason: str | None = None,
    ) -> None:
        self.message = LangChainDeltaMessage(content, tool_calls)
        self.finish_reason = finish_reason


class LangChainDeltaMessage:
    """Delta message wrapper that mimics Cohere's delta message interface"""

    def __init__(self, content: str = None, tool_calls: list[dict] = None) -> None:
        self.content = LangChainDeltaContent(content)
        self.tool_calls = tool_calls


class LangChainDeltaContent:
    """Delta content wrapper that mimics Cohere's delta content interface"""

    def __init__(self, content: str | None = None) -> None:
        self.text = content or ""


class LangChainAsyncCitationClient:
    """
    LangChain Async Citation Client that wraps LangChain's ChatOpenAI
    and provides Cohere-compatible chat and chat_stream methods.
    """

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        """
        Initialize the LangChain citation client.

        Args:
            api_key: OpenAI API key
            base_url: Optional base URL for OpenAI API
        """
        self.client = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model="gpt-4o",
            streaming=True,
            temperature=0.1,
        )
        self.citations: dict[str, list[Any]] = {"database": [], "web": []}

    async def chat(
        self,
        model: str,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs,
    ) -> LangChainResponse:
        """
        Chat completion method that works with LangChain messages.

        Args:
            model: Model name (e.g., "gpt-4o")
            messages: list of LangChain message objects
            tools: Optional list of tools
            response_format: Optional response format
            **kwargs: Additional arguments

        Returns:
            LangChainResponse object with Cohere-compatible interface
        """
        # Set response format if provided
        if response_format:
            self.client.response_format = response_format

        # Make the API call
        response = await self.client.ainvoke(messages, tools=tools, **kwargs)

        return LangChainResponse(response, self.citations)

    def chat_stream(
        self,
        model: str,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
        citation_options: CitationOptions | None = None,
        **kwargs,
    ) -> AsyncGenerator[LangChainStreamEvent]:
        """
        Streaming chat completion that works with LangChain messages.

        Args:
            model: Model name (e.g., "gpt-4o")
            messages: list of LangChain message objects
            tools: Optional list of tools
            citation_options: Citation options (for compatibility)
            **kwargs: Additional arguments

        Yields:
            LangChainStreamEvent objects with Cohere-compatible interface
        """
        return self._stream_chat(model, messages, tools, citation_options, **kwargs)

    async def _stream_chat(
        self,
        model: str,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
        citation_options: CitationOptions | None = None,
        **kwargs,
    ) -> AsyncGenerator[LangChainStreamEvent]:
        """Internal streaming implementation"""

        # TODO: Handle citations

        # Make the streaming API call
        async for chunk in self.client.astream(messages, tools=tools, **kwargs):
            # Determine event type based on chunk content
            event_type = self._determine_event_type(chunk)

            # Extract relevant data from chunk
            delta_content = None
            tool_calls = None
            finish_reason = None

            if hasattr(chunk, "content") and chunk.content:
                delta_content = chunk.content
            elif hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls = chunk.tool_calls
            elif hasattr(chunk, "finish_reason"):
                finish_reason = chunk.finish_reason

            yield LangChainStreamEvent(
                event_type=event_type,
                delta_content=delta_content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                citations=self.citations,
            )

    def _determine_event_type(self, chunk) -> str:
        """Determine the event type based on LangChain chunk"""
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            return "tool-call-start"
        elif hasattr(chunk, "content") and chunk.content:
            return "content-delta"
        elif hasattr(chunk, "finish_reason") and chunk.finish_reason:
            return "message-end"
        else:
            return "unknown"


# Export LangChain message classes for direct use
__all__ = [
    "HumanMessage",
    "SystemMessage",
    "AIMessage",
    "ToolMessage",
    "Document",
    "DocumentToolContent",
    "CitationOptions",
    "ToolV2",
    "ToolV2Function",
    "JsonObjectResponseFormatV2",
    "LangChainAsyncCitationClient",
    "LangChainResponse",
    "LangChainStreamEvent",
]
