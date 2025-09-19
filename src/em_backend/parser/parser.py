from io import BytesIO
import logging
from docling_core.types.doc.document import DoclingDocument
import torch
from fastapi import UploadFile
from docling.document_converter import DocumentConverter
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

    async def convert_documents(self, docs: list[UploadFile]) -> list[DoclingDocument]:
        document_streams = [DocumentStream(name=doc.filename or 'file.pdf', stream=BytesIO(await doc.read())) for doc in docs]
        conv_results_iter = self.doc_converter.convert_all(document_streams)
        return [result.document for result in conv_results_iter]