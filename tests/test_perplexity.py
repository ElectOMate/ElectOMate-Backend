import pytest

from em_backend.agent.agent import Agent
from em_backend.agent.utils import (
    format_party_web_sources_for_prompt,
    format_web_sources_for_prompt,
    normalize_perplexity_sources,
)
from em_backend.models.chunks import PerplexitySourcesChunk


def test_agent_graph_contains_perplexity_nodes() -> None:
    graph = Agent.get_compiled_agent_graph()
    nodes = getattr(graph, "graph", None)
    if nodes is None:  # pragma: no cover - langgraph API compatibility
        pytest.skip("LangGraph Pregel does not expose internal graph structure")
    node_names = set(nodes.nodes)
    assert "decide_generic_web_search" in node_names
    assert "perplexity_generic_search" in node_names
    assert "perplexity_comparison_search" in node_names
    assert "perplexity_single_party_search" in node_names


def test_normalize_perplexity_sources_merges_payloads() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "Summary bullet one."},
                        {"type": "text", "text": "Summary bullet two."},
                    ]
                }
            }
        ],
        "citations": [
            {
                "title": "Example Source",
                "url": "https://example.com/a",
                "snippet": "A short teaser",
            },
            "https://example.com/b",
        ],
        "search_results": [
            {
                "name": "Example Source",
                "source": "https://example.com/a",
                "passage": "Duplicate entry should be deduplicated",
            },
            {
                "title": "Third",
                "url": "https://example.com/c",
            },
        ],
    }

    answer, sources = normalize_perplexity_sources(payload)
    assert "Summary" in answer
    urls = [item["url"] for item in sources]
    assert urls.count("https://example.com/a") == 1
    assert "https://example.com/b" in urls
    assert "https://example.com/c" in urls


def test_format_web_sources_for_prompt_includes_snippets() -> None:
    sources = [
        {"title": "First", "url": "https://example.com/one", "snippet": "Snippet"},
        {"title": "Second", "url": "https://example.com/two", "snippet": ""},
    ]
    rendered = format_web_sources_for_prompt(sources)
    assert "1. Title: First" in rendered
    assert "Snippet" in rendered
    assert "https://example.com/two" in rendered


def test_perplexity_sources_chunk_serializes_summary() -> None:
    chunk = PerplexitySourcesChunk(
        scope="generic",
        summary="Two bullet summary",
        sources=[
            {
                "title": "Example",
                "url": "https://example.com",
                "snippet": "Snippet text",
            }
        ],
    )
    dumped = chunk.model_dump()
    assert dumped["type"] == "web_response_sources"
    assert dumped["summary"] == "Two bullet summary"
    assert dumped["sources"][0]["title"] == "Example"


def test_format_party_web_sources_for_prompt_groups_sources_by_party() -> None:
    parties = [
        type("Party", (), {"fullname": "Party A", "shortname": "PA"})(),
        type("Party", (), {"fullname": "Party B", "shortname": "PB"})(),
    ]
    sources = [
        {"title": "A1", "url": "https://example.com/a1", "party": "PA", "snippet": "foo"},
        {"title": "B1", "url": "https://example.com/b1", "party": "PB", "snippet": "bar"},
    ]
    summaries = {"PA": "Summary A", "PB": "Summary B"}

    rendered = format_party_web_sources_for_prompt(parties, sources, summaries)

    assert "Party: Party A (PA)" in rendered
    assert "Summary: Summary A" in rendered
    assert "https://example.com/b1" in rendered
