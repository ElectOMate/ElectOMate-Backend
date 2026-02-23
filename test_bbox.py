import sys
sys.path.insert(0, "src")

import fitz
from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor

extractor = PDFBboxExtractor()
doc = extractor.extract_from_path("assets/manifestos/CDU.pdf")
print(f"PDF loaded: {len(doc)} pages")

chunks = [
    {"chunk_id": "test-1", "text": "Deutschland", "page_number": 1},
    {"chunk_id": "test-2", "text": "Wirtschaft", "page_number": 2},
]

result = extractor.extract_bboxes_for_chunks(doc, chunks)
doc.close()

for cid, bboxes in result.items():
    print(f"{cid}: {len(bboxes)} bboxes")
    for b in bboxes[:3]:
        print(f"  {b}")
