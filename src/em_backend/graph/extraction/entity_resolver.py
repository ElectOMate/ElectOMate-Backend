"""Entity resolution for Hungarian politicians and parties.

Matches extracted speaker names to known politicians,
resolves party affiliations, and handles Hungarian name variants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ResolvedEntity:
    """A resolved politician entity."""

    canonical_name: str
    party_shortname: str | None
    role: str | None
    confidence: float  # 0.0 to 1.0
    match_type: str  # "exact", "fuzzy", "alias", "unknown"


# ============================================================================
# Known Hungarian politicians and their aliases
# ============================================================================

# {canonical_name: {party, role, aliases}}
KNOWN_POLITICIANS: dict[str, dict] = {
    "Orbán Viktor": {
        "party": "FIDESZ",
        "role": "Miniszterelnök",
        "aliases": [
            "Orbán", "Viktor Orbán", "Orban Viktor", "Orban",
            "miniszterelnök", "a kormányfő", "Orbán V.",
        ],
    },
    "Magyar Péter": {
        "party": "TISZA",
        "role": "Pártelnök",
        "aliases": [
            "Magyar", "Péter Magyar", "Peter Magyar", "Magyar P.",
        ],
    },
    "Gyurcsány Ferenc": {
        "party": "DK",
        "role": "Pártelnök",
        "aliases": [
            "Gyurcsány", "Ferenc Gyurcsány", "Gyurcsany Ferenc",
            "Gyurcsány F.",
        ],
    },
    "Dobrev Klára": {
        "party": "DK",
        "role": "EP-képviselő",
        "aliases": [
            "Dobrev", "Klára Dobrev", "Dobrev K.",
        ],
    },
    "Toroczkai László": {
        "party": "MI_HAZANK",
        "role": "Pártelnök",
        "aliases": [
            "Toroczkai", "László Toroczkai", "Toroczkai L.",
        ],
    },
    "Dúró Dóra": {
        "party": "MI_HAZANK",
        "role": "Alelnök",
        "aliases": [
            "Dúró", "Dóra Dúró", "Duro Dora",
        ],
    },
    "Kovács Gergely": {
        "party": "MKKP",
        "role": "Pártelnök",
        "aliases": [
            "Kovács G.", "Gergely Kovács",
        ],
    },
    "Jakab Péter": {
        "party": "JOBBIK",
        "role": "Volt pártelnök",
        "aliases": [
            "Jakab", "Péter Jakab", "Jakab P.",
        ],
    },
    "Tóth Bertalan": {
        "party": "MSZP",
        "role": "Társelnök",
        "aliases": [
            "Tóth B.", "Bertalan Tóth",
        ],
    },
    "Kocsis Máté": {
        "party": "FIDESZ",
        "role": "Frakcióvezető",
        "aliases": [
            "Kocsis", "Máté Kocsis", "Kocsis M.",
        ],
    },
    "Gulyás Gergely": {
        "party": "FIDESZ",
        "role": "Miniszterelnökséget vezető miniszter",
        "aliases": [
            "Gulyás", "Gergely Gulyás", "Gulyás G.",
        ],
    },
    "Szijjártó Péter": {
        "party": "FIDESZ",
        "role": "Külgazdasági és Külügyminiszter",
        "aliases": [
            "Szijjártó", "Péter Szijjártó", "Szijjarto Peter",
        ],
    },
    "Navracsics Tibor": {
        "party": "FIDESZ",
        "role": "Területfejlesztési miniszter",
        "aliases": [
            "Navracsics", "Tibor Navracsics",
        ],
    },
    "Sulyok Tamás": {
        "party": None,
        "role": "Köztársasági elnök",
        "aliases": [
            "Sulyok", "köztársasági elnök", "az államfő",
        ],
    },
    "Kövér László": {
        "party": "FIDESZ",
        "role": "Házelnök",
        "aliases": [
            "Kövér", "házelnök", "az Országgyűlés elnöke",
        ],
    },
}

# Party name normalization
PARTY_ALIASES: dict[str, str] = {
    "Fidesz": "FIDESZ",
    "FIDESZ": "FIDESZ",
    "Fidesz-KDNP": "FIDESZ",
    "KDNP": "FIDESZ",
    "Tisza": "TISZA",
    "Tisza Párt": "TISZA",
    "DK": "DK",
    "Demokratikus Koalíció": "DK",
    "Mi Hazánk": "MI_HAZANK",
    "Mi Hazánk Mozgalom": "MI_HAZANK",
    "MKKP": "MKKP",
    "Kétfarkú": "MKKP",
    "Magyar Kétfarkú Kutya Párt": "MKKP",
    "Jobbik": "JOBBIK",
    "JOBBIK": "JOBBIK",
    "MSZP": "MSZP",
    "Szocialista": "MSZP",
    "Magyar Szocialista Párt": "MSZP",
    "LMP": "LMP",
    "Momentum": "MOMENTUM",
    "Párbeszéd": "PARBESZED",
}


def resolve_politician(name: str) -> ResolvedEntity:
    """Resolve a speaker name to a known politician.

    Args:
        name: Raw speaker name from text extraction.

    Returns:
        ResolvedEntity with canonical name and party.
    """
    if not name or not name.strip():
        return ResolvedEntity(
            canonical_name=name or "Unknown",
            party_shortname=None,
            role=None,
            confidence=0.0,
            match_type="unknown",
        )

    name_clean = name.strip()

    # Exact match on canonical name
    if name_clean in KNOWN_POLITICIANS:
        info = KNOWN_POLITICIANS[name_clean]
        return ResolvedEntity(
            canonical_name=name_clean,
            party_shortname=info["party"],
            role=info["role"],
            confidence=1.0,
            match_type="exact",
        )

    # Alias match
    name_lower = name_clean.lower()
    for canonical, info in KNOWN_POLITICIANS.items():
        for alias in info["aliases"]:
            if alias.lower() == name_lower:
                return ResolvedEntity(
                    canonical_name=canonical,
                    party_shortname=info["party"],
                    role=info["role"],
                    confidence=0.95,
                    match_type="alias",
                )

    # Fuzzy match: check if name contains a known last name
    for canonical, info in KNOWN_POLITICIANS.items():
        last_name = canonical.split()[0]
        if last_name.lower() in name_lower and len(last_name) > 3:
            return ResolvedEntity(
                canonical_name=canonical,
                party_shortname=info["party"],
                role=info["role"],
                confidence=0.7,
                match_type="fuzzy",
            )

    # Unknown politician
    return ResolvedEntity(
        canonical_name=name_clean,
        party_shortname=None,
        role=None,
        confidence=0.3,
        match_type="unknown",
    )


def resolve_party(party_text: str) -> str | None:
    """Resolve a party name/alias to standard shortname.

    Args:
        party_text: Raw party name from extraction.

    Returns:
        Standard party shortname or None.
    """
    if not party_text:
        return None

    party_clean = party_text.strip()

    # Direct alias lookup
    if party_clean in PARTY_ALIASES:
        return PARTY_ALIASES[party_clean]

    # Case-insensitive search
    party_lower = party_clean.lower()
    for alias, shortname in PARTY_ALIASES.items():
        if alias.lower() == party_lower:
            return shortname

    # Partial match
    for alias, shortname in PARTY_ALIASES.items():
        if alias.lower() in party_lower or party_lower in alias.lower():
            return shortname

    logger.debug("Unknown party", party_text=party_text)
    return None


def normalize_hungarian_name(name: str) -> str:
    """Normalize a Hungarian name (handle accents, ordering).

    Hungarian names are typically LastName FirstName.
    This function ensures consistent formatting.
    """
    # Remove extra whitespace
    name = re.sub(r"\s+", " ", name.strip())

    # Remove common prefixes/suffixes
    prefixes = ["dr.", "Dr.", "DR.", "ifj.", "id.", "özv."]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()

    return name
