# Party Shortname Mismatch — Known Issue

**Date discovered:** 2026-02-23
**Status:** Partially fixed — explicit mapping added. Watch for new parties.

---

## The Problem

The **Postgres `party_table`** stores party shortnames with umlauts and mixed case,
exactly as they appear in German:

| shortname (DB) | Weaviate chunk party field |
|---|---|
| `CDU` | `CDU` |
| `SPD` | `SPD` |
| `FDP` | `FDP` |
| `Grüne` | `Grüne` |
| `AfD` | `AfD` |
| `Linke` | `Linke` |

The **PDF proxy endpoint** (`GET /v2/documents/pdf/{party_key}`) and the
**manifesto key dicts** (`MANIFESTO_URLS`, `MANIFESTO_LOCAL_NAMES`) use
ASCII-normalised uppercase keys:

```
GRUNE, AFD, LINKE, CDU, SPD, FDP, BSW, VOLT, ...
```

### Why this breaks

```python
# Naive approach in the endpoint:
key = party_key.upper()

"Grüne".upper()  →  "GRÜNE"   # ü survives .upper()
MANIFESTO_LOCAL_NAMES.get("GRÜNE")  →  None  # key is "GRUNE", not "GRÜNE"
# Result: 404 — PDF panel silently fails for Grüne
```

The `ü` in `Grüne` uppercases to `Ü`, not `U`. Python's `.upper()` is
Unicode-aware, so it does the right Unicode thing — but that doesn't match
our ASCII-normalised keys.

Same risk for any future party with umlauts, ß, or other non-ASCII chars.

---

## The Fix Applied (2026-02-23)

Added `PARTY_SHORTNAME_TO_MANIFESTO_KEY` in
`src/em_backend/config/manifesto_urls.py`:

```python
PARTY_SHORTNAME_TO_MANIFESTO_KEY: dict[str, str] = {
    "CDU": "CDU",
    "SPD": "SPD",
    "Grüne": "GRUNE",
    "FDP": "FDP",
    "AfD": "AFD",
    "Linke": "LINKE",
    "BSW": "BSW",
    "VOLT": "VOLT",
    "BUENDNIS": "BUENDNIS",
    "FREIE": "FREIE",
    "MLPD": "MLPD",
}
```

The endpoint now does:
```python
key = PARTY_SHORTNAME_TO_MANIFESTO_KEY.get(party_key) or party_key.upper()
```

This means: try the explicit mapping first (handles umlauts exactly), then
fall back to `.upper()` for keys that are already ASCII-clean.

---

## Where It Could Still Break

### 1. New parties added to the DB

If someone seeds a new party with a shortname that has umlauts/special chars
(e.g., `Bündnis` for BSW, `Ökopartei`, etc.) and doesn't update
`PARTY_SHORTNAME_TO_MANIFESTO_KEY`, the PDF proxy will 404 for that party.

**Fix:** Always add new German parties to `PARTY_SHORTNAME_TO_MANIFESTO_KEY`
when seeding them.

### 2. Citation source `party` field in SSE

The chat backend sends the DB shortname directly in SSE events:
```
party_response_sources → chunk.party = "Grüne"  (DB shortname)
```

The frontend's `resolveCitationPdfUrl()` passes this to `getManifestoPdfUrl()`:
```typescript
getManifestoPdfUrl("Grüne")
// → GET /v2/documents/pdf/Grüne
// → backend normalises via PARTY_SHORTNAME_TO_MANIFESTO_KEY → "GRUNE" ✓
```

This chain now works correctly. But if the SSE ever starts sending manifesto
keys instead of DB shortnames (e.g. after a backend refactor), it would break.

### 3. Chile or other elections

The Chile parties use ASCII shortnames (`PC`, `REP`, `UDI`, etc.) so they're
unaffected. If future elections use non-ASCII shortnames, the same fix applies.

---

## Alternative Fix (Not Applied — For Reference)

Could normalise at the Python level using `unicodedata`:

```python
import unicodedata

def normalize_party_key(key: str) -> str:
    """NFD-decompose then strip combining diacritics, then uppercase."""
    nfd = unicodedata.normalize("NFD", key)
    ascii_only = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return ascii_only.upper()

normalize_party_key("Grüne")  # → "GRUNE" ✓
normalize_party_key("AfD")    # → "AFD" ✓
normalize_party_key("Linke")  # → "LINKE" ✓
```

This would handle any future umlaut case automatically without needing
to maintain the lookup table. Downside: less explicit, could produce
unexpected results for edge cases (e.g. `ß` → `SS` in some locales).

The explicit lookup table was chosen for clarity and safety.
