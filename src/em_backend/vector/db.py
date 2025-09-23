from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Self, TypedDict
from uuid import UUID

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.collections.classes.batch import ErrorObject

from em_backend.config import settings


class DocumentChunk(TypedDict):
    title: str
    text: str
    score: float


class VectorDatabase:
    """Interface to the Weaviate Database."""

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

    @classmethod
    @asynccontextmanager
    async def create(cls) -> AsyncGenerator[Self]:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.wv_url,
            auth_credentials=Auth.api_key(settings.wv_api_key),
            headers={
                "X-OpenAI-Api-Key": settings.openai_api_key,
            },
        )
        async_client = weaviate.use_async_with_weaviate_cloud(
            cluster_url=settings.wv_url,
            auth_credentials=Auth.api_key(settings.wv_api_key),
            headers={
                "X-OpenAI-Api-Key": settings.openai_api_key,
            },
        )
        client.connect()
        await async_client.connect()
        if not (client.is_ready() and await async_client.is_ready()):
            raise ConnectionError("Could not connect to weaviate vector database.")
        yield cls(cls.__create_key, client, async_client)
        client.close()
        await async_client.close()

    async def create_election_document_collection(self, election_id: UUID) -> str:
        async with self.async_client:
            collection = await self.async_client.collections.create(
                name="D" + str(election_id).replace("_", "").replace("-", ""),
                vector_config=Configure.Vectors.text2vec_openai(),
                generative_config=Configure.Generative.openai(),
                properties=[
                    Property(name="text", data_type=DataType.TEXT),
                    Property(
                        name="title", data_type=DataType.TEXT, skip_vectorization=True
                    ),
                    Property(
                        name="party", data_type=DataType.UUID, skip_vectorization=True
                    ),
                    Property(
                        name="doc_id", data_type=DataType.UUID, skip_vectorization=True
                    ),
                ],
            )
            return collection.name

    async def delete_collection(self, election_id: UUID) -> None:
        async with self.async_client:
            await self.async_client.collections.delete(
                "D" + str(election_id).replace("_", "").replace("-", "")
            )

    def insert_chunks(
        self, election_id: UUID, party_id: UUID, chunks: list[tuple[str, str]]
    ) -> list[ErrorObject]:
        country_docs = self.sync_client.collections.use(
            "D" + str(election_id).replace("_", "").replace("-", "")
        )
        with country_docs.batch.dynamic() as batch:
            for title, text in chunks:
                batch.add_object({"text": text, "title": title, "party": party_id})
                if batch.number_errors > 10:
                    break
        return country_docs.batch.failed_objects

    async def retrieve_chunks(
        self, election_id: UUID, party_id: UUID, query: str, *, limit=10, offset=0
    ) -> list[DocumentChunk]:
        election_docs = self.async_client.collections.use(
            "D" + str(election_id).replace("_", "").replace("-", "")
        )
        async with self.async_client:
            response = await election_docs.query.hybrid(
                query,
                filters=Filter.by_property("party").equal(party_id),
                return_metadata=MetadataQuery(score=True),
                limit=limit,
                offset=offset,
            )
        return [
            DocumentChunk(
                title=o.properties["title"],  # pyright: ignore[reportArgumentType]
                text=o.properties["text"],  # pyright: ignore[reportArgumentType]
                score=o.metadata.score,  # pyright: ignore[reportArgumentType]
            )
            for o in response.objects
        ]

    async def delete_chunks(self, election_id: UUID, document_id: UUID) -> None:
        election_docs = self.async_client.collections.use(
            "D" + str(election_id).replace("_", "").replace("-", "")
        )
        async with self.async_client:
            await election_docs.data.delete_many(
                where=Filter.by_property("doc_id").equal(document_id)
            )
