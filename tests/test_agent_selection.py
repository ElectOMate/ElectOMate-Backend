from __future__ import annotations

from dataclasses import dataclass

from em_backend.agent.agent import deduplicate_party_list


@dataclass
class DummyParty:
    shortname: str





def test_deduplicate_party_list_keeps_order_and_uniques() -> None:
    parties = [DummyParty("Tisza"), DummyParty("Tisza"), DummyParty("DK"), DummyParty("Tisza"), DummyParty("Fidesz")]

    unique_parties = deduplicate_party_list(parties)

    assert [party.shortname for party in unique_parties] == ["Tisza", "DK", "Fidesz"]


def test_deduplicate_party_list_handles_empty() -> None:
    assert deduplicate_party_list([]) == []


def test_deduplicate_party_list_preserves_first_occurrence() -> None:
    parties = [DummyParty("DK"), DummyParty("Tisza"), DummyParty("DK"), DummyParty("Fidesz"), DummyParty("Tisza")]

    unique_parties = deduplicate_party_list(parties)

    assert [party.shortname for party in unique_parties] == ["DK", "Tisza", "Fidesz"]

