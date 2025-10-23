from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_load_germany_data_constants_match_spec() -> None:
    module = importlib.import_module("scripts.load_germany_data")

    assert module.GERMANY_COUNTRY.name == "Germany"
    assert module.GERMANY_COUNTRY.code == "DE"

    election_seed = module.GERMANY_ELECTION
    assert election_seed.name == "Bundestagswahl 2025"
    assert election_seed.year == 2025
    assert election_seed.date.isoformat() == "2025-01-01T00:00:00"
    assert election_seed.url == "https://en.wikipedia.org/wiki/Germany_2025_election"
    assert election_seed.wv_collection == "D2025bundestagswahl"

    country_id = UUID("725b3476-cd23-4ee7-8192-de8a1d64ea9a")
    election_create = election_seed.to_create(country_id)
    assert election_create.country_id == country_id

    party_seeds = module.GERMANY_PARTIES
    shortnames = [seed.shortname for seed in party_seeds]
    assert shortnames == ["CDU", "SPD", "AfD"]

    parties_by_short = {seed.shortname: seed for seed in party_seeds}
    assert parties_by_short["CDU"].fullname == (
        "Christlich Demokratische Union Deutschlands / Christlich-Soziale Union in Bayern"
    )
    assert parties_by_short["CDU"].description.startswith("Die CDU/CSU ist ein Bündnis")
    assert parties_by_short["CDU"].url is None

    assert parties_by_short["SPD"].fullname == "Sozialdemokratische Partei Deutschlands"
    assert parties_by_short["SPD"].description.startswith("Die SPD ist Deutschlands älteste Partei")
    assert parties_by_short["SPD"].url is None

    assert parties_by_short["AfD"].fullname == "Alternative für Deutschland"
    assert parties_by_short["AfD"].description.startswith("Die AfD ist eine rechtspopulistische")
    assert parties_by_short["AfD"].url is None

    election_id = UUID("7160b058-e88d-4e89-823d-de07342b3f79")
    party_create_models = [seed.to_create(election_id) for seed in party_seeds]
    assert [model.election_id for model in party_create_models] == [election_id] * 3

