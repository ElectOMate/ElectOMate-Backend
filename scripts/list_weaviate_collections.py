#!/usr/bin/env python3
"""
List all collections in Weaviate to find the correct collection name.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path / "src"))

import weaviate
import weaviate.classes as wvc
from em_backend.core.config import settings


def list_collections():
    """List all collections in Weaviate"""
    try:
        # Connect to Weaviate using v4 API
        wv_url = settings.wv_url
        if not wv_url.startswith("http"):
            wv_url = f"https://{wv_url}"

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=wv_url,
            auth_credentials=wvc.init.Auth.api_key(settings.wv_api_key),
        )

        print("=" * 80)
        print("WEAVIATE COLLECTIONS")
        print("=" * 80)
        print(f"\nConnected to: {settings.wv_url}\n")

        # List all collections
        collections = client.collections.list_all()

        if not collections:
            print("❌ No collections found in Weaviate!")
        else:
            print(f"Found {len(collections)} collection(s):\n")
            for name, config in collections.items():
                print(f"  ✅ {name}")
                if config and hasattr(config, 'properties'):
                    print(f"     Properties: {[p.name for p in config.properties]}")
                print()

        client.close()

    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")


if __name__ == "__main__":
    list_collections()
