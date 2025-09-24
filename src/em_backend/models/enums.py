from enum import StrEnum, auto


class SupportedDocumentFormats(StrEnum):
    PDF = auto()
    DOCX = auto()
    XLSX = auto()
    PPTX = auto()
    MARKDOWN = auto()
    ASCII = auto()
    HTML = auto()
    XHTML = auto()
    CSV = auto()


class ParsingQuality(StrEnum):
    NO_PARSING = auto()
    POOR = auto()
    FAIR = auto()
    GOOD = auto()
    EXCELLENT = auto()
    UNSPECIFIED = auto()


class IndexingSuccess(StrEnum):
    NO_INDEXING = auto()
    SUCCESS = auto()
    PARTIAL_SUCESS = auto()
    FAILED = auto()
