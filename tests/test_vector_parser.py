import os
import sys
import types
from types import SimpleNamespace


def _ensure_module(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    sys.modules[name] = module
    parent, _, child = name.rpartition(".")
    if parent:
        parent_module = _ensure_module(parent)
        setattr(parent_module, child, module)
    return module


docling_base_models = _ensure_module("docling.datamodel.base_models")
docling_pipeline_options = _ensure_module("docling.datamodel.pipeline_options")
docling_document_converter = _ensure_module("docling.document_converter")
docling_core_hybrid = _ensure_module(
    "docling_core.transforms.chunker.hybrid_chunker"
)
docling_core_tokenizer = _ensure_module(
    "docling_core.transforms.chunker.tokenizer.openai"
)
docling_core_serializer = _ensure_module(
    "docling_core.transforms.serializer.markdown"
)
docling_core_doc = _ensure_module("docling_core.types.doc.document")
docling_core_io = _ensure_module("docling_core.types.io")

docling_base_models.ConfidenceReport = getattr(
    docling_base_models,
    "ConfidenceReport",
    type("ConfidenceReport", (), {}),
)
docling_base_models.InputFormat = getattr(
    docling_base_models,
    "InputFormat",
    type("InputFormat", (), {"PDF": "PDF"}),
)


class _PdfPipelineOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _PdfFormatOption:
    def __init__(self, pipeline_options=None):
        self.pipeline_options = pipeline_options


docling_pipeline_options.PdfPipelineOptions = getattr(
    docling_pipeline_options,
    "PdfPipelineOptions",
    _PdfPipelineOptions,
)
docling_document_converter.PdfFormatOption = getattr(
    docling_document_converter,
    "PdfFormatOption",
    _PdfFormatOption,
)

docling_document_converter.DocumentConverter = getattr(
    docling_document_converter,
    "DocumentConverter",
    type("DocumentConverter", (), {}),
)
docling_core_hybrid.HybridChunker = getattr(
    docling_core_hybrid,
    "HybridChunker",
    type("HybridChunker", (), {}),
)
docling_core_tokenizer.OpenAITokenizer = getattr(
    docling_core_tokenizer,
    "OpenAITokenizer",
    type("OpenAITokenizer", (), {}),
)
docling_core_serializer.MarkdownDocSerializer = getattr(
    docling_core_serializer,
    "MarkdownDocSerializer",
    type("MarkdownDocSerializer", (), {}),
)
docling_core_doc.DoclingDocument = getattr(
    docling_core_doc,
    "DoclingDocument",
    type("DoclingDocument", (), {}),
)
docling_core_io.DocumentStream = getattr(
    docling_core_io,
    "DocumentStream",
    type("DocumentStream", (), {}),
)

os.environ.setdefault("WV_URL", "https://dummy.weaviate.network")
os.environ.setdefault("WV_API_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("POSTGRES_URL", "postgresql://dummy:dummy@localhost/dummy")

import em_backend.vector.parser as parser_module


class FakeEncoding:
    """Simple encoding stub mapping characters to ordinal tokens."""

    def encode(self, text: str) -> list[int]:
        return [ord(ch) for ch in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)


class FakeDocumentConverter:
    def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - stub
        pass


class FakeOpenAITokenizer:
    def __init__(self, tokenizer, max_tokens) -> None:
        self._tokenizer = tokenizer
        self._max_tokens = max_tokens

    def get_max_tokens(self) -> int:
        return self._max_tokens


class FakeHybridChunker:
    def __init__(self, *args, **kwargs) -> None:
        self.delim = "\n\n"
        self.chunks: list[SimpleNamespace] = []

    def chunk(self, _doc):  # noqa: D401 - stub
        return iter(self.chunks)

    def contextualize(self, chunk):
        return chunk.text

    def serialize(self, chunk):
        return chunk.text


class FakeMarkdownSerializer:
    def __init__(self, doc) -> None:  # noqa: D401 - stub
        self._doc = doc

    def serialize(self, item=None, **kwargs):
        if item is None:
            return SimpleNamespace(text="")
        return SimpleNamespace(text=getattr(item, "markdown", ""))


def _build_chunk(
    markdown_parts: list[str], pages: list[int], raw_text: str = "/gid0001"
) -> SimpleNamespace:
    doc_items = [
        SimpleNamespace(markdown=md, prov=[SimpleNamespace(page_no=page)])
        for md, page in zip(markdown_parts, pages, strict=True)
    ]
    meta = SimpleNamespace(doc_items=doc_items)
    return SimpleNamespace(text=raw_text, meta=meta)


def test_chunk_document_produces_markdown_without_gid(monkeypatch):
    fake_encoding = FakeEncoding()

    monkeypatch.setattr(
        parser_module.tiktoken, "encoding_for_model", lambda _model: fake_encoding
    )
    monkeypatch.setattr(parser_module, "DocumentConverter", FakeDocumentConverter)
    monkeypatch.setattr(parser_module, "OpenAITokenizer", FakeOpenAITokenizer)
    monkeypatch.setattr(parser_module, "HybridChunker", FakeHybridChunker)
    monkeypatch.setattr(parser_module, "MarkdownDocSerializer", FakeMarkdownSerializer)

    parser = parser_module.DocumentParser()

    long_markdown_section = "# Heading\n" + ("a" * 1000)
    trailing_markdown_section = "Paragraph" + ("b" * 1100)
    parser.chunker.chunks = [
        _build_chunk(
            [long_markdown_section, trailing_markdown_section],
            pages=[3, 4],
        )
    ]

    chunks = list(parser.chunk_document(doc=object()))

    assert len(chunks) == 2
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]
    assert chunks[0]["chunk_id"] != chunks[1]["chunk_id"]
    assert all("/gid" not in chunk["text"] for chunk in chunks)
    assert all(
        len(fake_encoding.encode(chunk["text"])) == parser.MAX_CHUNK_TOKENS
        for chunk in chunks
    )
    assert all(chunk["page_number"] == 3 for chunk in chunks)


def test_chunk_document_skips_missing_text_placeholders(monkeypatch):
    fake_encoding = FakeEncoding()

    monkeypatch.setattr(
        parser_module.tiktoken, "encoding_for_model", lambda _model: fake_encoding
    )
    monkeypatch.setattr(parser_module, "DocumentConverter", FakeDocumentConverter)
    monkeypatch.setattr(parser_module, "OpenAITokenizer", FakeOpenAITokenizer)
    monkeypatch.setattr(parser_module, "HybridChunker", FakeHybridChunker)
    monkeypatch.setattr(parser_module, "MarkdownDocSerializer", FakeMarkdownSerializer)

    parser = parser_module.DocumentParser()

    readable_text = "Legible text " * 120
    parser.chunker.chunks = [
        _build_chunk(
            ["<!-- missing-text -->"],
            pages=[7],
            raw_text=readable_text,
        )
    ]

    chunks = list(parser.chunk_document(doc=object()))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["page_number"] == 7
    assert "<!-- missing-text -->" not in chunk["text"]
    assert chunk["text"].strip().startswith("Legible text")


def test_chunk_document_filters_gid_bullet_and_uses_fallback(monkeypatch):
    fake_encoding = FakeEncoding()

    monkeypatch.setattr(
        parser_module.tiktoken, "encoding_for_model", lambda _model: fake_encoding
    )
    monkeypatch.setattr(parser_module, "DocumentConverter", FakeDocumentConverter)
    monkeypatch.setattr(parser_module, "OpenAITokenizer", FakeOpenAITokenizer)
    monkeypatch.setattr(parser_module, "HybridChunker", FakeHybridChunker)
    monkeypatch.setattr(parser_module, "MarkdownDocSerializer", FakeMarkdownSerializer)

    parser = parser_module.DocumentParser()

    parser.chunker.chunks = [
        _build_chunk(
            ["- /gid00019/gid00023"],
            pages=[5],
            raw_text="Readable fallback content from serialize()",
        )
    ]

    chunks = list(parser.chunk_document(doc=object()))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["page_number"] == 5
    assert "/gid" not in chunk["text"]
    assert chunk["text"] == "Readable fallback content from serialize()"


def test_chunk_document_records_summary_and_markdown(monkeypatch, tmp_path):
    fake_encoding = FakeEncoding()

    monkeypatch.setenv("EM_CHUNK_REPORTS_DIR", str(tmp_path / "reports"))

    monkeypatch.setattr(
        parser_module.tiktoken, "encoding_for_model", lambda _model: fake_encoding
    )
    monkeypatch.setattr(parser_module, "DocumentConverter", FakeDocumentConverter)
    monkeypatch.setattr(parser_module, "OpenAITokenizer", FakeOpenAITokenizer)
    monkeypatch.setattr(parser_module, "HybridChunker", FakeHybridChunker)
    monkeypatch.setattr(parser_module, "MarkdownDocSerializer", FakeMarkdownSerializer)

    def fake_chunk_with_openai_vision(self, placeholder_pages):
        assert placeholder_pages == {2}
        return [
            {
                "chunk_id": "vision-1",
                "text": "Recovered vision text",
                "page_number": 2,
                "chunk_index": 0,
                "extraction_method": "vision:test-model",
            }
        ]

    monkeypatch.setattr(
        parser_module.DocumentParser,
        "_chunk_with_openai_vision",
        fake_chunk_with_openai_vision,
    )

    parser = parser_module.DocumentParser()

    parser.chunker.chunks = [
        _build_chunk([
            "- /gid00019/gid00023"
        ], pages=[2], raw_text="fallback text"),
    ]

    chunks = list(parser.chunk_document(doc=object()))

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Recovered vision text"

    summary = parser.get_last_run_summary()
    assert summary["total_chunks"] == 1
    assert summary["vision_chunks"] == 1
    assert summary["docling_chunks"] == 0
    assert summary["vision_fallback_attempted"] is True
    assert summary["vision_fallback_successful_pages"] == [2]

    reports_dir = tmp_path / "reports"
    report_files = list(reports_dir.glob("*chunk_summary*.md"))
    assert report_files, "expected a chunk summary markdown file"
    newest_report = max(report_files, key=lambda path: path.stat().st_mtime)
    contents = newest_report.read_text()
    assert "Total chunks: 1" in contents
    assert "Vision chunks: 1" in contents
    assert "Recovered vision text" in contents
    assert "Page: 2" in contents
