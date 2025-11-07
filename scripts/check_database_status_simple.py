#!/usr/bin/env python3
"""
Check database status - simple version using psycopg directly.
Check what documents are in PostgreSQL and Weaviate.
Shows upload status, chunks counts, and identifies failed uploads.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path / "src"))

import psycopg
from em_backend.core.config import settings

# Weaviate imports
try:
    import weaviate
    HAS_WEAVIATE = True
except ImportError:
    HAS_WEAVIATE = False
    print("⚠️  Warning: weaviate-client not installed. Weaviate checks will be skipped.")
    print("   Install with: pip install weaviate-client")


def check_postgresql():
    """Check PostgreSQL for all documents"""
    print("=" * 80)
    print("POSTGRESQL DATABASE")
    print("=" * 80)

    # Parse the URL to extract connection parameters
    # Format: postgresql+psycopg://user:pass@host:port/dbname
    url = settings.postgres_url.replace("postgresql+psycopg://", "")

    # For Docker, replace 'postgres' hostname with 'localhost'
    if "@postgres:" in url:
        url = url.replace("@postgres:", "@localhost:")

    conn_url = f"postgresql://{url}"

    try:
        with psycopg.connect(conn_url) as conn:
            with conn.cursor() as cur:
                # Get all documents with party info
                # First, get the election's weaviate collection name
                cur.execute("""
                    SELECT DISTINCT e.wv_collection
                    FROM document_table d
                    JOIN party_table p ON d.party_id = p.id
                    JOIN election_table e ON p.election_id = e.id
                    LIMIT 1
                """)
                wv_collection_result = cur.fetchone()
                wv_collection_name = wv_collection_result[0] if wv_collection_result else "DocumentChunk"

                # Get all documents with party info
                cur.execute("""
                    SELECT
                        d.id,
                        d.title,
                        d.type,
                        d.parsing_quality,
                        d.indexing_success,
                        d.created_at,
                        p.fullname as party_name,
                        p.id as party_id
                    FROM document_table d
                    JOIN party_table p ON d.party_id = p.id
                    ORDER BY p.fullname, d.title
                """)

                documents = cur.fetchall()

                if not documents:
                    print("❌ No documents found in database!")
                    return []

                print(f"\nTotal documents: {len(documents)}\n")

                doc_list = []
                for row in documents:
                    doc_id, title, doc_type, parsing_quality, indexing_success, created_at, party_name, party_id = row

                    # Map indexing_success enum to status icons
                    status_icon = {
                        "SUCCESS": "✅",
                        "SUCCESSFUL": "✅",
                        "FAILED": "❌",
                        "FAILURE": "❌",
                        "NO_INDEXING": "⏸️"
                    }.get(indexing_success, "❓")

                    print(f"{status_icon} {party_name[:30]:<30} | {title[:40]:<40}")
                    print(f"   ID: {doc_id}")
                    print(f"   Indexing Status: {indexing_success}")
                    print(f"   Parsing Quality: {parsing_quality}")
                    print(f"   Type: {doc_type}")
                    print(f"   Uploaded: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print()

                    doc_list.append({
                        "id": str(doc_id),
                        "title": title,
                        "party_name": party_name,
                        "indexing_success": indexing_success,
                        "parsing_quality": parsing_quality,
                        "party_id": str(party_id)
                    })

                # Summary by indexing status
                cur.execute("""
                    SELECT indexing_success, COUNT(*)
                    FROM document_table
                    GROUP BY indexing_success
                """)
                status_counts = dict(cur.fetchall())

                print("-" * 80)
                print("INDEXING STATUS SUMMARY:")
                for status, count in status_counts.items():
                    icon = {"SUCCESS": "✅", "SUCCESSFUL": "✅", "FAILED": "❌", "FAILURE": "❌", "NO_INDEXING": "⏸️"}.get(status, "❓")
                    print(f"  {icon} {status}: {count}")
                print()
                print(f"📦 Weaviate Collection: {wv_collection_name}")
                print()

                return doc_list, wv_collection_name

    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print(f"   URL: {conn_url}")
        return [], "DocumentChunk"


def check_weaviate(doc_list, collection_name="DocumentChunk"):
    """Check Weaviate for chunks"""
    if not HAS_WEAVIATE:
        return {}

    print("=" * 80)
    print("WEAVIATE VECTOR DATABASE")
    print("=" * 80)

    try:
        import weaviate.classes as wvc

        # Connect to Weaviate using v4 API
        # The URL needs to be in https:// format
        wv_url = settings.wv_url
        if not wv_url.startswith("http"):
            wv_url = f"https://{wv_url}"

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=wv_url,
            auth_credentials=wvc.init.Auth.api_key(settings.wv_api_key),
        )

        print(f"\n✅ Connected to Weaviate at {settings.wv_url}")
        print(f"📦 Using collection: {collection_name}\n")

        # Count chunks per document
        document_chunks = {}

        for doc in doc_list:
            doc_id = doc["id"]

            try:
                # Query Weaviate to count chunks for this document
                collection = client.collections.get(collection_name)

                # Use aggregation to count
                # Note: The property might be "document" or "document_id" depending on schema
                result = collection.aggregate.over_all(
                    filters=wvc.query.Filter.by_property("document").equal(doc_id),
                    total_count=True
                )

                count = result.total_count if result and result.total_count else 0
                document_chunks[doc_id] = count
                print(f"  {doc['party_name'][:30]:<30} | {doc['title'][:40]:<40} | {count:>5} chunks")

            except Exception as e:
                print(f"  ❌ Error querying chunks for {doc['title']}: {e}")
                document_chunks[doc_id] = -1

        print()
        print("-" * 80)
        print("WEAVIATE SUMMARY:")
        total_chunks = sum(c for c in document_chunks.values() if c > 0)
        docs_with_chunks = sum(1 for c in document_chunks.values() if c > 0)
        print(f"  Total chunks: {total_chunks}")
        print(f"  Documents with chunks: {docs_with_chunks}/{len(doc_list)}")
        print()

        client.close()
        return document_chunks

    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        print(f"   URL: {settings.wv_url}")
        return {}


def compare_status(doc_list, weaviate_chunks):
    """Compare PostgreSQL and Weaviate to find issues"""
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    issues = []

    for doc in doc_list:
        doc_id = doc["id"]
        indexing_status = doc["indexing_success"]
        chunk_count = weaviate_chunks.get(doc_id, -1)

        # Check for issues
        if indexing_status in ("SUCCESS", "SUCCESSFUL") and chunk_count == 0:
            print(f"❌ ISSUE: {doc['party_name']} - {doc['title']}")
            print(f"   Indexing status is '{indexing_status}' but 0 chunks in Weaviate!")
            print(f"   Document ID: {doc_id}")
            issues.append({**doc, "issue": "successful_but_no_chunks"})
            print()

        elif indexing_status in ("SUCCESS", "SUCCESSFUL") and chunk_count == -1:
            print(f"⚠️  WARNING: {doc['party_name']} - {doc['title']}")
            print(f"   Indexing status is '{indexing_status}' but couldn't verify Weaviate chunks")
            print(f"   Document ID: {doc_id}")
            issues.append({**doc, "issue": "successful_but_weaviate_error"})
            print()

        elif indexing_status in ("FAILED", "FAILURE"):
            print(f"❌ FAILED: {doc['party_name']} - {doc['title']}")
            print(f"   Indexing failed, chunks: {chunk_count}")
            print(f"   Document ID: {doc_id}")
            issues.append({**doc, "issue": "indexing_failed", "chunk_count": chunk_count})
            print()

        elif indexing_status == "NO_INDEXING":
            print(f"⏸️ NOT INDEXED: {doc['party_name']} - {doc['title']}")
            print(f"   Not yet indexed, chunks: {chunk_count}")
            print(f"   Document ID: {doc_id}")
            issues.append({**doc, "issue": "not_indexed", "chunk_count": chunk_count})
            print()

    if not issues:
        print("✅ No issues found! All documents appear to be correctly uploaded.")
    else:
        print("-" * 80)
        print(f"FOUND {len(issues)} ISSUE(S)")
        print()
        print("To fix these issues, you can:")
        print("1. Re-upload failed documents via the UI")
        print("2. Use the batch_reupload.py script (to be created)")
        print("3. Manually clean up and re-upload specific documents")

    print()


def main():
    """Main function"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + "DATABASE STATUS CHECK".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Check PostgreSQL
    doc_list, collection_name = check_postgresql()

    if not doc_list:
        print("\n⚠️  No documents found in PostgreSQL. Exiting.")
        return

    # Check Weaviate
    weaviate_chunks = check_weaviate(doc_list, collection_name)

    # Compare and find issues
    if weaviate_chunks:
        compare_status(doc_list, weaviate_chunks)
    else:
        print("⚠️  Skipping comparison - Weaviate data not available")


if __name__ == "__main__":
    main()
