# ✅ SOLUTION: Proper Page Number Extraction with Docling

## 🔴 The Problem

The `HybridChunker` from docling-core **does NOT preserve the `prov` attribute** on chunks. This is by design - chunks are text segments with metadata, NOT document elements.

## ✅ The Solution

According to Docling documentation, you need to extract page numbers from the **original DoclingDocument items** BEFORE or DURING chunking, not from the chunks themselves.

### Method 1: Iterate Through Document Items (Recommended)

Instead of chunking the entire document, iterate through individual items which DO have provenance:

```python
def chunk_document_with_pages(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
    """Chunk document while preserving page numbers from provenance."""
    chunk_index = 0
    
    # Iterate through document items that have provenance
    for item in doc.iterate_items():
        # Extract page number from item's provenance
        page_number = None
        if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
            first_prov = item.prov[0]
            if hasattr(first_prov, 'page_no'):
                page_number = first_prov.page_no
        
        # Get the text from this item
        item_text = item.text if hasattr(item, 'text') else str(item)
        
        # Now chunk this specific item's text
        for text_segment in self._split_to_token_budget(item_text):
            token_count = len(self._encoding.encode(text_segment))
            
            yield {
                "chunk_id": str(uuid4()),
                "text": text_segment,
                "page_number": page_number,  # Page from original item
                "chunk_index": chunk_index,
            }
            chunk_index += 1
```

### Method 2: Use Chunk Metadata (Alternative)

Chunks from `HybridChunker` maintain links to source items via metadata. Access the original items through the chunk:

```python
def chunk_document_with_metadata(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
    """Chunk document and extract page numbers from chunk metadata."""
    chunk_index = 0
    
    for chunk in self.chunker.chunk(doc):
        # Get page number from chunk metadata
        page_number = None
        
        # Chunks have metadata that links back to doc_items
        if hasattr(chunk, 'meta') and hasattr(chunk.meta, 'doc_items'):
            # Get the first source item
            if chunk.meta.doc_items and len(chunk.meta.doc_items) > 0:
                source_item_ref = chunk.meta.doc_items[0]
                
                # Resolve the reference to get the actual item
                # (This requires accessing the original document)
                source_item = self._resolve_item_ref(doc, source_item_ref)
                
                if source_item and hasattr(source_item, 'prov') and source_item.prov:
                    if len(source_item.prov) > 0:
                        first_prov = source_item.prov[0]
                        if hasattr(first_prov, 'page_no'):
                            page_number = first_prov.page_no
        
        # Contextualize chunk
        contextualized = self.chunker.contextualize(chunk)
        
        for text_segment in self._split_to_token_budget(contextualized):
            token_count = len(self._encoding.encode(text_segment))
            
            yield {
                "chunk_id": str(uuid4()),
                "text": text_segment,
                "page_number": page_number,
                "chunk_index": chunk_index,
            }
            chunk_index += 1
```

### Method 3: Direct Item Access (Simplest)

Skip the HybridChunker entirely and chunk document items directly:

```python
def chunk_document_direct(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
    """Chunk document by directly processing items with provenance."""
    chunk_index = 0
    
    # Access document body items directly
    if hasattr(doc, 'body') and doc.body:
        items = self._get_all_items_from_node(doc, doc.body)
        
        for item in items:
            # Extract page number
            page_number = None
            if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
                page_number = item.prov[0].page_no if hasattr(item.prov[0], 'page_no') else None
            
            # Get text content
            text = self._get_item_text(item)
            
            if not text:
                continue
                
            # Chunk this item's text
            for text_segment in self._split_to_token_budget(text):
                token_count = len(self._encoding.encode(text_segment))
                
                yield {
                    "chunk_id": str(uuid4()),
                    "text": text_segment,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
                chunk_index += 1

def _get_all_items_from_node(self, doc, node, items=None):
    """Recursively get all items from a document node."""
    if items is None:
        items = []
    
    # The node might be a reference, resolve it
    if isinstance(node, dict) and '$ref' in node:
        # This is a JSON reference, resolve it
        ref_path = node['$ref']
        # Navigate doc structure based on ref (e.g., "#/texts/0")
        parts = ref_path.lstrip('#/').split('/')
        if len(parts) == 2:
            collection_name, index = parts
            if hasattr(doc, collection_name):
                collection = getattr(doc, collection_name)
                if isinstance(collection, list) and int(index) < len(collection):
                    return collection[int(index)]
    
    # Or iterate through document collections directly
    for collection_name in ['texts', 'tables', 'pictures', 'groups']:
        if hasattr(doc, collection_name):
            collection = getattr(doc, collection_name)
            if collection:
                items.extend(collection)
    
    return items

def _get_item_text(self, item):
    """Extract text from various item types."""
    if hasattr(item, 'text') and item.text:
        return item.text
    elif hasattr(item, 'orig') and item.orig:
        return item.orig
    return None
```

## 📝 Implementation for Your Code

Here's what to change in `ElectOMate-Backend/src/em_backend/vector/parser.py`:

```python
def chunk_document(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
    """Chunk document while preserving page numbers."""
    chunk_index = 0
    
    # Get all text items from the document (these have provenance!)
    text_items = []
    for collection_name in ['texts', 'tables', 'pictures']:
        if hasattr(doc, collection_name):
            collection = getattr(doc, collection_name)
            if collection:
                text_items.extend(collection)
    
    # Process each item
    for item in text_items:
        # Extract page number from item's provenance
        page_number = None
        if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
            first_prov = item.prov[0]
            page_number = getattr(first_prov, 'page_no', None)
        
        # Get text from item
        text = getattr(item, 'text', None) or getattr(item, 'orig', None)
        if not text:
            continue
        
        # Chunk this item's text
        for text_segment in self._split_to_token_budget(text):
            token_count = len(self._encoding.encode(text_segment))
            logger.info(
                f"Generated chunk {chunk_index}: {token_count} tokens, "
                f"page {page_number if page_number is not None else 'unknown'}"
            )
            yield {
                "chunk_id": str(uuid4()),
                "text": text_segment,
                "page_number": page_number,
                "chunk_index": chunk_index,
            }
            chunk_index += 1
```

## 🎯 Why This Works

1. **DoclingDocument items have provenance** ✅
   - `doc.texts` - List of TextItem objects
   - `doc.tables` - List of TableItem objects
   - `doc.pictures` - List of PictureItem objects
   - Each has `item.prov[0].page_no` containing the page number

2. **We iterate items directly** ✅
   - Skip the HybridChunker which loses provenance
   - Access provenance before chunking
   - Chunk each item's text individually

3. **Page numbers are preserved** ✅
   - Extracted once per item
   - Applied to all chunks from that item
   - Properly stored in Weaviate

## 📊 Key Docling Structures

### Provenance Structure
```python
item.prov = [
    ProvenanceItem(
        page_no=1,  # ← THE PAGE NUMBER!
        bbox=BoundingBox(...),
        charspan=[0, 100]
    )
]
```

### DoclingDocument Collections
```python
doc.texts      # List[TextItem] - paragraphs, headers, etc.
doc.tables     # List[TableItem] - tables with cells
doc.pictures   # List[PictureItem] - images
doc.groups     # List[GroupItem] - lists, sections
```

Each item in these collections has:
- `item.text` or `item.orig` - The actual text content
- `item.prov` - List of ProvenanceItem with page numbers
- `item.label` - Type of element (TEXT, SECTION_HEADER, etc.)

## 🚀 Next Steps

1. Update `em_backend/vector/parser.py` with the new method
2. Test with your PDF to verify page numbers work
3. Re-upload documents to Weaviate to get page numbers indexed

The key insight: **DON'T rely on chunks having provenance - get it from the DoclingDocument items directly!**

