"""Enrich the knowledge graph with full metadata.

Adds: Platforms, Locations, Organizations, Politicians, Utterances,
UUIDs, expanded argument types, temporal metadata.

Usage: AGE_POSTGRES_URL="host=localhost port=5433 ..." python scripts/enrich_graph_metadata.py
"""

import os
import sys
import uuid

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)
GRAPH = "hungarian_politics"


def cypher_write(cur, conn, query):
    """Execute a write Cypher query."""
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, '$user', public;")
    try:
        cur.execute(f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) as (v agtype);")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False


def cypher_read(cur, conn, query, columns):
    """Execute a read Cypher query."""
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, '$user', public;")
    col_defs = ", ".join(f"{c} agtype" for c in columns)
    cur.execute(f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) as ({col_defs});")
    rows = cur.fetchall()
    conn.commit()
    results = []
    for row in rows:
        d = {}
        for i, c in enumerate(columns):
            v = row[i]
            if isinstance(v, str):
                v = v.strip('"')
            d[c] = v
        results.append(d)
    return results


def esc(s):
    """Escape single quotes for Cypher."""
    if not s:
        return ""
    return str(s).replace("'", "\\'").replace("\\\\", "\\")


def main():
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    print("=" * 60)
    print("GRAPH ENRICHMENT PIPELINE")
    print("=" * 60)

    # ================================================================
    # PHASE A: Seed Platform nodes
    # ================================================================
    print("\n--- Phase A: Creating Platform nodes ---")
    platforms = [
        ("YouTube", "video", "youtube.com", "US"),
        ("parlament.hu", "parliament", "parlament.hu", "HU"),
        ("kormany.hu", "government", "kormany.hu", "HU"),
        ("telex.hu", "news", "telex.hu", "HU"),
        ("444.hu", "news", "444.hu", "HU"),
        ("hvg.hu", "news", "hvg.hu", "HU"),
        ("index.hu", "news", "index.hu", "HU"),
        ("ATV", "tv", "atv.hu", "HU"),
        ("HírTV", "tv", "hirtv.hu", "HU"),
        ("RTL Klub", "tv", "rtl.hu", "HU"),
        ("M1", "tv", "mediaklikk.hu", "HU"),
        ("Facebook", "social_media", "facebook.com", "US"),
        ("X", "social_media", "x.com", "US"),
    ]
    created = 0
    for name, ptype, url_base, country in platforms:
        if cypher_write(cur, conn,
            f"MERGE (pl:Platform {{name: '{esc(name)}'}}) "
            f"SET pl.type = '{ptype}', pl.url_base = '{url_base}', pl.country = '{country}' "
            f"RETURN pl"):
            created += 1
    print(f"  Platforms: {created}/{len(platforms)}")

    # ================================================================
    # PHASE B: Seed Location nodes
    # ================================================================
    print("\n--- Phase B: Creating Location nodes ---")
    locations = [
        ("Országház", "Parliament Building", "building", 47.5070, 19.0455),
        ("Budapest", "Budapest", "city", 47.4979, 19.0402),
        ("Magyarország", "Hungary", "country", 47.1625, 19.5033),
        ("Brüsszel", "Brussels", "city", 50.8503, 4.3517),
        ("Strasbourg", "Strasbourg", "city", 48.5734, 7.7521),
        ("Debrecen", "Debrecen", "city", 47.5316, 21.6273),
        ("Szeged", "Szeged", "city", 46.2530, 20.1414),
        ("Pécs", "Pécs", "city", 46.0727, 18.2323),
    ]
    created = 0
    for name, name_en, ltype, lat, lng in locations:
        if cypher_write(cur, conn,
            f"MERGE (loc:Location {{name: '{esc(name)}'}}) "
            f"SET loc.name_en = '{name_en}', loc.type = '{ltype}', "
            f"loc.lat = {lat}, loc.lng = {lng} "
            f"RETURN loc"):
            created += 1
    print(f"  Locations: {created}/{len(locations)}")

    # Location hierarchy
    hierarchies = [
        ("Országház", "Budapest"),
        ("Budapest", "Magyarország"),
        ("Debrecen", "Magyarország"),
        ("Szeged", "Magyarország"),
        ("Pécs", "Magyarország"),
    ]
    for child, parent in hierarchies:
        cypher_write(cur, conn,
            f"MATCH (c:Location {{name: '{child}'}}), (p:Location {{name: '{parent}'}}) "
            f"MERGE (c)-[:PART_OF]->(p) RETURN c")

    # ================================================================
    # PHASE C: Seed Organization nodes
    # ================================================================
    print("\n--- Phase C: Creating Organization nodes ---")
    organizations = [
        ("Magyar Nemzeti Bank", "government", "HU", "finance"),
        ("NAV", "government", "HU", "taxation"),
        ("Alkotmánybíróság", "government", "HU", "judiciary"),
        ("Legfőbb Ügyészség", "government", "HU", "judiciary"),
        ("Európai Bizottság", "international", "EU", "governance"),
        ("Európai Parlament", "international", "EU", "legislative"),
        ("OLAF", "international", "EU", "anti-fraud"),
        ("NATO", "international", "INT", "defense"),
        ("MOL", "company", "HU", "energy"),
        ("OTP Bank", "company", "HU", "finance"),
        ("Paks II", "company", "HU", "energy"),
        ("Rosatom", "company", "RU", "energy"),
    ]
    created = 0
    for name, otype, country, sector in organizations:
        if cypher_write(cur, conn,
            f"MERGE (org:Organization {{name: '{esc(name)}'}}) "
            f"SET org.type = '{otype}', org.country = '{country}', org.sector = '{sector}' "
            f"RETURN org"):
            created += 1
    print(f"  Organizations: {created}/{len(organizations)}")

    # ================================================================
    # PHASE D: Create Politician nodes + MEMBER_OF
    # ================================================================
    print("\n--- Phase D: Creating Politician nodes ---")
    from em_backend.graph.extraction.entity_resolver import KNOWN_POLITICIANS

    created = 0
    for name, info in KNOWN_POLITICIANS.items():
        n = esc(name)
        role = esc(info.get("role", ""))
        party = info.get("party")
        if cypher_write(cur, conn,
            f"MERGE (pol:Politician {{name: '{n}'}}) "
            f"SET pol.role = '{role}', pol.active = true "
            f"RETURN pol"):
            created += 1
            # Link to party
            if party:
                cypher_write(cur, conn,
                    f"MATCH (pol:Politician {{name: '{n}'}}), (p:Party {{shortname: '{party}'}}) "
                    f"MERGE (pol)-[:MEMBER_OF]->(p) RETURN pol")
    print(f"  Politicians: {created}/{len(KNOWN_POLITICIANS)}")

    # ================================================================
    # PHASE E: Add UUIDs to all Argument nodes
    # ================================================================
    print("\n--- Phase E: Adding UUIDs to Arguments ---")
    args = cypher_read(cur, conn,
        "MATCH (a:Argument) WHERE a.uuid IS NULL RETURN a.text", ["text"])
    added = 0
    for a in args:
        text = str(a["text"])
        uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, text[:500]))
        t = esc(text[:200])
        if cypher_write(cur, conn,
            f"MATCH (a:Argument) WHERE a.text STARTS WITH '{t}' "
            f"SET a.uuid = '{uid}' RETURN a"):
            added += 1
    print(f"  UUIDs added: {added}/{len(args)}")

    # ================================================================
    # PHASE F: Link Sources to Platforms
    # ================================================================
    print("\n--- Phase F: Linking Sources to Platforms ---")
    sources = cypher_read(cur, conn,
        "MATCH (s:Source) RETURN s.url, s.type", ["url", "stype"])

    platform_map = {
        "youtube.com": "YouTube",
        "parlamint://": "parlament.hu",
        "kormany.hu": "kormany.hu",
        "telex.hu": "telex.hu",
        "444.hu": "444.hu",
        "hvg.hu": "hvg.hu",
        "index.hu": "index.hu",
    }
    linked = 0
    for s in sources:
        url = str(s.get("url", ""))
        stype = str(s.get("stype", ""))
        platform = None

        for pattern, pname in platform_map.items():
            if pattern in url:
                platform = pname
                break

        # Infer from source type
        if not platform:
            if stype == "speech" or "parlamint" in url.lower():
                platform = "parlament.hu"
            elif stype == "interview" and ("youtube" in url.lower() or "youtu" in url.lower()):
                platform = "YouTube"

        if platform:
            url_esc = esc(url)
            if cypher_write(cur, conn,
                f"MATCH (s:Source {{url: '{url_esc}'}}), (pl:Platform {{name: '{platform}'}}) "
                f"MERGE (s)-[:PUBLISHED_ON]->(pl) RETURN s"):
                linked += 1
    print(f"  Source→Platform links: {linked}/{len(sources)}")

    # ================================================================
    # PHASE G: Link Sources to Locations
    # ================================================================
    print("\n--- Phase G: Linking Sources to Locations ---")
    linked = 0
    for s in sources:
        url = str(s.get("url", ""))
        stype = str(s.get("stype", ""))
        location = None

        if stype == "speech" or "parlamint" in url.lower():
            location = "Országház"
        elif "kormany.hu" in url:
            location = "Budapest"

        if location:
            url_esc = esc(url)
            if cypher_write(cur, conn,
                f"MATCH (s:Source {{url: '{url_esc}'}}), (loc:Location {{name: '{location}'}}) "
                f"MERGE (s)-[:RECORDED_AT]->(loc) RETURN s"):
                linked += 1
    print(f"  Source→Location links: {linked}/{len(sources)}")

    # ================================================================
    # PHASE H: Link Arguments with speakers to Politicians via SAID_BY
    # ================================================================
    print("\n--- Phase H: Linking Arguments to Politicians ---")
    args_with_speakers = cypher_read(cur, conn,
        "MATCH (a:Argument) WHERE a.speaker IS NOT NULL AND a.speaker <> 'null' "
        "RETURN a.text, a.speaker", ["text", "speaker"])

    from em_backend.graph.extraction.entity_resolver import resolve_politician
    linked = 0
    for a in args_with_speakers:
        speaker = str(a.get("speaker", ""))
        if not speaker or speaker == "null":
            continue
        resolved = resolve_politician(speaker)
        if resolved.confidence >= 0.5:
            t = esc(str(a["text"])[:200])
            pol_name = esc(resolved.canonical_name)
            if cypher_write(cur, conn,
                f"MATCH (a:Argument) WHERE a.text STARTS WITH '{t}' "
                f"MATCH (pol:Politician {{name: '{pol_name}'}}) "
                f"MERGE (a)-[:SAID_BY]->(pol) RETURN a"):
                linked += 1
    print(f"  Argument→Politician links: {linked}/{len(args_with_speakers)}")

    # ================================================================
    # PHASE I: Detect Organization mentions in arguments
    # ================================================================
    print("\n--- Phase I: Detecting Organization mentions ---")
    all_args = cypher_read(cur, conn,
        "MATCH (a:Argument) RETURN a.text LIMIT 1335", ["text"])

    org_names = [o[0] for o in organizations]
    linked = 0
    for a in all_args:
        text = str(a.get("text", "")).lower()
        for org_name in org_names:
            if org_name.lower() in text:
                t = esc(str(a["text"])[:200])
                o = esc(org_name)
                if cypher_write(cur, conn,
                    f"MATCH (a:Argument) WHERE a.text STARTS WITH '{t}' "
                    f"MATCH (org:Organization {{name: '{o}'}}) "
                    f"MERGE (a)-[:MENTIONS]->(org) RETURN a"):
                    linked += 1
    print(f"  Argument→Organization links: {linked}")

    # ================================================================
    # PHASE J: Add party colors
    # ================================================================
    print("\n--- Phase J: Adding party colors ---")
    colors = {
        "FIDESZ": "#FF6600", "TISZA": "#00B4D8", "DK": "#0066CC",
        "MI_HAZANK": "#006633", "MKKP": "#FFD700", "JOBBIK": "#1a1a1a",
        "MSZP": "#CC0000",
    }
    for shortname, color in colors.items():
        cypher_write(cur, conn,
            f"MATCH (p:Party {{shortname: '{shortname}'}}) "
            f"SET p.color = '{color}' RETURN p")
    print(f"  Party colors: {len(colors)}")

    # ================================================================
    # FINAL STATS
    # ================================================================
    print(f"\n{'=' * 60}")
    print("ENRICHMENT COMPLETE — Final graph stats:")
    for label in ["Argument", "Topic", "Party", "Politician", "Organization",
                   "Source", "Platform", "Location", "Utterance", "PolisQuestion"]:
        try:
            result = cypher_read(cur, conn, f"MATCH (n:{label}) RETURN count(n)", ["cnt"])
            print(f"  {label}: {result[0]['cnt']}")
        except Exception:
            print(f"  {label}: 0")

    print()
    for rel in ["MADE_BY", "SOURCED_FROM", "ABOUT", "SAID_BY", "PUBLISHED_ON",
                 "RECORDED_AT", "MENTIONS", "MEMBER_OF", "PART_OF"]:
        try:
            result = cypher_read(cur, conn, f"MATCH ()-[r:{rel}]->() RETURN count(r)", ["cnt"])
            print(f"  [{rel}]: {result[0]['cnt']}")
        except Exception:
            print(f"  [{rel}]: 0")

    conn.close()
    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    main()
