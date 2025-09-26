import logging
from collections.abc import Generator
from io import BytesIO

import tiktoken
from docling.datamodel.base_models import ConfidenceReport
from docling.document_converter import DocumentConverter
from docling.utils.model_downloader import download_models
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.io import DocumentStream

from em_backend.core.config import settings

logger = logging.getLogger("em_parser")


class DocumentParser:
    """Parse PDF files."""

    def __init__(self) -> None:
        # Pre download models
        download_models(progress=True)

        # Setup Document converter
        self.doc_converter = DocumentConverter()

        # Setup Document chunker
        self.tokenizer = OpenAITokenizer(
            tokenizer=tiktoken.encoding_for_model(settings.openai_model_name),
            max_tokens=128 * 1024,
        )
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
        )

    def parse_document(
        self,
        filename: str,
        file: BytesIO,
    ) -> tuple[DoclingDocument, ConfidenceReport]:
        result = self.doc_converter.convert(DocumentStream(name=filename, stream=file))
        return result.document, result.confidence

    def serialize_document(self, doc: DoclingDocument) -> str:
        serializer = MarkdownDocSerializer(doc=doc)
        ser_result = serializer.serialize()
        return ser_result.text

    def chunk_document(self, doc: DoclingDocument) -> Generator[str]:
        for chunk in self.chunker.chunk(doc):
            yield self.chunker.contextualize(chunk)
