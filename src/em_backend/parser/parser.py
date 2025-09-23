import logging
from io import BytesIO

import torch
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.io import DocumentStream

logger = logging.getLogger("em_parser")


class DocumentParser:
    """Parse PDF files."""

    def __init__(self) -> None:
        # Check if GPU or MPS is available
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            logger.info(f"CUDA GPU is enabled: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
            logger.info("MPS GPU is enabled.")
        else:
            self.device = None

        # Setup Document converter
        self.doc_converter = DocumentConverter()

        # Setup Document chunker
        self.chunker = HierarchicalChunker()

    async def parse_document(
        self,
        filename: str,
        file: BytesIO,
    ) -> DoclingDocument:
        result = self.doc_converter.convert(DocumentStream(name=filename, stream=file))
        return result.document

    def serialize_document(self, doc: DoclingDocument) -> str:
        serializer = MarkdownDocSerializer(doc=doc)
        ser_result = serializer.serialize()
        return ser_result.text

    def chunk_document(self, doc: DoclingDocument) -> list[tuple[str, str]]:
        texts: list[str] = []
        titles: list[str] = []

        # Chunk the documents
        chunks = list(self.chunker.chunk(doc))
        for chunk in chunks:
            texts.append(chunk.text)
            titles.append(doc.name)

        # Add title to every chunk
        for i in range(len(texts)):
            texts[i] = f"{titles[i]} {texts[i]}"

        return list(zip(titles, texts, strict=True))
