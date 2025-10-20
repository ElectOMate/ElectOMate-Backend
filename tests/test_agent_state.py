from typing import Annotated, get_args, get_origin

from em_backend.agent.types import (
    NonComparisonQuestionState,
    merge_party_sources,
    merge_party_summaries,
    use_latest_party,
)
from em_backend.database.models import Party


def test_noncomparison_party_state_uses_latest_party_aggregator() -> None:
    party_annotation = NonComparisonQuestionState.__annotations__["party"]

    assert get_origin(party_annotation) is Annotated

    annotated_args = get_args(party_annotation)
    assert len(annotated_args) == 2

    party_type, aggregator = annotated_args

    assert party_type is Party
    assert aggregator is use_latest_party

    sentinel_prev = object()
    sentinel_update = object()

    assert use_latest_party(sentinel_prev, sentinel_update) is sentinel_update


def test_party_sources_merge_aggregator() -> None:
    sources_annotation = NonComparisonQuestionState.__annotations__["perplexity_party_sources"]

    assert get_origin(sources_annotation) is Annotated

    annotated_args = get_args(sources_annotation)
    assert len(annotated_args) == 2

    mapping_type, aggregator = annotated_args

    assert mapping_type is dict
    assert aggregator is merge_party_sources

    base = {"PCCh": [{"title": "A", "url": "u", "snippet": "s"}]}
    update = {"PCCh": [{"title": "B", "url": "v", "snippet": "t"}], "PRCh": []}

    merged = merge_party_sources(base, update)

    assert len(merged["PCCh"]) == 2
    assert "PRCh" in merged


def test_party_summaries_merge_aggregator() -> None:
    summary_annotation = NonComparisonQuestionState.__annotations__["perplexity_party_summaries"]

    assert get_origin(summary_annotation) is Annotated

    annotated_args = get_args(summary_annotation)
    assert len(annotated_args) == 2

    mapping_type, aggregator = annotated_args

    assert mapping_type is dict
    assert aggregator is merge_party_summaries

    merged = merge_party_summaries({"PCCh": "old"}, {"PCCh": "new", "PRCh": "summary"})

    assert merged["PCCh"] == "new"
    assert merged["PRCh"] == "summary"
