from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Self, TypedDict

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery
from weaviate.collections.classes.batch import ErrorObject
from weaviate.collections.collection.async_ import CollectionAsync

from em_backend.config import settings


class DocumentChunk(TypedDict):
    title: str
    text: str
    score: str


class VectorDatabase:
    """Interface to the Weaviate Database."""

    collection_prefix = "document_"

    __create_key = object()

    def __init__(
        self,
        key: Any,
        sync_client: weaviate.WeaviateClient,
        async_client: weaviate.WeaviateAsyncClient,
    ) -> None:
        if key != self.__create_key:
            raise ValueError(
                "Please create the vector database with the `create` generator."
            )
        self.sync_client = sync_client
        self.async_client = async_client

    @asynccontextmanager
    @classmethod
    async def create(cls) -> AsyncGenerator[Self]:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.wv_url,
            auth_credentials=Auth.api_key(settings.wv_api_key),
        )
        async_client = weaviate.use_async_with_weaviate_cloud(
            cluster_url=settings.wv_url,
            auth_credentials=Auth.api_key(settings.wv_api_key),
        )
        if not (client.is_ready() and await async_client.is_ready()):
            raise ConnectionError("Could not connect to weaviate vector database.")
        yield cls(cls.__create_key, client, async_client)
        client.close()
        await async_client.close()

    async def create_country_pdf_collection(self, country_code: str) -> CollectionAsync:
        async with self.async_client:
            return await self.async_client.collections.create(
                name=self.collection_prefix + country_code,
                vector_config=Configure.Vectors.text2vec_openai(),
                generative_config=Configure.Generative.openai(),
                properties=[
                    Property(name="text", data_type=DataType.TEXT),
                    Property(
                        name="title", data_type=DataType.TEXT, skip_vectorization=True
                    ),
                ],
            )

    def insert_chunk(
        self, country_code: str, chunks: list[tuple[str, str]]
    ) -> list[ErrorObject]:
        country_docs = self.sync_client.collections.use(
            self.collection_prefix + country_code
        )
        with country_docs.batch.dynamic() as batch:
            for title, text in chunks:
                batch.add_object({"text": text, "title": title})
                if batch.number_errors > 10:
                    break
        return country_docs.batch.failed_objects

    async def retrieve_chunks(
        self, country_code: str, query: str, *, limit=10
    ) -> list[DocumentChunk]:
        country_docs = self.async_client.collections.use(
            self.collection_prefix + country_code
        )
        async with self.async_client:
            response = await country_docs.query.hybrid(
                query,
                limit=limit,
                return_metadata=MetadataQuery(score=True),
            )
        return [
            DocumentChunk(
                title=o.properties["title"],  # pyright: ignore[reportArgumentType]
                text=o.properties["text"],  # pyright: ignore[reportArgumentType]
                score=o.metadata.score,  # pyright: ignore[reportArgumentType]
            )
            for o in response.objects
        ]
