#!/usr/bin/env python3
"""
Check what documents are in PostgreSQL and Weaviate.
Shows upload status, chunks counts, and identifies failed uploads.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path / "src"))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from em_backend.database.models import Document, Party
from em_backend.core.config import settings

# Weaviate imports
try:
    import weaviate
    HAS_WEAVIATE = True
except ImportError:
    HAS_WEAVIATE = False
    print("⚠️  Warning: weaviate-client not installed. Weaviate checks will be skipped.")
    print("   Install with: pip install weaviate-client")


async def check_postgresql():
    """Check PostgreSQL for all documents"""
    print("=" * 80)
    print("POSTGRESQL DATABASE")
    print("=" * 80)

    # Create async engine and sessionmaker
    engine = create_async_engine(settings.postgres_url, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        # Get all documents with party info
        result = await db.execute(
            select(Document, Party)
            .join(Party, Document.party_id == Party.id)
            .order_by(Party.fullname, Document.title)
        )

        documents = result.all()

        if not documents:
            print("❌ No documents found in database!")
            await engine.dispose()
            return []

        print(f"\nTotal documents: {len(documents)}\n")

        doc_list = []
        for doc, party in documents:
            # Map indexing_success enum to status icons
            status_icon = {
                "SUCCESSFUL": "✅",
                "FAILED": "❌",
                "NO_INDEXING": "⏸️"
            }.get(doc.indexing_success.name, "❓")

            print(f"{status_icon} {party.fullname[:30]:<30} | {doc.title[:40]:<40}")
            print(f"   ID: {doc.id}")
            print(f"   Indexing Status: {doc.indexing_success.name}")
            print(f"   Parsing Quality: {doc.parsing_quality.name}")
            print(f"   Type: {doc.type.name}")
            print(f"   Uploaded: {doc.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            doc_list.append({
                "id": str(doc.id),
                "title": doc.title,
                "party_name": party.fullname,
                "indexing_success": doc.indexing_success.name,
                "parsing_quality": doc.parsing_quality.name,
                "party_id": str(doc.party_id)
            })

        # Summary by indexing status
        result = await db.execute(
            select(Document.indexing_success, func.count(Document.id))
            .group_by(Document.indexing_success)
        )
        status_counts = {status.name: count for status, count in result.all()}

        print("-" * 80)
        print("INDEXING STATUS SUMMARY:")
        for status, count in status_counts.items():
            icon = {"SUCCESSFUL": "✅", "FAILED": "❌", "NO_INDEXING": "⏸️"}.get(status, "❓")
            print(f"  {icon} {status}: {count}")
        print()

    await engine.dispose()
    return doc_list


def check_weaviate(doc_list):
    """Check Weaviate for chunks"""
    if not HAS_WEAVIATE:
        return {}

    print("=" * 80)
    print("WEAVIATE VECTOR DATABASE")
    print("=" * 80)

    try:
        # Connect to Weaviate
        client = weaviate.Client(
            url=settings.wv_url,
            timeout_config=(5, 15)
        )

        # Check if schema exists
        schema = client.schema.get()
        if not schema or "classes" not in schema:
            print("⚠️  No schema found in Weaviate")
            return {}

        # Find DocumentChunk class
        chunk_class = None
        for cls in schema["classes"]:
            if cls["class"] == "DocumentChunk":
                chunk_class = cls
                break

        if not chunk_class:
            print("⚠️  DocumentChunk class not found in Weaviate schema")
            return {}

        print(f"\n✅ Connected to Weaviate at {settings.wv_url}\n")

        # Count chunks per document
        document_chunks = {}

        for doc in doc_list:
            doc_id = doc["id"]

            # Query chunks for this document
            try:
                result = client.query.aggregate("DocumentChunk") \
                    .with_where({
                        "path": ["document_id"],
                        "operator": "Equal",
                        "valueText": doc_id
                    }) \
                    .with_fields("meta { count }") \
                    .do()

                count = 0
                if result.get("data", {}).get("Aggregate", {}).get("DocumentChunk"):
                    agg = result["data"]["Aggregate"]["DocumentChunk"][0]
                    count = agg.get("meta", {}).get("count", 0)

                document_chunks[doc_id] = count

                if count > 0:
                    print(f"✅ {doc['party_name'][:30]:<30} | {count:>4} chunks | {doc['filename'][:40]}")
                else:
                    print(f"❌ {doc['party_name'][:30]:<30} | {count:>4} chunks | {doc['filename'][:40]}")

            except Exception as e:
                print(f"⚠️  Error querying chunks for {doc['filename']}: {e}")
                document_chunks[doc_id] = -1

        # Total chunks
        try:
            total_result = client.query.aggregate("DocumentChunk") \
                .with_fields("meta { count }") \
                .do()

            total_chunks = 0
            if total_result.get("data", {}).get("Aggregate", {}).get("DocumentChunk"):
                agg = total_result["data"]["Aggregate"]["DocumentChunk"][0]
                total_chunks = agg.get("meta", {}).get("count", 0)

            print()
            print("-" * 80)
            print(f"TOTAL CHUNKS IN WEAVIATE: {total_chunks}")
            print()
        except Exception as e:
            print(f"⚠️  Error getting total chunk count: {e}")

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
        if indexing_status == "SUCCESSFUL" and chunk_count == 0:
            print(f"❌ ISSUE: {doc['party_name']} - {doc['title']}")
            print(f"   Indexing status is 'SUCCESSFUL' but 0 chunks in Weaviate!")
            print(f"   Document ID: {doc_id}")
            issues.append({**doc, "issue": "successful_but_no_chunks"})
            print()

        elif indexing_status == "SUCCESSFUL" and chunk_count == -1:
            print(f"⚠️  WARNING: {doc['party_name']} - {doc['title']}")
            print(f"   Indexing status is 'SUCCESSFUL' but couldn't verify Weaviate chunks")
            print(f"   Document ID: {doc_id}")
            issues.append({**doc, "issue": "successful_but_weaviate_error"})
            print()

        elif indexing_status == "FAILED":
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
    return issues


async def main():
    """Main function"""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " DATABASE STATUS CHECK ".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Check PostgreSQL
    doc_list = await check_postgresql()

    if not doc_list:
        print("No documents to check. Exiting.")
        return

    print()

    # Check Weaviate
    weaviate_chunks = check_weaviate(doc_list)

    print()

    # Compare and find issues
    if weaviate_chunks:
        issues = compare_status(doc_list, weaviate_chunks)

        # Return exit code based on issues
        if issues:
            sys.exit(1)
    else:
        print("⚠️  Skipping comparison - Weaviate data not available")

    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
