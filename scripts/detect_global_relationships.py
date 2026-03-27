"""Detect SUPPORTS/REBUTS/CONTRADICTS/EQUIVALENT relationships globally.

Pre-filters argument pairs by embedding cosine similarity (> 0.5),
then classifies via GPT-4o with graph-structural context features.

Usage: OPENAI_API_KEY=... AGE_POSTGRES_URL=... python scripts/detect_global_relationships.py
"""

import json
import os
import sys
import time
from collections import defaultdict

import psycopg2
from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)
GRAPH = "hungarian_politics"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_KEY:
    # Try .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("OPENAI_API_KEY="):
                OPENAI_KEY = line.split("=", 1)[1].strip()


def load_arguments_with_embeddings():
    """Load all arguments with their embeddings and metadata from pgvector."""
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT argument_id, argument_text, party, topics, speaker, embedding
        FROM argument_embeddings
        ORDER BY id
    """)
    args = []
    for row in cur.fetchall():
        args.append({
            "id": row[0],
            "text": row[1],
            "party": row[2],
            "topics": row[3] or [],
            "speaker": row[4],
            "embedding": row[5],  # pgvector returns as string
        })
    conn.close()
    return args


def find_candidate_pairs(args, min_cosine=0.45, max_pairs=5000):
    """Pre-filter pairs using pgvector cosine similarity."""
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    pairs = []
    seen = set()

    for i, arg in enumerate(args):
        if i % 100 == 0:
            print(f"  Pre-filtering: {i}/{len(args)} arguments...")

        # Find top 30 most similar to this argument
        cur.execute(f"""
            SELECT argument_id, argument_text, party, topics,
                   1 - (embedding <=> '{arg["embedding"]}'::vector) as sim
            FROM argument_embeddings
            WHERE argument_id != %s
            ORDER BY embedding <=> '{arg["embedding"]}'::vector
            LIMIT 30
        """, (arg["id"],))

        for row in cur.fetchall():
            other_id = row[0]
            sim = float(row[4])

            if sim < min_cosine:
                continue

            # Deduplicate: (A,B) == (B,A)
            pair_key = tuple(sorted([arg["id"], other_id]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            other_topics = row[3] or []
            arg_topics = arg["topics"] or []

            # Require shared topic OR high similarity
            shared_topics = set(arg_topics) & set(other_topics) if arg_topics and other_topics else set()
            if sim < 0.6 and not shared_topics:
                continue

            pairs.append({
                "a_id": arg["id"],
                "a_text": arg["text"],
                "a_party": arg["party"],
                "a_topics": arg_topics,
                "b_id": other_id,
                "b_text": row[1],
                "b_party": row[2],
                "b_topics": other_topics,
                "cosine": sim,
                "shared_topics": list(shared_topics),
            })

            if len(pairs) >= max_pairs:
                conn.close()
                return pairs

    conn.close()
    return pairs


CLASSIFY_PROMPT_TEMPLATE = """Classify the relationship between these Hungarian political argument pairs.

For each pair, determine:
- SUPPORTS: A provides evidence or reasoning that strengthens B
- REBUTS: A directly counters or argues against B
- CONTRADICTS: A and B make incompatible claims on the same issue
- EQUIVALENT: A and B express the same idea in different words
- UNRELATED: No meaningful argumentative connection

Consider the graph context:
- Same party arguments are more likely to SUPPORT each other
- Cross-party arguments on the same topic are more likely to CONTRADICT
- Very high cosine similarity (>0.85) suggests EQUIVALENT

Return JSON: {{"results": [{{"pair": 1, "relation": "...", "confidence": 0.0-1.0, "reasoning": "..."}}]}}

PAIRS:
"""


def classify_batch(pairs, oai, batch_size=5):
    """Classify a batch of argument pairs using GPT-4o."""
    pairs_text = ""
    for i, p in enumerate(pairs, 1):
        same_party = "Yes" if p["a_party"] == p["b_party"] and p["a_party"] else "No"
        pairs_text += f"""
Pair {i}:
A [{p['a_party'] or '?'}]: "{p['a_text'][:200]}"
B [{p['b_party'] or '?'}]: "{p['b_text'][:200]}"
Context: Same party={same_party}, Shared topics={p['shared_topics']}, Cosine={p['cosine']:.2f}
"""

    try:
        resp = oai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": CLASSIFY_PROMPT_TEMPLATE + pairs_text}],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)

        # Extract list of results from various formats
        items = []
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            # Try known wrapper keys
            for key in ("results", "pairs", "classifications", "data"):
                val = parsed.get(key)
                if isinstance(val, list):
                    items = val
                    break
            else:
                # Single result dict with "relation" key
                if "relation" in parsed:
                    items = [parsed]

        # Validate each item is a dict with "relation"
        valid = [it for it in items if isinstance(it, dict) and "relation" in it]
        return valid
    except Exception as e:
        import traceback
        print(f"    API error: {type(e).__name__}: {str(e)[:80]}")
        traceback.print_exc()
        return []


def insert_edges(pairs_with_relations, min_confidence=0.6):
    """Insert classified relationships into the AGE graph."""
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    inserted = 0
    by_type = defaultdict(int)

    for pair, result in pairs_with_relations:
        relation = result.get("relation", "UNRELATED")
        confidence = float(result.get("confidence", 0.5))

        if relation == "UNRELATED" or confidence < min_confidence:
            continue

        if relation not in ("SUPPORTS", "REBUTS", "CONTRADICTS", "EQUIVALENT"):
            continue

        a_text = pair["a_text"][:200].replace("'", "\\'")
        b_text = pair["b_text"][:200].replace("'", "\\'")
        reasoning = str(result.get("reasoning", "")).replace("'", "\\'")[:200]

        try:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute(f"""
                SELECT * FROM cypher('{GRAPH}', $$
                    MATCH (a:Argument) WHERE a.text STARTS WITH '{a_text}'
                    MATCH (b:Argument) WHERE b.text STARTS WITH '{b_text}'
                    MERGE (a)-[:{relation} {{confidence: {confidence}, reasoning: '{reasoning}'}}]->(b)
                    RETURN a
                $$) as (v agtype);
            """)
            conn.commit()
            inserted += 1
            by_type[relation] += 1
        except Exception:
            conn.rollback()

    conn.close()
    return inserted, dict(by_type)


def main():
    print("=" * 60)
    print("GLOBAL ARGUMENT RELATIONSHIP DETECTION")
    print("=" * 60)

    # Step 1: Load arguments
    print("\n1. Loading arguments with embeddings...")
    args = load_arguments_with_embeddings()
    print(f"   Loaded {len(args)} arguments")

    # Step 2: Pre-filter candidate pairs
    print("\n2. Pre-filtering candidate pairs (cosine > 0.45)...")
    t0 = time.time()
    pairs = find_candidate_pairs(args, min_cosine=0.6, max_pairs=500)
    print(f"   Found {len(pairs)} candidate pairs in {time.time()-t0:.1f}s")

    if not pairs:
        print("   No candidate pairs found. Exiting.")
        return

    # Show cosine distribution
    high = sum(1 for p in pairs if p["cosine"] > 0.8)
    med = sum(1 for p in pairs if 0.6 <= p["cosine"] <= 0.8)
    low = sum(1 for p in pairs if p["cosine"] < 0.6)
    print(f"   Distribution: {high} high (>0.8), {med} medium (0.6-0.8), {low} lower (<0.6)")

    # Step 3: Classify with GPT-4o
    print(f"\n3. Classifying {len(pairs)} pairs with GPT-4o...")
    oai = OpenAI(api_key=OPENAI_KEY)
    batch_size = 5

    all_results = []
    api_calls = 0

    for batch_start in range(0, len(pairs), batch_size):
        batch = pairs[batch_start:batch_start + batch_size]
        results = classify_batch(batch, oai, batch_size)
        api_calls += 1

        if not isinstance(results, list):
            results = [results] if results else []

        for i, result in enumerate(results):
            if not isinstance(result, dict):
                print(f"    Skipping non-dict result: {type(result)}: {repr(result)[:50]}")
                continue
            if i < len(batch):
                all_results.append((batch[i], result))

        if api_calls % 20 == 0:
            non_unrelated = sum(1 for _, r in all_results if r.get("relation") != "UNRELATED")
            print(f"   Progress: {batch_start+batch_size}/{len(pairs)} pairs, "
                  f"{non_unrelated} relationships found, {api_calls} API calls")

        # Rate limiting
        if api_calls % 50 == 0:
            time.sleep(1)

    # Stats
    relation_counts = defaultdict(int)
    for _, r in all_results:
        relation_counts[r.get("relation", "UNKNOWN")] += 1
    print(f"\n   Classification results:")
    for rel, count in sorted(relation_counts.items()):
        print(f"     {rel}: {count}")

    # Step 4: Insert edges
    print(f"\n4. Inserting edges into graph...")
    inserted, by_type = insert_edges(all_results, min_confidence=0.6)
    print(f"   Inserted {inserted} edges")
    for rel, count in by_type.items():
        print(f"     {rel}: {count}")

    # Step 5: Verify
    print(f"\n5. Verifying graph edges...")
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, '$user', public;")

    for rel in ["SUPPORTS", "REBUTS", "CONTRADICTS", "EQUIVALENT"]:
        cur.execute(f"""
            SELECT * FROM cypher('{GRAPH}', $$
                MATCH ()-[r:{rel}]->() RETURN count(r)
            $$) as (cnt agtype);
        """)
        print(f"   {rel}: {cur.fetchone()[0]}")
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"RELATIONSHIP DETECTION COMPLETE")
    print(f"  API calls: {api_calls}")
    print(f"  Edges inserted: {inserted}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
