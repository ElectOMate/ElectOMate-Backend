from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Self, TypedDict, TypeVar

from structlog.stdlib import get_logger

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter, MetadataQuery

from em_backend.core.config import settings
from em_backend.database.models import Document, Election, Party
from em_backend.models.enums import IndexingSuccess


class DocumentChunk(TypedDict, total=False):
    title: str
    text: str
    score: float
    chunk_id: str
    page_number: int | None
    chunk_index: int

T = TypeVar("T")


class VectorDatabase:
    """Interface to the Weaviate Database."""

    __create_key = object()

    def __init__(
        self,
        key: Any,  # noqa: ANN401
        sync_client: weaviate.WeaviateClient,
        async_client: weaviate.WeaviateAsyncClient,
    ) -> None:
        if key != self.__create_key:
            raise ValueError(
                "Please create the vector database with the `create` generator."
            )
        self.sync_client = sync_client
        self.async_client = async_client
        self.logger = get_logger(__name__)

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

    async def _execute_with_reconnect(self, action: Callable[[], Awaitable[T]]) -> T:
        try:
            return await action()
        except AssertionError:
            await self.async_client.connect()
            return await action()

    async def create_election_collection(self, election: Election) -> str:
        collection = await self._execute_with_reconnect(
            lambda: self.async_client.collections.create(
                name=election.wv_collection,
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
                        name="document",
                        data_type=DataType.UUID,
                        skip_vectorization=True,
                    ),
                    Property(
                        name="chunk_id",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                    ),
                    Property(
                        name="page_number",
                        data_type=DataType.INT,
                        skip_vectorization=True,
                    ),
                    Property(
                        name="chunk_index",
                        data_type=DataType.INT,
                        skip_vectorization=True,
                    ),
                ],
            )
        )
        return collection.name

    async def has_election_collection(self, election: Election) -> bool:
        return await self._execute_with_reconnect(
            lambda: self.async_client.collections.exists(election.wv_collection)
        )

    async def delete_collection(self, election: Election) -> None:
        await self._execute_with_reconnect(
            lambda: self.async_client.collections.delete(election.wv_collection)
        )

    def insert_chunks(
        self,
        election: Election,
        party: Party,
        document: Document,
        chunks: Generator[dict[str, Any], None, None],
    ) -> IndexingSuccess:
        country_docs = self.sync_client.collections.use(election.wv_collection)
        errors: list[dict[str, Any]] = []
        processed = 0
        with country_docs.batch.dynamic() as batch:
            for chunk in chunks:
                batch.add_object(
                    {
                        "text": chunk["text"],
                        "title": document.title,
                        "party": party.id,
                        "document": document.id,
                        "chunk_id": chunk["chunk_id"],
                        "page_number": chunk["page_number"],
                        "chunk_index": chunk["chunk_index"],
                    }
                )
                processed += 1
                if batch.number_errors:
                    errors.extend(country_docs.batch.failed_objects)
                if batch.number_errors > 50:
                    break
        if errors:
            self.logger.warning(
                "Chunk upload completed with errors",
                document_id=str(document.id),
                processed_chunks=processed,
                failed=len(errors),
            )
        else:
            self.logger.info(
                "Chunk upload completed",
                document_id=str(document.id),
                processed_chunks=processed,
            )

        if len(errors) > 50:
            return IndexingSuccess.FAILED
        if len(errors) > 1:
            return IndexingSuccess.PARTIAL_SUCESS
        else:
            return IndexingSuccess.SUCCESS

    async def retrieve_chunks(
        self,
        election: Election,
        party: Party,
        query: str,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DocumentChunk]:
        election_docs = self.async_client.collections.use(election.wv_collection)
        response = await self._execute_with_reconnect(
            lambda: election_docs.query.hybrid(
                query,
                filters=Filter.by_property("party").equal(party.id),
                return_metadata=MetadataQuery(score=True),
                limit=limit,
                offset=offset,
            )
        )
        documents: list[DocumentChunk] = []
        for obj in response.objects:
            properties = obj.properties  # pyright: ignore[reportAttributeAccessIssue]
            documents.append(
                DocumentChunk(
                    title=properties["title"],
                    text=properties["text"],
                    score=obj.metadata.score,
                    chunk_id=properties.get("chunk_id"),
                    page_number=properties.get("page_number"),
                    chunk_index=properties.get("chunk_index"),
                )
            )
        return documents

    async def delete_chunks(self, election: Election, document: Document) -> None:
        election_docs = self.async_client.collections.use(election.wv_collection)
        await self._execute_with_reconnect(
            lambda: election_docs.data.delete_many(
                where=Filter.by_property("document").equal(document.id)
            )
        )
